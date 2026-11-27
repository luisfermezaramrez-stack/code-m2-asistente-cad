"""Edición iterativa de la pieza por HTTP (HU-35, SPEC-036).

AC1: una edición verificada entrega una pieza nueva con el diff y conserva la anterior.
AC2: una edición que rompe la verificación declina con causa y no reemplaza la versión.
AC3: el historial lista las tres versiones en orden, con programa y artefactos.

Sin red, sin API key y sin GPU: el pipeline se sustituye por respuestas controladas.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _entorno(tmp_path, monkeypatch):
    """Aísla registro, versiones y MLflow en directorios temporales."""
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    monkeypatch.setenv("MLFLOW_DISABLE_AGENT_HINT", "1")
    monkeypatch.setenv("M2_VERSIONES_DIR", str(tmp_path / "versiones"))
    from m2_cad import api, seguimiento

    configuracion = seguimiento.configuracion_en(f"file:{tmp_path / 'mlruns'}")
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: configuracion
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    yield
    api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)


def _pieza(tmp_path: Path, *, thick: float) -> object:
    """ResultadoPieza con artefactos reales en un directorio propio por versión."""
    from m2_cad import pipeline

    salida = tmp_path / f"salida-{thick}"
    salida.mkdir(exist_ok=True)
    programa_json = salida / "programa.json"
    programa = {
        "parts": [
            {"id": "p", "type": "plate", "params": {"width": 40, "depth": 30, "thick": thick}}
        ],
        "mates": [],
    }
    programa_json.write_text(json.dumps(programa), encoding="utf-8")
    step = salida / "pieza.step"
    step.write_text("ISO-10303-21;\nEND-ISO-10303-21;", encoding="utf-8")
    glb = salida / "pieza.glb"
    glb.write_bytes(b"glTF")
    bom_csv = salida / "pieza.csv"
    bom_csv.write_text("type,cantidad\nplate,1\n", encoding="utf-8")
    return pipeline.ResultadoPieza(
        programa=programa,
        step=step,
        glb=glb,
        bom_csv=bom_csv,
        volumen_mm3=6000.0,
        caja_mm=(40.0, 30.0, thick),
        tiempo_construccion_s=0.1,
        tiempo_generacion_s=0.2,
        familia="plate",
        programa_json=programa_json,
    )


def _cliente_generado(tmp_path, monkeypatch, *, generar=None):
    """Cliente HTTP con una generación inicial ya entregada (versión 1)."""
    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline

    def generar_falso(texto, medir_uso=None):
        if medir_uso is not None:
            medir_uso({"prompt_tokens": 10, "completion_tokens": 5})
        return generar(tmp_path) if generar else _pieza(tmp_path, thick=5)

    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(pipeline, "generar_pieza", generar_falso)
    cliente = TestClient(api.app)
    cliente.__enter__()
    respuesta = cliente.post("/v1/generar", json={"texto": "Placa de 40x30x5 mm"})
    assert respuesta.status_code == 200
    # `/generar` publica el id de la solicitud en X-Registro-ID (HU-07).
    return cliente, respuesta.headers["X-Registro-ID"]


@pytest.fixture
def cliente_editando(tmp_path, monkeypatch):
    """Cliente con una generación inicial y una edición controlada."""
    from m2_cad import pipeline

    cliente, origen = _cliente_generado(tmp_path, monkeypatch)
    estado = {"programa": None}

    def editar_falso(programa_previo, instruccion, medir_uso=None):
        estado["programa"] = programa_previo
        estado["instruccion"] = instruccion
        if medir_uso is not None:
            medir_uso({"prompt_tokens": 12, "completion_tokens": 6})
        return _pieza(tmp_path, thick=10)

    monkeypatch.setattr(pipeline, "editar_pieza", editar_falso)
    yield cliente, origen, estado
    cliente.__exit__(None, None, None)


def test_ac1_la_edicion_entrega_pieza_nueva_con_diff_y_conserva_la_anterior(
    cliente_editando, tmp_path
):
    """AC1: 200 con diff, versión 2, y la versión 1 sigue en el historial."""
    cliente, origen, estado = cliente_editando

    respuesta = cliente.post(
        f"/v1/generar/{origen}/editar", json={"instruccion": "hazla 5 mm más gruesa"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["version"] == 2
    assert cuerpo["solicitud_id"] == origen
    assert cuerpo["programa"]["parts"][0]["params"]["thick"] == 10
    assert {"ruta": "parts[0].params.thick", "antes": 5, "despues": 10} in cuerpo["diff"]
    assert Path(cuerpo["step"]).is_file()
    assert estado["instruccion"] == "hazla 5 mm más gruesa"
    assert estado["programa"]["parts"][0]["params"]["thick"] == 5

    historial = cliente.get(f"/v1/generar/{origen}/versiones")
    assert [v["version"] for v in historial.json()["versiones"]] == [1, 2]
    assert historial.json()["versiones"][0]["programa"]["parts"][0]["params"]["thick"] == 5


def test_ac2_la_edicion_que_rompe_la_verificacion_declina_y_no_reemplaza(
    cliente_editando, monkeypatch
):
    """AC2: 422 con la causa de SPEC-027 y el historial intacto."""
    from m2_cad import declinacion, pipeline

    cliente, origen, _ = cliente_editando

    def romper(programa_previo, instruccion, medir_uso=None):
        raise pipeline.ErrorVerificacion(
            "part-build-error", causa=declinacion.Causa.DIMENSION_INCOHERENTE
        )

    monkeypatch.setattr(pipeline, "editar_pieza", romper)
    respuesta = cliente.post(f"/v1/generar/{origen}/editar", json={"instruccion": "hazla -5"})

    assert respuesta.status_code == 422
    assert (
        declinacion.QUE_HARIA_FALTA[declinacion.Causa.DIMENSION_INCOHERENTE]
        in (respuesta.json()["detail"])
    )
    historial = cliente.get(f"/v1/generar/{origen}/versiones").json()
    assert [v["version"] for v in historial["versiones"]] == [1]


def test_ac3_el_historial_lista_las_tres_versiones_en_orden(
    cliente_editando, monkeypatch, tmp_path
):
    """AC3: dos ediciones dejan tres versiones, cada una con programa y artefactos."""
    from m2_cad import pipeline

    cliente, origen, _ = cliente_editando
    gruesos = {"actual": 10}

    def editar(programa_previo, instruccion, medir_uso=None):
        gruesos["actual"] += 5
        return _pieza(tmp_path, thick=gruesos["actual"])

    monkeypatch.setattr(pipeline, "editar_pieza", editar)
    for instruccion in ("hazla 5 mm más gruesa", "otra vez 5 mm"):
        editada = cliente.post(f"/v1/generar/{origen}/editar", json={"instruccion": instruccion})
        assert editada.status_code == 200

    historial = cliente.get(f"/v1/generar/{origen}/versiones").json()

    assert [v["version"] for v in historial["versiones"]] == [1, 2, 3]
    for version in historial["versiones"]:
        assert version["programa"]["parts"][0]["type"] == "plate"
        assert version["artefactos"]
        assert version["prompt"]
        assert version["prompt_hash"]


def test_una_solicitud_inexistente_o_ajena_da_404(cliente_editando):
    """HU-53: ni editar ni ver versiones de otra solicitud."""
    cliente, _origen, _ = cliente_editando

    assert (
        cliente.post(
            "/v1/generar/00000000000000000000000000000000/editar", json={"instruccion": "x"}
        ).status_code
        == 404
    )
    assert cliente.get("/v1/generar/00000000000000000000000000000000/versiones").status_code == 404
    assert cliente.post("/v1/generar/../editar", json={"instruccion": "x"}).status_code == 404


def test_la_instruccion_vacia_o_larga_es_422_de_validacion(cliente_editando):
    """El cuerpo se valida con el mismo estilo que `/generar`."""
    cliente, origen, _ = cliente_editando

    vacia = cliente.post(f"/v1/generar/{origen}/editar", json={"instruccion": "  "})
    assert vacia.status_code == 422
    assert (
        cliente.post(f"/v1/generar/{origen}/editar", json={"instruccion": "x" * 1001}).status_code
        == 422
    )


def test_la_edicion_registra_la_fila_y_los_params_de_mlflow(cliente_editando, tmp_path):
    """RNF-3: la fila y la corrida llevan el prompt de edición y la versión."""
    from mlflow.tracking import MlflowClient

    from m2_cad import pipeline

    cliente, origen, _ = cliente_editando
    editada = cliente.post(
        f"/v1/generar/{origen}/editar", json={"instruccion": "hazla 5 mm más gruesa"}
    )
    assert editada.status_code == 200

    with (tmp_path / "registro.csv").open(newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    ultima = filas[-1]
    assert ultima["prompt"] == pipeline.PROMPT_EDICION.etiqueta
    assert ultima["prompt_hash"] == pipeline.PROMPT_EDICION.sha256

    cliente_mlflow = MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")
    from m2_cad import seguimiento

    experimento = cliente_mlflow.get_experiment_by_name(seguimiento.EXPERIMENTO_GENERACION)
    corridas = cliente_mlflow.search_runs([experimento.experiment_id])
    editada = [c for c in corridas if c.data.params.get("operacion") == "edicion"]
    assert len(editada) == 1
    assert editada[0].data.params["version_pieza"] == "2"
    assert editada[0].data.params["solicitud_origen"] == origen
    assert editada[0].data.params["prompt"] == pipeline.PROMPT_EDICION.etiqueta


def test_generar_conserva_su_contrato(tmp_path, monkeypatch):
    """RNF-2: `/generar` sigue devolviendo el mismo cuerpo de texto que antes."""

    cliente, origen = _cliente_generado(tmp_path, monkeypatch)
    try:
        respuesta = cliente.post("/v1/generar", json={"texto": "Placa de 40x30x5 mm"})
        assert respuesta.status_code == 200
        assert set(respuesta.json()) == {
            "step",
            "glb",
            "bom_csv",
            "aviso",
            "volumen_mm3",
            "caja_mm",
            "tiempo_generacion_s",
            "tiempo_construccion_s",
        }
        versiones = cliente.get(f"/v1/generar/{respuesta.headers['X-Registro-ID']}/versiones")
        assert versiones.status_code == 200
        assert origen
    finally:
        cliente.__exit__(None, None, None)


def test_la_idempotencia_de_la_edicion_no_duplica_la_version(cliente_editando):
    """HU-32: la misma clave no produce una segunda versión."""
    cliente, origen, _ = cliente_editando
    cabeceras = {"Idempotency-Key": "edicion-1"}

    primera = cliente.post(
        f"/v1/generar/{origen}/editar",
        json={"instruccion": "hazla 5 mm más gruesa"},
        headers=cabeceras,
    )
    segunda = cliente.post(
        f"/v1/generar/{origen}/editar",
        json={"instruccion": "hazla 5 mm más gruesa"},
        headers=cabeceras,
    )

    assert primera.status_code == 200
    assert segunda.status_code == 409
    historial = cliente.get(f"/v1/generar/{origen}/versiones").json()
    assert [v["version"] for v in historial["versiones"]] == [1, 2]


# --- Correcciones pedidas por la revisión de HU-35 (R3-reserva-ventana-404,
# --- R3-indice-corrupto-500, R2-002) ----------------------------------------


def test_los_404_no_consumen_la_ventana_de_uso(cliente_editando, monkeypatch):
    """R3-reserva-ventana-404: repetir ids sin historial no puede acabar en 429."""
    from m2_cad import api
    from m2_cad.control_uso import ConfiguracionUso

    cliente, origen, _ = cliente_editando
    control = api.ControlUso(
        ConfiguracionUso(
            limite_ventana=2,
            ventana_segundos=300,
            presupuesto_diario_usd=0.0,
        )
    )
    monkeypatch.setattr(api, "control_uso", control)
    api.app.dependency_overrides[api.obtener_control_uso] = lambda: control
    try:
        for _ in range(4):
            respuesta = cliente.get("/v1/generar/" + "0" * 32 + "/versiones")
            assert respuesta.status_code == 404
            editada = cliente.post(
                "/v1/generar/" + "0" * 32 + "/editar", json={"instruccion": "hazla más gruesa"}
            )
            assert editada.status_code == 404

        siguiente = cliente.post(
            f"/v1/generar/{origen}/editar", json={"instruccion": "hazla 5 mm más gruesa"}
        )
        assert siguiente.status_code == 200, siguiente.json()
    finally:
        api.app.dependency_overrides.pop(api.obtener_control_uso, None)


def test_un_indice_corrupto_es_un_error_catalogado(cliente_editando, tmp_path):
    """R3-indice-corrupto-500: un índice dañado responde 409 con mensaje, no 500."""
    cliente, origen, _ = cliente_editando
    indice = tmp_path / "versiones" / f"{origen}.json"
    indice.write_text("{esto no es json", encoding="utf-8")

    editada = cliente.post(f"/v1/generar/{origen}/editar", json={"instruccion": "hazla más gruesa"})
    historial = cliente.get(f"/v1/generar/{origen}/versiones")

    assert editada.status_code == 409
    assert "historial de versiones" in editada.json()["detail"]
    assert historial.status_code == 409
    assert "historial de versiones" in historial.json()["detail"]


def test_el_pipeline_no_queda_parchado_tras_las_pruebas_de_edicion():
    """R2-002: ninguna prueba deja `editar_pieza` reemplazado para las siguientes."""
    from m2_cad import pipeline

    assert pipeline.editar_pieza.__module__ == "m2_cad.pipeline"


# --- Bloqueos del verificador independiente de HU-35 (B1, B2, B3, B4) --------


def _procesador_de_cola(tmp_path, *, thick: float):
    """Procesador SSE mínimo: informa etapas, llena `medido` y devuelve la respuesta."""

    def procesar(texto, control, medido):
        from m2_cad import pipeline

        control.informar("validando")
        control.informar("generando")
        pieza = _pieza(tmp_path, thick=thick)
        medido.update(
            modelo=pieza.version_modelo,
            version_modelo="prueba",
            temperatura=0.1,
            familia=pieza.familia,
            prompt=pipeline.PROMPT_VIGENTE.etiqueta,
            prompt_hash=pipeline.PROMPT_VIGENTE.sha256,
            artefactos=[pieza.programa_json, pieza.step, pieza.glb, pieza.bom_csv],
            programa=pieza.programa,
        )
        return pieza.a_respuesta()

    return procesar


def test_b1_una_pieza_generada_por_el_worker_se_puede_editar(tmp_path, monkeypatch):
    """B1: con la cola activa, el worker deja la versión 1 y la SPA puede editar."""
    from dataclasses import asdict

    from fastapi.testclient import TestClient

    from m2_cad import api, cola_trabajos, seguimiento, worker

    monkeypatch.setenv("M2_COLA_HABILITADA", "1")
    monkeypatch.chdir(tmp_path)
    cola = cola_trabajos.ColaTrabajos(tmp_path / "cola.json", propietario="prueba-b1")
    monkeypatch.setattr(api, "cola_trabajos", cola)
    api.app.dependency_overrides[api.obtener_cola_trabajos] = lambda: cola
    ruta_registro = tmp_path / "registro.csv"
    try:
        trabajo = cola.encolar(
            "Placa de 40x30x5 mm",
            request_id="req-b1",
            configuracion=asdict(seguimiento.Configuracion(activo=False)),
            ruta_registro=str(ruta_registro),
            usuario="ana",
        )
        identificador = trabajo.id
        reclamado = cola.reclamar()
        assert reclamado is not None and reclamado["id"] == identificador
        worker.ejecutar(
            reclamado,
            _procesador_de_cola(tmp_path, thick=5),
            cola,
            ruta_registro=ruta_registro,
        )

        cliente = TestClient(api.app)
        cliente.__enter__()
        try:
            historial = cliente.get(f"/v1/generar/{identificador}/versiones")
            assert historial.status_code == 200, historial.json()
            assert [v["version"] for v in historial.json()["versiones"]] == [1]

            monkeypatch.setattr(
                "m2_cad.pipeline.editar_pieza", lambda *a, **k: _pieza(tmp_path, thick=10)
            )
            editada = cliente.post(
                f"/v1/generar/{identificador}/editar",
                json={"instruccion": "hazla 5 mm más gruesa"},
            )
            assert editada.status_code == 200, editada.json()
            assert editada.json()["version"] == 2
        finally:
            cliente.__exit__(None, None, None)
    finally:
        api.app.dependency_overrides.pop(api.obtener_cola_trabajos, None)


def test_b2_si_falla_la_escritura_del_indice_igual_registra_y_mide(
    cliente_editando, monkeypatch, tmp_path
):
    """B2: una edición construida sin poder archivarse deja fila, costo y corrida cerrada."""
    from mlflow.tracking import MlflowClient

    from m2_cad import seguimiento, versiones

    cliente, origen, _ = cliente_editando

    def roto(*args, **kwargs):
        raise versiones.ErrorVersiones("no hay espacio en el disco")

    monkeypatch.setattr(versiones, "registrar_version", roto)
    respuesta = cliente.post(
        f"/v1/generar/{origen}/editar", json={"instruccion": "hazla 5 mm más gruesa"}
    )

    assert respuesta.status_code == 409
    detalle = respuesta.json()["detail"]
    assert "no se pudo leer" not in detalle
    assert "no se pudo guardar" in detalle

    with (tmp_path / "registro.csv").open(newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert filas[-1]["texto"] == "hazla 5 mm más gruesa"
    assert filas[-1]["prompt"] == "editor-v1"

    cliente_mlflow = MlflowClient(tracking_uri=f"file:{tmp_path / 'mlruns'}")
    experimento = cliente_mlflow.get_experiment_by_name(seguimiento.EXPERIMENTO_GENERACION)
    corridas = list(cliente_mlflow.search_runs([experimento.experiment_id]))
    edicion = [c for c in corridas if c.data.params.get("operacion") == "edicion"]
    assert edicion, "la corrida de la edición tiene que existir"
    assert all(c.info.status == "FINISHED" for c in corridas), "ninguna corrida en RUNNING"
    assert edicion[0].data.metrics["verificacion_ok"] == pytest.approx(0.0)


def test_b3_un_indice_ajeno_corrupto_es_indistinguible_de_uno_inexistente(tmp_path, monkeypatch):
    """B3: con autenticación, el id ajeno da la misma respuesta que el desconocido."""
    import json
    import os

    from fastapi.testclient import TestClient

    from m2_cad import api, pipeline
    from m2_cad.autenticacion import hash_clave

    monkeypatch.setenv("M2_AUTH_ENABLED", "1")
    monkeypatch.setenv("M2_AUTH_SECRET", os.urandom(32).hex())
    monkeypatch.setenv(
        "M2_AUTH_USERS",
        json.dumps({"ana": hash_clave("clave-ana"), "bob": hash_clave("clave-bob")}),
    )
    monkeypatch.setenv("M2_AUTH_COOKIE_SECURE", "0")
    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    monkeypatch.setattr(
        pipeline, "generar_pieza", lambda texto, medir_uso=None: _pieza(tmp_path, thick=5)
    )

    ana = TestClient(api.app)
    ana.__enter__()
    try:
        acceso = ana.post("/v1/auth/login", json={"usuario": "ana", "clave": "clave-ana"})
        assert acceso.status_code == 200
        generada = ana.post("/v1/generar", json={"texto": "Placa de 40x30x5 mm"})
        assert generada.status_code == 200
        ajeno = generada.headers["X-Registro-ID"]
    finally:
        ana.__exit__(None, None, None)

    indice = tmp_path / "versiones" / f"{ajeno}.json"
    indice.write_text("{roto", encoding="utf-8")
    desconocido = "f" * 32

    bob = TestClient(api.app)
    bob.__enter__()
    try:
        acceso = bob.post("/v1/auth/login", json={"usuario": "bob", "clave": "clave-bob"})
        assert acceso.status_code == 200
        propio = bob.get(f"/v1/generar/{ajeno}/versiones")
        otro = bob.get(f"/v1/generar/{desconocido}/versiones")
        assert propio.status_code == 404
        assert propio.status_code == otro.status_code
        assert propio.json() == otro.json()

        editar_ajeno = bob.post(
            f"/v1/generar/{ajeno}/editar", json={"instruccion": "hazla más gruesa"}
        )
        editar_otro = bob.post(
            f"/v1/generar/{desconocido}/editar", json={"instruccion": "hazla más gruesa"}
        )
        assert editar_ajeno.status_code == 404
        assert editar_ajeno.status_code == editar_otro.status_code
        assert editar_ajeno.json() == editar_otro.json()
    finally:
        bob.__exit__(None, None, None)
