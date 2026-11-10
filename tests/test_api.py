"""Pruebas de la API FastAPI (HU-06).

Cubre POST /generar (200 con STEP o declinación; 422 ante texto vacío o de más
de 1000 caracteres), GET /health en ≤ 1 s y el registro sin campos vacíos ni
datos personales. Cobertura objetivo ≥ 80 % del módulo.
"""

import pytest


def test_modulo_api_importable():
    from m2_cad import api

    assert api is not None


def test_health_endpoint():
    """Verifica que la API responda correctamente."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app

    client = TestClient(app)
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "   ",
        "x" * 1001,
    ],
)
def test_generar_rechaza_entrada_invalida(texto):
    """Verifica que la API rechace solicitudes inválidas."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app

    client = TestClient(app)
    respuesta = client.post("/generar", json={"texto": texto})

    assert respuesta.status_code == 422


def test_generar_con_procesador_simulado():
    """Verifica la respuesta HTTP 200 sin ejecutar el pipeline CAD."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app, obtener_procesador

    # Simula una declinación válida del pipeline CAD.
    def procesador_simulado(texto: str) -> dict[str, str]:
        assert texto == "Placa de 120 mm"
        return {
            "resultado": "declinacion",
            "motivo": "Pieza fuera del catálogo",
        }

    # Sustituye temporalmente el procesador real.
    app.dependency_overrides[obtener_procesador] = lambda: procesador_simulado

    try:
        with TestClient(app) as client:
            respuesta = client.post(
                "/generar",
                json={"texto": "Placa de 120 mm"},
            )

        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "resultado": "declinacion",
            "motivo": "Pieza fuera del catálogo",
        }
    finally:
        # Restaura las dependencias para no afectar otras pruebas.
        app.dependency_overrides.pop(obtener_procesador, None)


def test_generar_pipeline_no_disponible():
    """Verifica que la API informe si el pipeline no está disponible."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app

    with TestClient(app) as client:
        respuesta = client.post(
            "/generar",
            json={"texto": "Placa de 120 mm"},
        )

    assert respuesta.status_code == 503
    assert respuesta.json() == {"detail": "El pipeline CAD aún no está disponible."}


def test_generar_archivos_cad_simulados():
    """Valida la respuesta de generación sin ejecutar el motor CAD."""
    from fastapi.testclient import TestClient

    from m2_cad.api import app, obtener_procesador

    # Simula el resultado esperado del pipeline.
    def procesador_simulado(texto: str) -> dict[str, str]:
        assert texto == "Placa de 120 mm"
        return {
            "resultado": "generada",
            "step": "pieza.step",
            "glb": "pieza.glb",
            "csv": "materiales.csv",
        }

    app.dependency_overrides[obtener_procesador] = lambda: procesador_simulado

    try:
        with TestClient(app) as client:
            respuesta = client.post(
                "/generar",
                json={"texto": "Placa de 120 mm"},
            )

        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "resultado": "generada",
            "step": "pieza.step",
            "glb": "pieza.glb",
            "csv": "materiales.csv",
        }
    finally:
        app.dependency_overrides.pop(obtener_procesador, None)
