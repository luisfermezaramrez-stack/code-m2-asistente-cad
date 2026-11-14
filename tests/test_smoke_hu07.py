"""Smoke SIMULADO: contrato de caso único, conservación y correlación; sin inferencia."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import httpx


def _script():
    spec = importlib.util.spec_from_file_location(
        "smoke_hu07", Path(__file__).resolve().parents[1] / "scripts/smoke_hu07.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_smoke_un_post_y_evidencias_con_mlflow_sin_crear_otras_corridas(tmp_path):
    enviados = []
    identificador = None

    def responder(request):
        nonlocal identificador
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/openapi.json":
            return httpx.Response(
                200,
                json={
                    "paths": dict.fromkeys(
                        [
                            "/generar",
                            "/registros/{identificador}",
                            "/registros/{identificador}/step",
                        ]
                    )
                },
            )
        if request.method == "POST":
            enviados.append(json.loads(request.content))
            identificador = request.headers["X-Request-ID"]
            return httpx.Response(
                200,
                headers={"X-Registro-ID": identificador},
                json={
                    "step": "outputs/pieza.step",
                    "volumen_mm3": "6000",
                    "caja_mm": "40x30x5",
                },
            )
        if request.url.path.endswith("/step"):
            return httpx.Response(200, content=b"STEP SIMULADO")
        return httpx.Response(200, json={"id": identificador, "traduccion": "no aplica"})

    def buscar(ids, *, filter_string):
        assert ids == ["1"]
        assert filter_string == f"tags.solicitud_id = '{identificador}'"
        return [
            SimpleNamespace(
                info=SimpleNamespace(run_id="corrida-simulada", status="FINISHED"),
                data=SimpleNamespace(metrics={"tokens_entrada": 100, "tokens_salida": 20}),
            )
        ]

    tracking = SimpleNamespace(
        get_experiment_by_name=lambda nombre: SimpleNamespace(experiment_id="1"),
        search_runs=buscar,
    )
    with httpx.Client(
        base_url="http://simulado", transport=httpx.MockTransport(responder)
    ) as cliente:
        resultado, carpeta = _script().ejecutar_smoke(
            cliente, tracking, salida=tmp_path, mlflow_ui="http://mlflow-simulado"
        )
    assert len(enviados) == 1 and set(enviados[0]) == {"texto"}
    assert "40 mm en X" in enviados[0]["texto"]
    assert resultado["categoria"] == "conforme"
    assert resultado["step_conservado"] and resultado["mlflow_confirmado"]
    assert resultado["mlflow"]["url"].endswith("/runs/corrida-simulada")
    assert (carpeta / "pieza.step").read_bytes() == b"STEP SIMULADO"
    assert (carpeta / "registro.json").is_file()
    assert json.loads((carpeta / "resultado.json").read_text(encoding="utf-8")) == resultado


def test_smoke_sin_api_no_envia_generacion(tmp_path):
    peticiones = []

    def responder(request):
        peticiones.append(request.method)
        return httpx.Response(503)

    import pytest

    with httpx.Client(
        base_url="http://simulado", transport=httpx.MockTransport(responder)
    ) as cliente:
        with pytest.raises(httpx.HTTPStatusError):
            _script().ejecutar_smoke(cliente, None, salida=tmp_path, mlflow_ui="http://simulado")
    assert peticiones == ["GET"]
    assert list(tmp_path.iterdir()) == []
