"""Panorama de métricas sobre MLflow (specs/052-hu-51-panorama-metricas).

Cubren S1 (agregados en una ventana), S2 (fuente única: las corridas de MLflow, sin
almacén propio), S6/AC2 (estado degradado, nunca 500) y S7/RNF-3 (sin textos ni PII
en los agregados). Corren offline: agregación pura sobre filas y un file store
temporal (``tmp_path/mlruns``), sin red, API key ni GPU.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from m2_cad import metricas, seguimiento

DESDE = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
HASTA = DESDE + timedelta(hours=24)

CLAVES_DEL_PANORAMA = {
    "disponible",
    "motivo",
    "desde",
    "hasta",
    "solicitudes",
    "entregadas",
    "declinadas",
    "errores",
    "declinaciones_por_causa",
    "latencia_media_ms",
    "costo_usd",
    "mlflow_ui",
    "generado_en",
}


@pytest.fixture(autouse=True)
def _mlflow_de_archivo(monkeypatch):
    """MLflow 3.x exige opt-out explícito para el file store de las pruebas."""
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    monkeypatch.delenv("MLFLOW_UI_URL", raising=False)


def _ms(momento: datetime) -> float:
    return momento.timestamp() * 1000


def _fila(
    estado: str | None,
    *,
    causa: str | None = None,
    latencia: float | None = None,
    costo: float | None = None,
    familia: str | None = "spacer",
    prompt: str | None = "planner-v1",
    inicio: datetime | None = None,
) -> dict:
    """Fila ya normalizada por ``metricas.lectura``."""
    return {
        "estado": estado,
        "causa": causa,
        "latencia_ms": latencia,
        "costo_usd": costo,
        "familia": familia,
        "prompt": prompt,
        "inicio_ms": _ms(inicio or DESDE + timedelta(hours=1)),
    }


def _configuracion(tmp_path, **cambios):
    return seguimiento.configuracion_en(f"file:{tmp_path / 'mlruns'}", **cambios)


def _corridas_en_mlflow(configuracion) -> list:
    from mlflow.tracking import MlflowClient

    cliente = MlflowClient(tracking_uri=configuracion.uri)
    experimento = cliente.get_experiment_by_name(configuracion.experimento_generacion)
    assert experimento is not None, "el experimento de generación no existe en MLflow"
    return cliente.search_runs([experimento.experiment_id])


# -- agregación pura ---------------------------------------------------


def test_resumir_corridas_agrega_totales_causas_latencia_y_costo():
    # Arrange
    corridas = [
        _fila("entregada", latencia=1000.0, costo=0.0001),
        _fila("entregada", latencia=2000.0, costo=0.0002),
        _fila("declinada", causa="familia_no_soportada"),
        _fila("declinada", causa="dimension_incoherente"),
        _fila("error"),
        _fila("cancelada"),
    ]

    # Act
    resumen = metricas.resumir_corridas(corridas, desde=DESDE, hasta=HASTA)

    # Assert
    assert set(resumen) == CLAVES_DEL_PANORAMA
    assert resumen["solicitudes"] == 6
    assert resumen["entregadas"] == 2
    assert resumen["declinadas"] == 2
    assert resumen["errores"] == 1
    assert resumen["declinaciones_por_causa"] == {
        "familia_no_soportada": 1,
        "dimension_incoherente": 1,
    }
    assert resumen["latencia_media_ms"] == pytest.approx(1500.0)
    assert resumen["costo_usd"] == pytest.approx(0.0003)
    assert resumen["disponible"] is True
    assert resumen["motivo"] is None
    assert resumen["desde"] == DESDE.isoformat()
    assert resumen["hasta"] == HASTA.isoformat()
    assert resumen["mlflow_ui"] == metricas.UI_POR_DEFECTO


def test_mlflow_ui_sale_del_entorno(monkeypatch):
    # Arrange
    monkeypatch.setenv("MLFLOW_UI_URL", "http://mlflow.interno:5000")

    # Act
    resumen = metricas.resumir_corridas([], desde=DESDE, hasta=HASTA)

    # Assert
    assert resumen["mlflow_ui"] == "http://mlflow.interno:5000"


def test_declinada_sin_causa_cuenta_como_sin_causa():
    # Arrange
    corridas = [
        _fila("declinada", causa=None),
        _fila("declinada", causa=""),
        _fila("declinada", causa="ninguna"),
        _fila("declinada", causa="familia_no_soportada"),
    ]

    # Act
    resumen = metricas.resumir_corridas(corridas, desde=DESDE, hasta=HASTA)

    # Assert
    assert resumen["declinadas"] == 4
    assert resumen["declinaciones_por_causa"] == {
        "familia_no_soportada": 1,
        "sin_causa": 3,
    }


def test_descarta_las_filas_fuera_de_la_ventana():
    # Arrange
    corridas = [
        _fila("entregada", latencia=100.0, inicio=DESDE - timedelta(milliseconds=1)),
        _fila("entregada", latencia=200.0, inicio=HASTA + timedelta(milliseconds=1)),
        _fila("entregada", latencia=300.0, inicio=DESDE),
        _fila("entregada", latencia=500.0, inicio=HASTA),
    ]

    # Act
    resumen = metricas.resumir_corridas(corridas, desde=DESDE, hasta=HASTA)

    # Assert
    assert resumen["solicitudes"] == 2
    assert resumen["entregadas"] == 2
    assert resumen["latencia_media_ms"] == pytest.approx(400.0)


def test_sin_metricas_no_inventa_latencia_ni_costo():
    # Arrange
    corridas = [_fila("entregada"), _fila("declinada", causa="tipo_fuera_catalogo")]

    # Act
    resumen = metricas.resumir_corridas(corridas, desde=DESDE, hasta=HASTA)

    # Assert
    assert resumen["latencia_media_ms"] is None
    assert resumen["costo_usd"] == 0.0


def test_el_resultado_no_expone_textos_ni_identificadores():
    # Arrange
    run_id = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
    corridas = [
        {
            **_fila("entregada", latencia=10.0, costo=0.0),
            "run_id": run_id,
            "texto": "una brida para Juan Polanco, juan@correo.com",
            "usuario": "juan@correo.com",
        }
    ]

    # Act
    serializado = json.dumps(
        metricas.resumir_corridas(corridas, desde=DESDE, hasta=HASTA), ensure_ascii=False
    )

    # Assert
    assert "texto" not in serializado
    assert "usuario" not in serializado
    assert "@" not in serializado
    assert run_id not in serializado


# -- estado degradado --------------------------------------------------


def test_resumir_corridas_con_motivo_degrada_y_deja_los_contadores_en_cero():
    # Arrange
    motivo = "El seguimiento está desactivado: activa MLFLOW y vuelve a intentarlo."

    # Act
    resumen = metricas.resumir_corridas(
        [_fila("entregada", latencia=10.0)], desde=DESDE, hasta=HASTA, motivo=motivo
    )

    # Assert
    assert resumen["disponible"] is False
    assert resumen["motivo"] == motivo
    assert resumen["solicitudes"] == 0
    assert resumen["entregadas"] == 0
    assert resumen["declinadas"] == 0
    assert resumen["errores"] == 0
    assert resumen["declinaciones_por_causa"] == {}
    assert resumen["latencia_media_ms"] is None
    assert resumen["costo_usd"] == 0.0


def test_leer_corridas_con_seguimiento_inactivo_no_toca_mlflow(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path, activo=False)

    # Act / Assert
    with pytest.raises(metricas.SeguimientoNoDisponible) as excinfo:
        metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)
    assert "desactivado" in str(excinfo.value)


def test_panorama_con_seguimiento_inactivo_degrada_sin_lanzar(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path, activo=False)

    # Act
    panorama = metricas.panorama(configuracion, horas=2)

    # Assert
    assert panorama["disponible"] is False
    assert "desactivado" in panorama["motivo"]
    assert panorama["solicitudes"] == 0
    assert panorama["mlflow_ui"] == metricas.UI_POR_DEFECTO
    desde = datetime.fromisoformat(panorama["desde"])
    hasta = datetime.fromisoformat(panorama["hasta"])
    assert hasta - desde == timedelta(hours=2)


def test_panorama_con_mlflow_caido_degrada_sin_lanzar():
    # Arrange
    configuracion = seguimiento.Configuracion(uri="http://127.0.0.1:9")

    # Act
    panorama = metricas.panorama(configuracion, horas=1)

    # Assert
    assert panorama["disponible"] is False
    assert panorama["motivo"]
    assert panorama["solicitudes"] == 0


def test_el_error_de_mlflow_no_expone_credenciales():
    # Arrange
    configuracion = seguimiento.Configuracion(uri="http://usuario:secreto@127.0.0.1:9")

    # Act
    with pytest.raises(metricas.SeguimientoNoDisponible) as excinfo:
        metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)

    # Assert
    mensaje = str(excinfo.value)
    assert "secreto" not in mensaje
    assert "usuario:secreto" not in mensaje


@pytest.mark.parametrize("horas", [0, -1, metricas.HORAS_MAXIMAS + 1])
def test_panorama_rechaza_ventanas_fuera_de_rango(tmp_path, horas):
    # Arrange
    configuracion = _configuracion(tmp_path, activo=False)

    # Act / Assert
    with pytest.raises(ValueError):
        metricas.panorama(configuracion, horas=horas)


# -- MLflow real y offline ---------------------------------------------


def test_lee_y_agrega_las_corridas_que_mlflow_tiene_en_la_ventana(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path)
    entregada = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    entregada.registrar_params(familia="spacer", prompt="planner-v1")
    entregada.registrar_metricas(latencia_ms=1200.0, costo_usd=0.0004)
    entregada.finalizar(estado="entregada")
    declinada = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    declinada.registrar_params(familia="brida", prompt="planner-v1")
    declinada.registrar_metricas(latencia_ms=800.0, costo_usd=0.0002)
    declinada.finalizar(estado="declinada", causa_declinacion="familia_no_soportada")
    assert entregada.id and declinada.id

    desde = datetime.now(UTC) - timedelta(hours=1)
    hasta = datetime.now(UTC) + timedelta(hours=1)

    # Act
    filas = metricas.leer_corridas(configuracion, desde=desde, hasta=hasta)
    resumen = metricas.resumir_corridas(filas, desde=desde, hasta=hasta)

    # Assert
    en_mlflow = [
        corrida
        for corrida in _corridas_en_mlflow(configuracion)
        if _ms(desde) <= corrida.info.start_time <= _ms(hasta)
    ]
    assert len(filas) == len(en_mlflow) == 2
    assert resumen["solicitudes"] == len(en_mlflow)
    assert resumen["entregadas"] == sum(
        1 for corrida in en_mlflow if corrida.data.tags.get("estado") == "entregada"
    )
    assert resumen["declinadas"] == sum(
        1 for corrida in en_mlflow if corrida.data.tags.get("estado") == "declinada"
    )
    assert resumen["errores"] == 0
    assert resumen["declinaciones_por_causa"] == {"familia_no_soportada": 1}
    assert resumen["latencia_media_ms"] == pytest.approx(
        sum(corrida.data.metrics["latencia_ms"] for corrida in en_mlflow) / len(en_mlflow)
    )
    assert resumen["costo_usd"] == pytest.approx(
        sum(corrida.data.metrics["costo_usd"] for corrida in en_mlflow)
    )
    normalizadas = sorted(filas, key=lambda fila: fila["latencia_ms"])
    declinada_leida, entregada_leida = normalizadas
    assert set(declinada_leida) == {
        "estado",
        "causa",
        "latencia_ms",
        "costo_usd",
        "familia",
        "prompt",
        "inicio_ms",
    }
    assert declinada_leida["estado"] == "declinada"
    assert declinada_leida["causa"] == "familia_no_soportada"
    assert declinada_leida["latencia_ms"] == pytest.approx(800.0)
    assert declinada_leida["costo_usd"] == pytest.approx(0.0002)
    assert declinada_leida["familia"] == "brida"
    assert declinada_leida["prompt"] == "planner-v1"
    assert _ms(desde) <= declinada_leida["inicio_ms"] <= _ms(hasta)
    assert entregada_leida["estado"] == "entregada"
    assert entregada_leida["causa"] is None
    assert entregada_leida["familia"] == "spacer"


def test_leer_corridas_reporta_un_experimento_inexistente(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path, experimento_generacion="experimento-inexistente")

    # Act / Assert
    with pytest.raises(metricas.SeguimientoNoDisponible) as excinfo:
        metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)
    assert "experimento-inexistente" in str(excinfo.value)
