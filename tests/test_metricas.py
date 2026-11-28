"""Panorama de métricas sobre MLflow (specs/052-hu-51-panorama-metricas).

Cubren S1 (agregados en una ventana), S2 (fuente única: las corridas de MLflow, sin
almacén propio), S6/AC2 (estado degradado, nunca 500) y S7/RNF-3 (sin textos ni PII
en los agregados). Corren offline: agregación pura sobre filas y un file store
temporal (``tmp_path/mlruns``), sin red, API key ni GPU.
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from m2_cad import metricas, seguimiento

DESDE = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
HASTA = DESDE + timedelta(hours=24)

# El motivo que llega al cliente es fijo: no arrastra texto de la excepción ni el
# URI del backend (R1-1/R1-2).
MOTIVO_BACKEND = "El seguimiento no está disponible: no se pudieron leer las métricas de MLflow."
VAR_ESPERA = "MLFLOW_HTTP_REQUEST_TIMEOUT"

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
    "entregadas_por_familia",
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


class _Pagina(list):
    """Página de resultados falsa con el token de continuación que publica MLflow."""

    def __init__(self, corridas=(), token=None):
        super().__init__(corridas)
        self.token = token


class _ClienteFalso:
    """Cliente de MLflow guionizado: ni red ni file store (S5/RNF-1)."""

    def __init__(self, paginas=(), *, error=None, al_leer=None):
        self.paginas = list(paginas)
        self.llamadas: list[dict] = []
        self.experimentos_consultados: list[str] = []
        self.error = error
        self.al_leer = al_leer

    def get_experiment_by_name(self, nombre):
        self.experimentos_consultados.append(nombre)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(experiment_id="exp-generacion")

    def search_runs(self, experiment_ids, **parametros):
        self.llamadas.append({"experiment_ids": experiment_ids, **parametros})
        if self.al_leer is not None:
            self.al_leer()
        if self.error is not None:
            raise self.error
        return self.paginas.pop(0) if self.paginas else _Pagina()


def _instalar_cliente(monkeypatch, cliente, observaciones=None):
    """Sustituye el cliente de MLflow por el doble y anota el entorno al construirlo."""

    def construir(**_):
        if observaciones is not None:
            observaciones["creacion"] = os.environ.get(VAR_ESPERA)
        return cliente

    monkeypatch.setattr("mlflow.tracking.MlflowClient", construir)
    return cliente


def _corrida_falsa(
    *,
    estado: str = "entregada",
    familia: str | None = "spacer",
    latencia: float | None = None,
    costo: float | None = None,
    inicio: datetime | None = None,
):
    """Corrida mínima compatible con ``metricas.lectura``, sin MLflow de por medio."""
    medidas = {
        clave: valor
        for clave, valor in (("latencia_ms", latencia), ("costo_usd", costo))
        if valor is not None
    }
    parametros = {"familia": familia} if familia is not None else {}
    return SimpleNamespace(
        info=SimpleNamespace(start_time=_ms(inicio or DESDE + timedelta(hours=1))),
        data=SimpleNamespace(tags={"estado": estado}, metrics=medidas, params=parametros),
    )


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
    assert resumen["entregadas_por_familia"] == {"spacer": 2}
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


def test_entregadas_por_familia_solo_cuenta_entregadas():
    # Arrange
    corridas = [
        _fila("entregada", familia="spacer"),
        _fila("entregada", familia="brida"),
        _fila("entregada", familia=None),
        _fila("entregada", familia=""),
        _fila("declinada", causa="familia_no_soportada", familia="spacer"),
        _fila("error", familia="brida"),
    ]

    # Act
    resumen = metricas.resumir_corridas(corridas, desde=DESDE, hasta=HASTA)

    # Assert
    assert resumen["entregadas_por_familia"] == {
        "brida": 1,
        "desconocida": 2,
        "spacer": 1,
    }
    assert list(resumen["entregadas_por_familia"]) == ["brida", "desconocida", "spacer"]


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
    assert resumen["entregadas_por_familia"] == {}
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
    assert mensaje == MOTIVO_BACKEND
    assert "secreto" not in mensaje
    assert "usuario:secreto" not in mensaje


def test_el_motivo_degradado_es_fijo_y_no_filtra_el_detalle_del_backend(monkeypatch, caplog):
    # Arrange: la excepción del backend arrastra URI con credenciales y rutas.
    fuga = RuntimeError(
        "falló http://usuario:clave@host:5000/mlruns al leer /var/lib/mlflow "
        "(credencial clave=clave-interna)"
    )
    _instalar_cliente(monkeypatch, _ClienteFalso(error=fuga))
    configuracion = seguimiento.configuracion_en("http://127.0.0.1:5000")

    # Act
    with caplog.at_level(logging.WARNING):
        panorama = metricas.panorama(configuracion, horas=1)

    # Assert
    assert panorama["disponible"] is False
    motivo = panorama["motivo"]
    assert motivo == MOTIVO_BACKEND
    assert "http://" not in motivo
    assert "@" not in motivo
    assert "/var/lib" not in motivo
    assert "clave" not in motivo
    assert "RuntimeError" not in motivo
    # El detalle técnico sigue disponible en el log, sin el userinfo del URI.
    assert "RuntimeError" in caplog.text
    assert "usuario:clave" not in caplog.text


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


def test_leer_corridas_reporta_un_experimento_inexistente(tmp_path, caplog):
    # Arrange
    configuracion = _configuracion(tmp_path, experimento_generacion="experimento-inexistente")

    # Act
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(metricas.SeguimientoNoDisponible) as excinfo,
    ):
        metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)

    # Assert
    assert str(excinfo.value) == MOTIVO_BACKEND
    assert "experimento-inexistente" in caplog.text


# -- puerta pública del seguimiento (R2-003) ----------------------------


def test_metricas_usa_la_puerta_publica_del_seguimiento(tmp_path, monkeypatch):
    # Arrange
    assert callable(seguimiento.preparar_entorno)
    configuracion = _configuracion(tmp_path)
    corrida = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    corrida.finalizar(estado="entregada")
    assert corrida.id
    original = seguimiento.preparar_entorno
    recibidas = []

    def espia(configuracion_recibida):
        recibidas.append(configuracion_recibida)
        return original(configuracion_recibida)

    monkeypatch.setattr(seguimiento, "preparar_entorno", espia)
    desde = datetime.now(UTC) - timedelta(hours=1)
    hasta = datetime.now(UTC) + timedelta(hours=1)

    # Act
    filas = metricas.leer_corridas(configuracion, desde=desde, hasta=hasta)

    # Assert
    assert recibidas == [configuracion]
    assert len(filas) == 1
    assert filas[0]["estado"] == "entregada"


# -- ventana: un solo predicado y filtro en el servidor (R2-004, R3) -----


def test_leer_corridas_delega_la_ventana_en_mlflow_y_no_refiltra_en_memoria(monkeypatch):
    # Arrange
    dentro = _corrida_falsa(inicio=DESDE + timedelta(hours=1))
    fuera = _corrida_falsa(inicio=DESDE - timedelta(days=30))
    cliente = _instalar_cliente(monkeypatch, _ClienteFalso([_Pagina([dentro, fuera])]))
    configuracion = seguimiento.configuracion_en("http://127.0.0.1:5000")

    # Act
    filas = metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)
    resumen = metricas.resumir_corridas(filas, desde=DESDE, hasta=HASTA)

    # Assert
    assert len(filas) == 2, "leer_corridas ya no vuelve a decidir la ventana en memoria"
    assert resumen["solicitudes"] == 1, "resumir_corridas es el único que decide"
    assert cliente.llamadas[0]["filter_string"] == (
        f"attributes.start_time >= {math.floor(_ms(DESDE))} "
        f"and attributes.start_time <= {math.ceil(_ms(HASTA))}"
    )
    assert cliente.llamadas[0]["order_by"] == ["attributes.start_time DESC"]
    assert cliente.llamadas[0]["max_results"] == 1000


def test_leer_corridas_sigue_la_continuacion_hasta_agotar_los_tokens(monkeypatch):
    # Arrange
    corridas = [_corrida_falsa(latencia=float(indice)) for indice in range(5)]
    paginas = [
        _Pagina(corridas[0:2], token="pagina-2"),
        _Pagina(corridas[2:4], token="pagina-3"),
        _Pagina(corridas[4:5]),
    ]
    cliente = _instalar_cliente(monkeypatch, _ClienteFalso(paginas))
    configuracion = seguimiento.configuracion_en("http://127.0.0.1:5000")

    # Act
    filas = metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)

    # Assert
    assert len(filas) == 5
    assert [llamada["page_token"] for llamada in cliente.llamadas] == [
        None,
        "pagina-2",
        "pagina-3",
    ]


def test_leer_corridas_no_se_detiene_en_un_multiplo_exacto_de_la_pagina(monkeypatch):
    # Arrange: 4 filas es múltiplo exacto de la página, y todavía quedaba token.
    corridas = [_corrida_falsa(latencia=float(indice)) for indice in range(4)]
    paginas = [
        _Pagina(corridas[0:2], token="pagina-2"),
        _Pagina(corridas[2:4], token="pagina-3"),
        _Pagina(),
    ]
    cliente = _instalar_cliente(monkeypatch, _ClienteFalso(paginas))
    configuracion = seguimiento.configuracion_en("http://127.0.0.1:5000")

    # Act
    filas = metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)

    # Assert
    assert len(filas) == 4
    assert len(cliente.llamadas) == 3


def test_lee_las_1050_corridas_del_file_store_con_paginacion_completa(tmp_path):
    """Regresión R3: con más corridas que una página, el panorama no se queda corto.

    Las corridas se crean directamente con el cliente de MLflow porque 1050
    `iniciar_corrida` cerradas una a una hacen el suite demasiado lento; el tamaño de
    página es el real del módulo (``TAMANO_PAGINA = 1000``), así que la prueba cruza
    el mismo límite que la implementación en producción y lee dos páginas.
    """
    # Arrange
    from mlflow.tracking import MlflowClient

    configuracion = _configuracion(tmp_path)
    cliente = MlflowClient(tracking_uri=configuracion.uri)
    experimento_id = cliente.create_experiment(configuracion.experimento_generacion)
    ahora_ms = int(datetime.now(UTC).timestamp() * 1000)
    for indice in range(1050):
        cliente.create_run(
            experimento_id,
            start_time=ahora_ms - 1050 + indice,
            tags={"estado": "entregada"},
        )
    desde = datetime.now(UTC) - timedelta(hours=1)
    hasta = datetime.now(UTC) + timedelta(hours=1)

    # Act
    filas = metricas.leer_corridas(configuracion, desde=desde, hasta=hasta)
    resumen = metricas.resumir_corridas(filas, desde=desde, hasta=hasta)

    # Assert
    assert len(filas) == 1050, "una página incompleta acorta el panorama sin avisar"
    assert resumen["solicitudes"] == 1050
    assert resumen["entregadas"] == 1050
    assert metricas.TAMANO_PAGINA == 1000


# -- plazo del backend (R3-no-backend-timeout) --------------------------


def test_fija_el_plazo_del_backend_y_restaura_el_valor_anterior(monkeypatch):
    # Arrange
    monkeypatch.setenv(VAR_ESPERA, "2")
    observaciones = {}

    def al_leer():
        observaciones["lectura"] = os.environ.get(VAR_ESPERA)

    _instalar_cliente(
        monkeypatch,
        _ClienteFalso([_Pagina([_corrida_falsa()])], al_leer=al_leer),
        observaciones=observaciones,
    )
    configuracion = seguimiento.configuracion_en("http://127.0.0.1:5000")

    # Act
    metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)

    # Assert
    assert metricas.ESPERA_BACKEND_S == 5
    plazo = str(metricas.ESPERA_BACKEND_S)
    assert observaciones["creacion"] == plazo
    assert observaciones["lectura"] == plazo
    assert os.environ.get(VAR_ESPERA) == "2"


def test_quita_el_plazo_del_backend_si_no_estaba_fijado(monkeypatch):
    # Arrange
    monkeypatch.delenv(VAR_ESPERA, raising=False)
    observaciones = {}
    _instalar_cliente(monkeypatch, _ClienteFalso(), observaciones=observaciones)
    configuracion = seguimiento.configuracion_en("http://127.0.0.1:5000")

    # Act
    metricas.leer_corridas(configuracion, desde=DESDE, hasta=HASTA)

    # Assert
    assert observaciones["creacion"] == str(metricas.ESPERA_BACKEND_S)
    assert VAR_ESPERA not in os.environ
