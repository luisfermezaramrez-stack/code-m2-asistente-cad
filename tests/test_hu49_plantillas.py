"""SPEC-050 (HU-49) AC1-AC3: instanciar plantillas sin LLM, guardar y aislar.

El modelo se simula y se comprueba que **no** se invoca al instanciar (RNF-1). Sin
red, sin API key y sin GPU.
"""

import csv
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from m2_cad import api, corpus_dorado, pipeline, plantillas, seguimiento

PROGRAMA = {
    "parts": [
        {
            "id": "p",
            "type": "plate",
            "material": "steel",
            "params": {
                "width": 100,
                "depth": 60,
                "thick": 8,
                "boss_d": 0,
                "boss_h": 0,
                "bolt_d": 10,
                "bolt_circle": 70,
                "bolt_count": 4,
            },
        }
    ],
    "mates": [],
}
COLUMNAS_HISTORICAS = ["part_type", "qty", "total_mass_g", "unit_mass_g"]


@pytest.fixture(autouse=True)
def _entorno(tmp_path, monkeypatch):
    """Aísla seguimiento, registro, versiones y plantillas guardadas."""
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )
    monkeypatch.setattr(api, "RUTA_DEFAULT", tmp_path / "registro.csv")
    monkeypatch.setenv("M2_PLANTILLAS_JSON", str(tmp_path / "plantillas.json"))
    monkeypatch.setenv("M2_VERSIONES_DIR", str(tmp_path / "versiones"))
    # `/generar` exige un modelo configurado; el modelo real nunca se llama (doble).
    monkeypatch.setenv("LLM_BASE_URL", "http://llama:8080")
    # Las piezas instanciadas se construyen en el temporal, nunca en `outputs/`.
    construir = pipeline.construir_desde_programa
    monkeypatch.setattr(
        pipeline,
        "construir_desde_programa",
        lambda programa: construir(programa, directorio=tmp_path / "salidas"),
    )
    yield
    api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)
    api.app.dependency_overrides.pop(api.usuario_actual, None)


def _modelo_simulado(destino: Path, llamadas: list) -> object:
    def generar(texto: str, **kwargs: object) -> object:
        llamadas.append(texto)
        return pipeline.construir_pieza(PROGRAMA, destino)

    return generar


