"""SPEC-044 AC2: el cajetín del PDF lleva el id de solicitud y el material canónico.

Pruebas de interfaz pública: la de B1 pasa por la ruta `POST /generar` (JSON)
con el pipeline real (el modelo se simula con un planificador doble) y por el
mismo mecanismo de contexto que usan las rutas SSE (`trabajos.py`) y el worker
(`worker.py`) al fijar `contexto_solicitud(..., job_id=...)`. Sin red, sin GPU.
"""

import uuid

import pytest


def _programa(**material):
    """Programa DSL de placa; `material` permite pedir alias/minúsculas."""
    return {
        "parts": [
            {
                "id": "p",
                "type": "plate",
                "material": material.get("material", "steel"),
                "params": {"width": 40, "depth": 20, "thick": 6},
            }
        ],
        "mates": [],
    }


@pytest.fixture(scope="module")
def placa(tmp_path_factory):
    """La pieza construida con el pipeline real, sin LLM."""
    from m2_cad import pipeline

    return pipeline.construir_pieza(_programa(), tmp_path_factory.mktemp("placa"))


def _texto_cajetin(resultado):
    """Extrae el texto del PDF entregado con pypdf."""
    import pypdf

    return pypdf.PdfReader(resultado.pdf).pages[0].extract_text() or ""


# ---------- B1 (AC2/RF-2): el id real de la solicitud en el cajetín ----------


def test_b1_contextojob_id_cajetin_con_el_id_real(tmp_path):
    """B1: como `trabajos.py` (SSE) y `worker.py` fijan `job_id` en el contexto.

    El id llega al cajetín sin parámetro: `construir_pieza` lo toma del
    contexto de ejecución, la misma vía que ambas rutas ya usan.
    """
    from m2_cad import pipeline
    from m2_cad.observabilidad import contexto_solicitud

    with contexto_solicitud(request_id="req-1", job_id="sol-worker-77"):
        resultado = pipeline.generar_pieza(
            "Placa de 40x20x6 mm",
            planificar=lambda texto: _programa(),
            directorio=tmp_path,
        )

    texto = _texto_cajetin(resultado)
    assert "sol-worker-77" in texto
    assert "SOLICITUD: —" not in texto


def test_b1_api_json_cajetin_con_el_id_real(tmp_path, monkeypatch):
    """B1: por la API pública, el cajetín muestra el id de la solicitud (RF-2)."""
    pytest.importorskip("cadquery")
    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline

    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    # El modelo se simula: el planificador doble devuelve el programa sin red.
    monkeypatch.setattr(
        pipeline, "_planificador_con_uso", lambda medir_uso, control=None: lambda texto: _programa()
    )
    id_solicitud = uuid.uuid4().hex
    api.app.dependency_overrides[api.obtener_procesador] = lambda: api.procesar_con_pipeline
    try:
        with TestClient(api.app) as cliente:
            respuesta = cliente.post(
                "/generar",
                json={"texto": "Placa de 40x20x6 mm"},
                headers={"X-Request-ID": id_solicitud},
            )
    finally:
        api.app.dependency_overrides.clear()
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["X-Registro-ID"] == id_solicitud

    import pypdf

    texto = pypdf.PdfReader(respuesta.json()["pdf"]).pages[0].extract_text() or ""
    assert id_solicitud in texto


def test_b1_sin_id_de_solicitud_el_cajetin_conserva_su_neutro(tmp_path):
    """Retrocompatibilidad: sin parámetro ni contexto, el cajetín sigue con «—»."""
    from m2_cad import pipeline

    respuesta = pipeline.construir_pieza(_programa(), tmp_path)
    assert "SOLICITUD: —" in _texto_cajetin(respuesta)
    # Y el parámetro explícito gana a un contexto que no lo es.
    resultado = pipeline.construir_pieza(_programa(), tmp_path / "otra", solicitud_id="sol-42")
    assert "sol-42" in _texto_cajetin(resultado)


# ---------- B2 (AC2/RF-2): material canónico de HU-48 en el cajetín ----------


def test_b2_cajetin_muestra_el_material_canonico(tmp_path):
    """B2: el guard de HU-48 (`verificar_programa` → `validar_materiales`) normaliza
    el alias antes de construir; el cajetín refleja el canónico, no el pedido."""
    from m2_cad import pipeline

    resultado = pipeline.generar_pieza(
        "Placa de 40x20x6 mm",
        planificar=lambda texto: _programa(material="al"),
        directorio=tmp_path,
    )

    texto = _texto_cajetin(resultado)
    assert "MATERIAL: aluminum" in texto
    assert "MATERIAL: al\n" not in texto
