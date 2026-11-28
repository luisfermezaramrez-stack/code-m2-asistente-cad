"""SPEC-031 AC3: readiness local sin conectarse a DeepSeek ni usar CAD."""

import pytest
from fastapi.testclient import TestClient

from m2_cad import api


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    with TestClient(api.app) as test_client:
        yield test_client


def test_ac3_modelo_sin_configurar_devuelve_503_y_health_sigue_ok(cliente, monkeypatch):
    for variable in ("DEEPSEEK_API_KEY", "LLM_API_KEY", "LLM_BASE_URL"):
        monkeypatch.delenv(variable, raising=False)

    respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    assert respuesta.json()["dependencias"]["modelo"] == "no_disponible"
    assert respuesta.json()["dependencias"]["registro"] == "ok"
    assert cliente.get("/health").json() == {"status": "ok"}


def test_ac3_modelo_configurado_y_registro_accesible(cliente, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "credencial-simulada")
    respuesta = cliente.get("/ready")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "status": "ok",
        "dependencias": {"modelo": "ok", "registro": "ok", "datos": "ok"},
    }


def test_ac3_registro_inaccesible_devuelve_503(cliente, monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "credencial-simulada")
    archivo = tmp_path / "obstaculo"
    archivo.write_text("No es un directorio", encoding="utf-8")
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: archivo / "registro.csv")
    respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    assert respuesta.json()["dependencias"]["registro"] == "no_disponible"
    assert cliente.get("/health").status_code == 200


def test_ac3_no_expone_credenciales_en_respuesta(cliente, monkeypatch):
    secreto_simulado = "credencial-simulada-secreta"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secreto_simulado)
    respuesta = cliente.get("/ready")
    assert respuesta.status_code == 200
    assert secreto_simulado not in respuesta.text
