"""Seguimiento MLflow de POST /generar (specs/009-hu-16-mlflow: AC2, AC3, AC5).

Corre offline contra un file store temporal: una corrida por solicitud, cierre con
estado entregada/declinada/error y artefactos de la pieza cuando se construye.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _entorno_mlflow(tmp_path, monkeypatch):
    """File store temporal, registro aislado y API apuntando a esa configuración."""
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    from m2_cad import api, seguimiento

    configuracion = seguimiento.configuracion_en(f"file:{tmp_path / 'mlruns'}")
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: configuracion
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    yield
    api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)


def _corridas(tmp_path):
    """Corridas del experimento de generación, ya ordenadas por fecha."""
    from mlflow.tracking import MlflowClient

    from m2_cad import seguimiento

    cliente = MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")
    experimento = cliente.get_experiment_by_name(seguimiento.EXPERIMENTO_GENERACION)
    if experimento is None:
        return []
    return cliente.search_runs([experimento.experiment_id])


def _pieza(tmp_path, *, familia="spacer"):
    """Resultado de pipeline con artefactos reales en disco."""
    from m2_cad import pipeline

    salida = tmp_path / "salida"
    salida.mkdir(exist_ok=True)
    programa_json = salida / "programa.json"
    programa_json.write_text('{"parts": [{"type": "spacer"}]}', encoding="utf-8")
    step = salida / "pieza.step"
    step.write_text("ISO-10303-21;\nEND-ISO-10303-21;", encoding="utf-8")
    glb = salida / "pieza.glb"
    glb.write_bytes(b"glTF")
    bom_csv = salida / "pieza.csv"
    bom_csv.write_text("type,cantidad\nspacer,1\n", encoding="utf-8")
    return pipeline.ResultadoPieza(
        programa={"parts": [{"type": "spacer"}], "mates": []},
        step=step,
        glb=glb,
        bom_csv=bom_csv,
        volumen_mm3=1256.64,
        caja_mm=(14.0, 14.0, 10.0),
        tiempo_construccion_s=0.1,
        tiempo_generacion_s=0.2,
        familia=familia,
        programa_json=programa_json,
    )


def test_solicitud_entregada_registra_params_metricas_tags_y_artefactos(tmp_path, monkeypatch):
    """AC2: una corrida por solicitud con los campos y artefactos declarados."""
    pytest.importorskip("cadquery")
    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline, seguimiento

    def generar_falso(texto, medir_uso=None):
        if medir_uso is not None:
            medir_uso({"prompt_tokens": 120, "completion_tokens": 40})
        return _pieza(tmp_path)

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", generar_falso)

    with TestClient(api.app) as client:
        respuesta = client.post("/generar", json={"texto": "Espaciador de 14 mm"})

    assert respuesta.status_code == 200
    corridas = _corridas(tmp_path)
    assert len(corridas) == 1
    corrida = corridas[0]
    assert corrida.info.status == "FINISHED"
    assert corrida.data.params["modelo"] == pipeline.llm.planner_model()
    assert corrida.data.params["version_modelo"] == seguimiento.version_modelo()
    assert corrida.data.params["familia"] == "spacer"
    assert float(corrida.data.params["temperatura"]) == pytest.approx(pipeline.TEMPERATURA_LLM)
    assert corrida.data.metrics["tokens_entrada"] == pytest.approx(120.0)
    assert corrida.data.metrics["tokens_salida"] == pytest.approx(40.0)
    assert corrida.data.metrics["verificacion_ok"] == pytest.approx(1.0)
    assert corrida.data.metrics["latencia_ms"] > 0
    assert corrida.data.tags["estado"] == "entregada"
    assert corrida.data.tags["solicitud_id"]

    from mlflow.tracking import MlflowClient

    cliente = MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")
    artefactos = {item.path for item in cliente.list_artifacts(corrida.info.run_id)}
    assert {"programa.json", "pieza.step", "pieza.glb", "pieza.csv"} <= artefactos


def test_declinacion_cierra_la_corrida_con_motivo(tmp_path, monkeypatch):
    """AC3: estado=declinada con motivo_declinacion y verificacion_ok=0."""
    pytest.importorskip("cadquery")
    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline

    motivo = "los ensamblajes de varias piezas están fuera del alcance."

    def declinar(texto, medir_uso=None):
        exc = pipeline.PiezaDeclinada(motivo)
        exc.programa_json = tmp_path / "programa.json"
        raise exc

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", declinar)

    with TestClient(api.app) as client:
        respuesta = client.post("/generar", json={"texto": "Ensamble de dos bridas"})

    assert respuesta.status_code == 422
    assert "Pieza declinada" in respuesta.json()["detail"]
    corrida = _corridas(tmp_path)[0]
    assert corrida.info.status == "FINISHED"
    assert corrida.data.tags["estado"] == "declinada"
    assert motivo in corrida.data.tags["motivo_declinacion"]
    assert corrida.data.metrics["verificacion_ok"] == pytest.approx(0.0)


def test_fallo_tecnico_cierra_la_corrida_con_la_clase_del_error(tmp_path, monkeypatch):
    """AC3: estado=error, tag error con la clase y ninguna corrida en RUNNING."""
    pytest.importorskip("cadquery")
    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline

    def fallar(texto, medir_uso=None):
        raise pipeline.ErrorVerificacion("unknown part type")

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", fallar)

    with TestClient(api.app) as client:
        respuesta = client.post("/generar", json={"texto": "Engranaje helicoidal"})

    assert respuesta.status_code == 422
    corridas = _corridas(tmp_path)
    assert [corrida.info.status for corrida in corridas] == ["FINISHED"]
    assert corridas[0].data.tags["estado"] == "error"
    assert corridas[0].data.tags["error"] == "ErrorVerificacion"


def test_sin_modelo_configurado_registra_la_corrida_como_error(tmp_path, monkeypatch):
    """AC3: el 503 por falta de API key también cierra la corrida en error."""
    from fastapi.testclient import TestClient

    from m2_cad import api

    for variable in ("LLM_BASE_URL", "LLM_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(variable, raising=False)

    with TestClient(api.app) as client:
        respuesta = client.post("/generar", json={"texto": "Placa de 120 mm"})

    assert respuesta.status_code == 503
    corrida = _corridas(tmp_path)[0]
    assert corrida.info.status == "FINISHED"
    assert corrida.data.tags["estado"] == "error"
    assert corrida.data.tags["error"] == "ModeloNoDisponible"


def test_el_registro_no_conserva_la_version_desconocida(tmp_path, monkeypatch):
    """AC7: la fila del CSV registra el modelo servido, no 'desconocida'."""
    from fastapi.testclient import TestClient

    from m2_cad import api, seguimiento

    api.app.dependency_overrides[api.obtener_procesador] = lambda: (
        lambda texto, medicion=None: {"resultado": "generada"}
    )
    try:
        with TestClient(api.app) as client:
            client.post("/generar", json={"texto": "Placa de 120 mm"})
    finally:
        api.app.dependency_overrides.pop(api.obtener_procesador, None)

    import csv

    with (tmp_path / "registro.csv").open(newline="", encoding="utf-8") as archivo:
        fila = next(csv.DictReader(archivo))
    assert fila["version"] == seguimiento.version_modelo()
    assert fila["version"] != "desconocida"


def test_excepcion_inesperada_cierra_la_corrida_y_no_bloquea_la_siguiente(tmp_path):
    """AC3: un fallo que no es HTTP también cierra la corrida con estado=error.

    Sin el cierre, la corrida quedaba en RUNNING y, como MLflow guarda la corrida
    activa por hilo, la siguiente solicitud de ese hilo no podía abrir la suya.
    """
    from fastapi.testclient import TestClient

    from m2_cad import api

    def explotar(texto, medicion=None):
        raise RuntimeError("fallo inesperado del kernel")

    api.app.dependency_overrides[api.obtener_procesador] = lambda: explotar
    try:
        with TestClient(api.app, raise_server_exceptions=False) as client:
            primera = client.post("/generar", json={"texto": "Placa de 100 x 50 x 5 mm"})
            segunda = client.post("/generar", json={"texto": "Placa de 80 x 40 x 4 mm"})
    finally:
        api.app.dependency_overrides.pop(api.obtener_procesador, None)

    assert primera.status_code == segunda.status_code == 500
    corridas = _corridas(tmp_path)
    assert [corrida.info.status for corrida in corridas] == ["FINISHED", "FINISHED"]
    assert {corrida.data.tags["estado"] for corrida in corridas} == {"error"}
    assert {corrida.data.tags["error"] for corrida in corridas} == {"RuntimeError"}


def test_solicitud_ligada_a_la_version_de_modelo_registrada(tmp_path, monkeypatch):
    """AC7: la corrida de generación queda ligada a la versión de modelo servida."""
    pytest.importorskip("cadquery")
    from fastapi.testclient import TestClient
    from mlflow.tracking import MlflowClient

    from m2_cad import api, pipeline, seguimiento

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", lambda texto, medir_uso=None: _pieza(tmp_path))

    with TestClient(api.app) as client:
        for texto in ("Espaciador de 14 mm", "Espaciador de 20 mm"):
            assert client.post("/generar", json={"texto": texto}).status_code == 200

    referencia = f"m2-cad-{pipeline.llm.planner_model()}/v1"
    assert {c.data.tags.get("modelo_registrado") for c in _corridas(tmp_path)} == {referencia}

    cliente = MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")
    nombre = seguimiento.nombre_modelo_registrado(f"m2-cad-{pipeline.llm.planner_model()}")
    assert len(cliente.search_model_versions(f"name='{nombre}'")) == 1


def _post_sse(texto):
    from fastapi.testclient import TestClient

    from m2_cad import api

    with TestClient(api.app) as client:
        return client.post(
            "/generar", json={"texto": texto}, headers={"Accept": "text/event-stream"}
        )


def test_solicitud_sse_entregada_registra_su_corrida(tmp_path, monkeypatch):
    """HU-15 + HU-16: la ruta SSE también deja una corrida cerrada con sus métricas."""
    pytest.importorskip("cadquery")
    from m2_cad import pipeline

    def generar_falso(texto, *, control, medir_uso=None):
        control.informar("validando")
        control.informar("generando")
        medir_uso({"prompt_tokens": 90, "completion_tokens": 30})
        return _pieza(tmp_path)

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", generar_falso)

    respuesta = _post_sse("Espaciador de 14 mm")

    assert respuesta.status_code == 200
    assert "event: verificado" in respuesta.text
    corridas = _corridas(tmp_path)
    assert len(corridas) == 1
    corrida = corridas[0]
    assert corrida.info.status == "FINISHED"
    assert corrida.data.tags["estado"] == "entregada"
    assert corrida.data.tags["transporte"] == "sse"
    assert corrida.data.tags["solicitud_id"] in respuesta.text
    assert corrida.data.params["familia"] == "spacer"
    assert corrida.data.metrics["tokens_entrada"] == pytest.approx(90.0)
    assert corrida.data.metrics["verificacion_ok"] == pytest.approx(1.0)


def test_solicitud_sse_declinada_cierra_la_corrida_con_su_motivo(tmp_path, monkeypatch):
    """AC3 en SSE: la declinación cierra la corrida con estado y motivo."""
    pytest.importorskip("cadquery")
    from m2_cad import pipeline

    def generar_falso(texto, *, control, medir_uso=None):
        control.informar("validando")
        control.informar("generando")
        raise pipeline.PiezaDeclinada("engranaje fuera de catálogo")

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", generar_falso)

    respuesta = _post_sse("Engranaje helicoidal")

    assert "event: declinado" in respuesta.text
    corridas = _corridas(tmp_path)
    assert len(corridas) == 1
    assert corridas[0].info.status == "FINISHED"
    assert corridas[0].data.tags["estado"] == "declinada"
    assert corridas[0].data.tags["motivo_declinacion"] == "engranaje fuera de catálogo"
    assert corridas[0].data.metrics["verificacion_ok"] == pytest.approx(0.0)
