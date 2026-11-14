"""Pruebas del módulo de seguimiento con MLflow.

Cubren specs/009-hu-16-mlflow: AC2 (params/métricas/tags/artefactos), AC3 (cierre sin
RUNNING), AC5 (sanitización de PII), AC6 (degradación segura) y AC7 (versión de modelo).
Corren offline contra un file store temporal (``tmp_path/mlruns``), sin red ni GPU.
"""

from __future__ import annotations

import logging
import time

import pytest

from m2_cad import seguimiento


@pytest.fixture(autouse=True)
def _habilitar_file_store(monkeypatch):
    """MLflow 3.x exige opt-out explícito para el file store de las pruebas."""
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")


def _configuracion(tmp_path, **cambios):
    return seguimiento.configuracion_en(f"file:{tmp_path / 'mlruns'}", **cambios)


def _cliente(tmp_path):
    from mlflow.tracking import MlflowClient

    return MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")


def _corridas(tmp_path, experimento):
    cliente = _cliente(tmp_path)
    experimento_obj = cliente.get_experiment_by_name(experimento)
    if experimento_obj is None:
        return []
    return cliente.search_runs([experimento_obj.experiment_id])


def test_modo_desactivado_no_abre_corridas(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path, activo=False)

    # Act
    corrida = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    corrida.registrar_params(modelo="deepseek-v4-pro")
    corrida.registrar_metricas(latencia_ms=10.0)
    corrida.finalizar(estado="entregada")

    # Assert
    assert corrida.activa is False
    assert corrida.id is None
    assert _corridas(tmp_path, seguimiento.EXPERIMENTO_GENERACION) == []


def test_corrida_exitosa_registra_params_metricas_tags_y_artefactos(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path)
    programa = tmp_path / "programa.json"
    programa.write_text('{"parts": []}', encoding="utf-8")

    # Act
    corrida = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION,
        nombre="solicitud abc",
        tags={"solicitud_id": "abc"},
        configuracion=configuracion,
    )
    corrida.registrar_params(
        modelo="deepseek-v4-pro", version_modelo="v1", familia="spacer", temperatura=0.0
    )
    corrida.registrar_metricas(
        latencia_ms=12.5,
        tokens_entrada=100,
        tokens_salida=50,
        costo_usd=0.001,
        verificacion_ok=1,
    )
    corrida.registrar_artefactos(programa)
    corrida.finalizar(estado="entregada")

    # Assert
    corridas = _corridas(tmp_path, seguimiento.EXPERIMENTO_GENERACION)
    assert len(corridas) == 1
    registrada = corridas[0]
    assert registrada.data.params["modelo"] == "deepseek-v4-pro"
    assert registrada.data.params["familia"] == "spacer"
    assert registrada.data.metrics["latencia_ms"] == pytest.approx(12.5)
    assert registrada.data.metrics["verificacion_ok"] == pytest.approx(1.0)
    assert registrada.data.tags["estado"] == "entregada"
    assert registrada.data.tags["solicitud_id"] == "abc"
    artefactos = [item.path for item in _cliente(tmp_path).list_artifacts(corrida.id)]
    assert "programa.json" in artefactos


def test_corrida_cerrada_nunca_queda_en_running(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path)

    # Act
    corrida = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    corrida.finalizar(estado="declinada", motivo_declinacion="tipo fuera del catálogo")

    # Assert
    corridas = _corridas(tmp_path, seguimiento.EXPERIMENTO_GENERACION)
    estados = [registrada.info.status for registrada in corridas]
    assert estados == ["FINISHED"]
    tags = corridas[0].data.tags
    assert tags["estado"] == "declinada"
    assert tags["motivo_declinacion"] == "tipo fuera del catálogo"


def test_texto_registrado_se_sanitiza(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path)
    pii = "me llamo Juan Polanco y escribo a juan@correo.com por una brida"

    # Act
    corrida = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION,
        nombre=pii,
        tags={"solicitud_id": pii},
        configuracion=configuracion,
    )
    corrida.registrar_params(modelo=pii)
    corrida.registrar_tags(nota=pii)
    corrida.finalizar(estado="entregada")

    # Assert
    registrada = _corridas(tmp_path, seguimiento.EXPERIMENTO_GENERACION)[0]
    textos = [
        registrada.data.tags["solicitud_id"],
        registrada.data.tags["nota"],
        registrada.data.params["modelo"],
        registrada.info.run_name,
    ]
    assert all("juan@correo.com" not in texto for texto in textos)
    assert all("Juan Polanco" not in texto for texto in textos)
    assert "[correo eliminado]" in registrada.data.tags["nota"]
    assert "[nombre eliminado]" in registrada.data.tags["nota"]


