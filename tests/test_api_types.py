"""SPEC-028: divergencias reales del esquema y preservación del contrato HTTP/SSE."""

import copy
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from m2_cad import api
from m2_cad.contratos import EstadoTrabajo
from m2_cad.trabajos import GestorTrabajos, Trabajo


@pytest.fixture(scope="module")
def generator():
    spec = importlib.util.spec_from_file_location(
        "generate_api_types", Path(__file__).resolve().parents[1] / "scripts/generate_api_types.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cambio_de_campo_sin_regenerar_falla_sin_modificar_versionado(generator, tmp_path, capsys):
    # AC1: usar el generador real, no un doble que dé por cierta la divergencia.
    schema = api.app.openapi()
    original = generator.generate_types(schema)
    destination = tmp_path / "api.ts"
    generator.synchronize(original, destination, check=False)
    changed = copy.deepcopy(schema)
    model = changed["components"]["schemas"]["EstadoTrabajo"]
    model["properties"]["etapa_nueva"] = model["properties"].pop("estado")
    model["required"].remove("estado")
    model["required"].append("etapa_nueva")

    regenerated = generator.generate_types(changed)

    assert "etapa_nueva:" in regenerated
    assert generator.synchronize(regenerated, destination, check=True) == 1
    assert "make api-types" in capsys.readouterr().err
    assert destination.read_text(encoding="utf-8") == original
    generator.synchronize(regenerated, destination, check=False)
    assert generator.synchronize(regenerated, destination, check=True) == 0


def test_generacion_determinista_y_versionada(generator):
    schema = api.app.openapi()
    first = generator.generate_types(schema)
    assert first == generator.generate_types(schema)
    assert generator.synchronize(first, generator.DESTINATION, check=True) == 0


def test_openapi_comparte_modelo_entre_consulta_cancelacion_y_data_sse():
    schema = api.app.openapi()
    paths = schema["paths"]
    reference = {"$ref": "#/components/schemas/EstadoTrabajo"}
    for method, code in [("get", "200"), ("delete", "200"), ("delete", "202")]:
        response = paths["/generaciones/{solicitud_id}"][method]["responses"][code]
        assert response["content"]["application/json"]["schema"] == reference
    content = paths["/generar"]["post"]["responses"]["200"]["content"]
    assert content["text/event-stream"]["x-event-data-schema"] == reference
    assert content["text/event-stream"]["schema"] == {"type": "string"}


def test_consulta_y_cancelacion_preservan_campos_ausentes_y_codigos():
    # Un trabajo sin hilo evita carreras y comprueba el estado inicial real.
    manager = GestorTrabajos()
    job = Trabajo()
    manager._trabajos[job.id] = job
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: manager
    try:
        with TestClient(api.app) as client:
            initial = client.get(f"/generaciones/{job.id}")
            assert initial.status_code == 200
            assert initial.json() == job.estado()
            assert "resultado" not in initial.json() and "secuencia" not in initial.json()
            cancel = client.delete(f"/generaciones/{job.id}")
            assert cancel.status_code == 202
            assert cancel.json() == job.estado()
            job.ejecutar("Pieza", lambda *_: pytest.fail("No debe generar"), lambda _: None)
            terminal = client.delete(f"/generaciones/{job.id}")
            assert terminal.status_code == 200
            assert terminal.json() == job.estado()
            assert terminal.json()["cancelacion_remota_confirmada"] is False
    finally:
        api.app.dependency_overrides.pop(api.obtener_gestor_trabajos, None)


@pytest.mark.parametrize("state", ["verificado", "declinado", "error", "cancelado"])
def test_modelo_acepta_eventos_terminales_reales_sin_insertar_campos(state):
    from m2_cad.control import GeneracionCancelada, SolicitudDeclinada

    job = Trabajo()

    def process(text, control):
        control.informar("validando")
        control.informar("generando")
        if state == "cancelado":
            raise GeneracionCancelada()
        if state == "declinado":
            raise SolicitudDeclinada("Fuera del catálogo")
        if state == "error":
            raise ValueError("Fallo simulado")
        return {"step": "pieza.step", "aviso": "Diseño preliminar"}

    job.ejecutar("Placa", process, lambda _: None)
    adapter = TypeAdapter(EstadoTrabajo)
    while not job._eventos.empty():
        event = job._eventos.get_nowait()
        assert adapter.validate_python(event) == event
    assert job.estado()["estado"] == state