def test_ac1_instanciar_la_placa_entrega_pieza_y_no_llama_al_modelo(tmp_path, monkeypatch):
    llamadas: list = []
    monkeypatch.setattr(pipeline, "generar_pieza", _modelo_simulado(tmp_path / "texto", llamadas))
    cliente = TestClient(api.app)

    respuesta = cliente.post(
        "/v1/plantillas/placa-con-agujeros/instanciar",
        json={"valores": {"width": 60, "depth": 50, "thick": 6}},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    for clave in ("step", "glb", "bom_csv"):
        assert Path(cuerpo[clave]).is_file(), clave
    assert llamadas == [], "instanciar una plantilla no puede invocar al modelo"
    assert cuerpo["tiempo_generacion_s"] == "0.000"
    assert cuerpo["firma"]["volume"] == pytest.approx(float(cuerpo["volumen_mm3"]), rel=1e-6)

    with open(cuerpo["bom_csv"], encoding="utf-8") as archivo:
        filas = list(csv.reader(archivo))
    assert filas[0][:4] == COLUMNAS_HISTORICAS, "el BOM conserva su prefijo histórico"
    assert filas[1][4] == "steel"


def test_ac2_la_api_rechaza_un_espesor_bajo_el_minimo_con_su_rango(tmp_path):
    cliente = TestClient(api.app)

    respuesta = cliente.post(
        "/v1/plantillas/placa-con-agujeros/instanciar",
        json={"valores": {"thick": 1}},
    )

    assert respuesta.status_code == 422
    detalle = str(respuesta.json()["detail"])
    assert "thick" in detalle
    assert "2" in detalle and "50" in detalle


def test_ac2_un_parametro_fuera_de_rango_nunca_llega_a_construir(tmp_path, monkeypatch):
    def construir_prohibido(*args: object, **kwargs: object) -> object:
        raise AssertionError("un valor fuera de rango no puede llegar a construir")

    monkeypatch.setattr(pipeline, "construir_desde_programa", construir_prohibido)
    cliente = TestClient(api.app)

    respuesta = cliente.post(
        "/v1/plantillas/placa-con-agujeros/instanciar",
        json={"valores": {"thick": 51}},
    )

    assert respuesta.status_code == 422
    assert "thick" in respuesta.json()["detail"]
    assert not (tmp_path / "registro.csv").exists(), "un rechazo previo no deja registro"


def test_ac2_una_plantilla_inexistente_responde_404(tmp_path):
    cliente = TestClient(api.app)

    assert cliente.post("/v1/plantillas/no-existe/instanciar", json={}).status_code == 404


def test_ac3_guardar_una_pieza_y_reinstanciarla_reproduce_la_firma(tmp_path, monkeypatch):
    llamadas: list = []
    monkeypatch.setattr(pipeline, "generar_pieza", _modelo_simulado(tmp_path / "texto", llamadas))
    cliente = TestClient(api.app)
    solicitud_id = str(uuid.uuid4())

    generada = cliente.post(
        "/v1/generar",
        json={"texto": "placa de 100 x 60 x 8"},
        headers={"X-Request-ID": solicitud_id},
    )
    assert generada.status_code == 200
    original = generada.json()

    guardada = cliente.post(
        "/v1/plantillas", json={"solicitud_id": solicitud_id, "nombre": "Mi placa"}
    )
    assert guardada.status_code == 200
    plantilla = guardada.json()
    assert plantilla["nombre"] == "Mi placa"
    assert plantilla["tipo"] == "plate"
    valores = {parametro["nombre"]: parametro["defecto"] for parametro in plantilla["parametros"]}

    instancia = cliente.post(
        f"/v1/plantillas/{plantilla['id']}/instanciar", json={"valores": valores}
    )

    assert instancia.status_code == 200
    copia = instancia.json()
    assert corpus_dorado.huella_step(Path(original["step"])) == corpus_dorado.huella_step(
        Path(copia["step"])
    )
    assert float(copia["volumen_mm3"]) == pytest.approx(float(original["volumen_mm3"]), rel=1e-6)


def test_el_catalogo_sale_con_origen_y_las_guardadas_aparecen(tmp_path):
    cliente = TestClient(api.app)
    guardada = plantillas.guardar(
        "anónimo", "Mía", plantillas.cargar_catalogo()["espaciador"]["programa"]
    )

    plantillas_de_la_api = cliente.get("/v1/plantillas").json()["plantillas"]
    origenes = {p["id"]: p["origen"] for p in plantillas_de_la_api}

    assert origenes["placa-con-agujeros"] == "catalogo"
    assert origenes[guardada["id"]] == "guardada"
    assert all(p["parametros"] for p in plantillas_de_la_api)


def test_la_lista_nunca_expone_propietario_ni_programa(tmp_path):
    cliente = TestClient(api.app)
    plantillas.guardar("anónimo", "Mía", plantillas.cargar_catalogo()["espaciador"]["programa"])

    respuesta = cliente.get("/v1/plantillas")

    assert respuesta.status_code == 200
    for plantilla in respuesta.json()["plantillas"]:
        assert set(plantilla) == {
            "id",
            "nombre",
            "descripcion",
            "tipo",
            "familia",
            "origen",
            "parametros",
        }
        assert "usuario" not in str(plantilla) and "programa" not in str(plantilla)


def test_un_usuario_no_ve_ni_instancia_la_plantilla_de_otro(tmp_path, monkeypatch):
    monkeypatch.setenv("M2_AUTH_ENABLED", "1")
    ajena = plantillas.guardar(
        "ana", "Suya", plantillas.cargar_catalogo()["espaciador"]["programa"]
    )
    api.app.dependency_overrides[api.usuario_actual] = lambda: "beto"
    cliente = TestClient(api.app)

    catalogo = cliente.get("/v1/plantillas").json()["plantillas"]
    assert all(p["origen"] == "catalogo" for p in catalogo)
    assert ajena["id"] not in {p["id"] for p in catalogo}
    assert cliente.post(f"/v1/plantillas/{ajena['id']}/instanciar", json={}).status_code == 404

    api.app.dependency_overrides[api.usuario_actual] = lambda: "ana"
    propia = cliente.get("/v1/plantillas").json()["plantillas"]
    assert ajena["id"] in {p["id"] for p in propia}


def test_guardar_una_solicitud_ajena_responde_404(tmp_path, monkeypatch):
    monkeypatch.setenv("M2_AUTH_ENABLED", "1")
    monkeypatch.setattr(pipeline, "generar_pieza", _modelo_simulado(tmp_path / "texto", []))
    cliente = TestClient(api.app)
    solicitud_id = str(uuid.uuid4())
    api.app.dependency_overrides[api.usuario_actual] = lambda: "ana"
    assert (
        cliente.post(
            "/v1/generar", json={"texto": "placa"}, headers={"X-Request-ID": solicitud_id}
        ).status_code
        == 200
    )

    api.app.dependency_overrides[api.usuario_actual] = lambda: "beto"
    respuesta = cliente.post(
        "/v1/plantillas", json={"solicitud_id": solicitud_id, "nombre": "Robada"}
    )

    assert respuesta.status_code == 404


def test_el_flujo_por_texto_y_las_versiones_siguen_igual(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "generar_pieza", _modelo_simulado(tmp_path / "texto", []))
    cliente = TestClient(api.app)
    solicitud_id = str(uuid.uuid4())

    generada = cliente.post(
        "/v1/generar", json={"texto": "placa"}, headers={"X-Request-ID": solicitud_id}
    )

    assert generada.status_code == 200
    assert Path(generada.json()["step"]).is_file()
    historial = cliente.get(f"/v1/generar/{solicitud_id}/versiones")
    assert historial.status_code == 200
    assert historial.json()["versiones"][0]["programa"]["parts"][0]["type"] == "plate"
    assert cliente.get("/v1/health").status_code == 200
