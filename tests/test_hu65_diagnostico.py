"""SPEC-066 (HU-65): el despliegue se diagnostica en vez de mentir.

Readyness con datos versionados y motivo público para fallos conocidos del pipeline.
"""

import pytest
from fastapi.testclient import TestClient

from m2_cad import api, materiales
from m2_cad.errores_publicos import MENSAJE_DATOS, motivo_publico
from m2_cad.pipeline import ErrorGeneracion, ModeloNoDisponible


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "credencial-simulada")
    with TestClient(api.app) as test_client:
        yield test_client


def test_datos_versionados_presentes_ready_ok(cliente):
    respuesta = cliente.get("/ready")

    assert respuesta.status_code == 200
    assert respuesta.json()["dependencias"]["datos"] == "ok"


def test_tabla_de_materiales_ausente_ready_503(cliente, monkeypatch, tmp_path):
    monkeypatch.setenv("M2_MATERIALES", str(tmp_path / "no-existe.toml"))

    respuesta = cliente.get("/ready")

    assert respuesta.status_code == 503
    assert respuesta.json()["status"] == "no_disponible"
    assert respuesta.json()["dependencias"]["datos"] == "no_disponible"
    # El registro y el modelo siguen informando su propio estado.
    assert respuesta.json()["dependencias"]["registro"] == "ok"


def test_catalogo_de_plantillas_ausente_ready_503(cliente, monkeypatch, tmp_path):
    monkeypatch.setenv("M2_PLANTILLAS", str(tmp_path / "no-existe.toml"))

    respuesta = cliente.get("/ready")

    assert respuesta.status_code == 503
    assert respuesta.json()["dependencias"]["datos"] == "no_disponible"


def test_health_no_depende_de_los_datos(cliente, monkeypatch, tmp_path):
    monkeypatch.setenv("M2_MATERIALES", str(tmp_path / "no-existe.toml"))

    assert cliente.get("/health").json() == {"status": "ok"}


def test_falta_de_materiales_no_expone_la_ruta_interna():
    exc = materiales.ErrorMateriales("no existe la tabla de materiales: /app/data/materiales.toml")

    motivo = motivo_publico(exc)

    assert motivo == MENSAJE_DATOS
    assert "/app/data" not in motivo


def test_modelo_no_disponible_conserva_su_mensaje():
    assert motivo_publico(ModeloNoDisponible("El modelo respondió con error HTTP 400.")) == (
        "El modelo respondió con error HTTP 400."
    )


def test_error_de_generacion_conserva_su_mensaje():
    assert motivo_publico(ErrorGeneracion("La salida del modelo no es un programa.")) == (
        "La salida del modelo no es un programa."
    )


def test_fallo_desconocido_sigue_siendo_generico():
    assert motivo_publico(RuntimeError("Traceback interno con rutas")) is None