def test_servidor_inalcanzable_no_propaga_y_advierte(tmp_path, caplog):
    # Arrange
    caplog.set_level(logging.WARNING, logger="m2_cad.seguimiento")
    configuracion = seguimiento.Configuracion(uri="http://127.0.0.1:9")

    # Act
    corrida = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    corrida.registrar_metricas(latencia_ms=1.0)
    corrida.finalizar(estado="entregada")

    # Assert
    assert corrida.activa is False
    assert corrida.fallos >= 1
    assert any("seguimiento" in mensaje for mensaje in caplog.messages)


def test_metricas_descartan_none_y_valores_no_finitos(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path)

    # Act
    corrida = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    corrida.registrar_metricas(tokens_entrada=None, latencia_ms=float("nan"), costo_usd="no-numero")
    corrida.finalizar(estado="error")

    # Assert
    assert _corridas(tmp_path, seguimiento.EXPERIMENTO_GENERACION)[0].data.metrics == {}


def test_costo_usd_usa_precios_por_millon_de_tokens():
    # Act
    costo = seguimiento.costo_usd(1_000_000, 1_000_000, precio_entrada=0.1, precio_salida=0.4)

    # Assert
    assert costo == pytest.approx(0.5)
    assert seguimiento.costo_usd(None, None) == 0.0


def test_version_de_modelo_se_registra_una_vez_y_liga_la_corrida(tmp_path):
    # Arrange
    configuracion = _configuracion(tmp_path)

    # Act
    primera = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    primera.registrar_params(modelo="deepseek-v4-pro")
    primera.finalizar(estado="entregada")
    registrada = seguimiento.registrar_version_modelo(
        nombre="m2-cad-deepseek-v4-pro",
        version="deepseek-v4-pro",
        corrida_id=primera.id,
        fuente=f"runs:/{primera.id}",
        configuracion=configuracion,
    )
    segunda = seguimiento.iniciar_corrida(
        seguimiento.EXPERIMENTO_GENERACION, configuracion=configuracion
    )
    segunda.finalizar(estado="declinada")
    repetida = seguimiento.registrar_version_modelo(
        nombre="m2-cad-deepseek-v4-pro",
        version="deepseek-v4-pro",
        corrida_id=segunda.id,
        fuente=f"runs:/{segunda.id}",
        configuracion=configuracion,
    )

    # Assert
    assert registrada == "m2-cad-deepseek-v4-pro/v1"
    assert repetida == "m2-cad-deepseek-v4-pro/v1"
    versiones = _cliente(tmp_path).search_model_versions("name='m2-cad-deepseek-v4-pro'")
    assert [str(version.version) for version in versiones] == ["1"]
    assert versiones[0].tags["version_modelo"] == "deepseek-v4-pro"


def test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms(tmp_path):
    """AC6: la sobrecarga (contra el modo desactivado) es ≤ 50 ms p95.

    Se mide la diferencia con la misma secuencia en modo no-op para que la carga
    de la máquina afecte a ambas muestras y no alumbra una cifra de AC6.
    """
    configuracion = _configuracion(tmp_path)
    desactivado = _configuracion(tmp_path, activo=False)

    def ciclo(activa) -> float:
        inicio = time.perf_counter()
        corrida = seguimiento.iniciar_corrida(
            activa.experimento_generacion,
            nombre="medicion",
            tags={"solicitud_id": "medicion"},
            configuracion=activa,
        )
        corrida.registrar_params(
            modelo="deepseek-v4-pro", version_modelo="v1", familia="spacer", temperatura=0.1
        )
        corrida.registrar_metricas(
            latencia_ms=10.0,
            tokens_entrada=100,
            tokens_salida=50,
            costo_usd=0.0,
            verificacion_ok=1,
        )
        corrida.finalizar(estado="entregada")
        return (time.perf_counter() - inicio) * 1000

    ciclo(configuracion)  # calienta la importación de mlflow y el experimento
    muestras = sorted(ciclo(configuracion) - ciclo(desactivado) for _ in range(12))
    p95 = muestras[int(0.95 * (len(muestras) - 1))]

    assert p95 <= 50.0, f"p95={p95:.1f} ms muestras={[round(m, 1) for m in muestras]}"
