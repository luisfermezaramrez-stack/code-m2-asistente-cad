"""Panorama de métricas por HTTP (HU-51, SPEC-052).

AC1: los agregados de la ventana salen de las corridas de MLflow.
AC2: con el seguimiento apagado o MLflow caído responde un estado degradado, no un 500.
Sin red, sin API key y sin GPU: MLflow corre contra un file store temporal.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Configuración de MLflow en un file store temporal y API apuntando a ella."""
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    from m2_cad import api, seguimiento

    configuracion = seguimiento.configuracion_en(f"file:{tmp_path / 'mlruns'}")
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: configuracion
    yield configuracion
    api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)


def _corrida(configuracion, *, estado, causa=None, latencia=800.0, costo=0.001, familia="plate"):
    """Crea una corrida cerrada con los datos que el panorama debe agregar."""
    from m2_cad import seguimiento

    corrida = seguimiento.iniciar_corrida(
        configuracion.experimento_generacion,
        nombre=f"caso-{estado}-{causa or 'ok'}",
        tags={"solicitud_id": "x", "estado": estado},
        configuracion=configuracion,
    )
    corrida.registrar_params(familia=familia, prompt="planner-v1")
    corrida.registrar_metricas(latencia_ms=latencia, costo_usd=costo)
    corrida.finalizar(estado=estado, motivo_declinacion=causa, causa_declinacion=causa)
    return corrida


def test_ac1_los_agregados_salen_de_las_corridas_de_mlflow(entorno):
    """AC1: totales, desglose por causa, latencia media y costo de la ventana."""
    from fastapi.testclient import TestClient

    from m2_cad import api

    _corrida(entorno, estado="entregada", latencia=1000.0, costo=0.002)
    _corrida(entorno, estado="entregada", latencia=500.0, costo=0.001)
    _corrida(entorno, estado="declinada", causa="familia_no_soportada")
    _corrida(entorno, estado="declinada", causa="dimension_incoherente")

    with TestClient(api.app) as cliente:
        respuesta = cliente.get("/v1/metricas")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["disponible"] is True
    assert cuerpo["motivo"] is None
    assert cuerpo["solicitudes"] == 4
    assert cuerpo["entregadas"] == 2
    assert cuerpo["declinadas"] == 2
    assert cuerpo["errores"] == 0
    assert cuerpo["entregadas_por_familia"] == {"plate": 2}
    assert cuerpo["declinaciones_por_causa"] == {
        "dimension_incoherente": 1,
        "familia_no_soportada": 1,
    }
    esperada = (1000.0 + 500.0 + 800.0 + 800.0) / 4
    assert cuerpo["latencia_media_ms"] == pytest.approx(esperada, rel=1e-6)
    assert cuerpo["costo_usd"] == pytest.approx(0.002 + 0.001 + 0.001 + 0.001, rel=1e-6)
    assert cuerpo["mlflow_ui"].startswith("http://")
    assert cuerpo["desde"] < cuerpo["hasta"]


def test_ac2_con_el_seguimiento_apagado_responde_degradado(entorno):
    """AC2: sin MLflow el panorama es explícito y no rompe la respuesta."""
    from fastapi.testclient import TestClient

    from m2_cad import api, seguimiento

    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )

    with TestClient(api.app) as cliente:
        respuesta = cliente.get("/v1/metricas")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["disponible"] is False
    assert "seguimiento" in cuerpo["motivo"].lower()
    assert cuerpo["solicitudes"] == 0
    assert cuerpo["costo_usd"] == 0.0
    assert cuerpo["declinaciones_por_causa"] == {}


def test_ac2_con_mlflow_caido_responde_degradado(entorno, tmp_path):
    """AC2: un MLflow inaccesible también es estado degradado, nunca 500."""
    from fastapi.testclient import TestClient

    from m2_cad import api, seguimiento

    rota = seguimiento.configuracion_en(f"file:{tmp_path / 'no-existe' / 'mlruns'}")
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: rota

    with TestClient(api.app) as cliente:
        respuesta = cliente.get("/v1/metricas")

    assert respuesta.status_code == 200
    assert respuesta.json()["disponible"] is False


@pytest.mark.parametrize("horas", [0, -1, 721, 10000])
def test_la_ventana_fuera_de_rango_es_422(entorno, horas):
    """La ventana se valida en el contrato, no en el cuerpo de la respuesta."""
    from fastapi.testclient import TestClient

    from m2_cad import api

    with TestClient(api.app) as cliente:
        assert cliente.get(f"/v1/metricas?horas={horas}").status_code == 422


def test_los_agregados_no_llevan_textos_ni_datos_personales(entorno):
    """RNF-3: el panorama agrega; no devuelve el texto de la solicitud ni usuarios."""
    from fastapi.testclient import TestClient

    from m2_cad import api, seguimiento

    corrida = seguimiento.iniciar_corrida(
        entorno.experimento_generacion,
        nombre="caso-pii",
        tags={"solicitud_id": "x", "estado": "declinada", "usuario": "ana@example.com"},
        configuracion=entorno,
    )
    corrida.registrar_metricas(latencia_ms=10.0)
    corrida.finalizar(estado="declinada", causa_declinacion="texto_ambiguo")

    with TestClient(api.app) as cliente:
        texto = json.dumps(cliente.get("/v1/metricas").json())

    assert "@" not in texto
    assert "ana" not in texto.lower()
    assert "texto" not in texto.lower() or "texto_ambiguo" in texto
