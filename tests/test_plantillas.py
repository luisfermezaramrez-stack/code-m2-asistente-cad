"""SPEC-050 (HU-49) RF-1, RF-3 y RF-4: catálogo versionado y parámetros.

El catálogo es un archivo de datos verificado en CI; las plantillas guardadas viven
en un índice con propietario. Sin red, sin API key y sin GPU.
"""

import json
from pathlib import Path

import pytest

from m2_cad import materiales, pipeline, plantillas

FAMILIAS = ("plate", "sheet_bracket", "adapter", "flange", "spacer", "screw")


@pytest.fixture(autouse=True)
def _indice_aislado(tmp_path, monkeypatch):
    """Cada prueba escribe su propio índice de plantillas guardadas."""
    monkeypatch.setenv("M2_PLANTILLAS_JSON", str(tmp_path / "plantillas.json"))


def test_el_catalogo_versionado_no_tiene_problemas():
    assert plantillas.verificar() == []


def test_hay_una_plantilla_por_familia_del_banco():
    catalogo = plantillas.cargar_catalogo()

    assert sorted(plantilla["tipo"] for plantilla in catalogo.values()) == sorted(FAMILIAS)


def test_cada_plantilla_declara_tipo_material_y_parametros():
    for plantilla in plantillas.cargar_catalogo().values():
        parte = plantilla["programa"]["parts"][0]
        assert parte["type"] in pipeline.CATALOGO
        assert parte["material"] in materiales.SOPORTADOS
        assert plantilla["parametros"], plantilla["id"]
        for parametro in plantilla["parametros"]:
            assert parametro["nombre"] in parte["params"]
            assert parametro["unidad"] in ("mm", "u")
            assert parametro["minimo"] <= parametro["defecto"] <= parametro["maximo"]


def test_la_placa_de_ac1_tiene_agujeros_y_espesor_con_minimo():
    placa = plantillas.cargar_catalogo()["placa-con-agujeros"]
    params = placa["programa"]["parts"][0]["params"]
    nombres = {parametro["nombre"]: parametro for parametro in placa["parametros"]}

    assert {"bolt_d", "bolt_circle", "bolt_count"} <= set(params)
    assert nombres["thick"]["minimo"] == 2
    assert nombres["thick"]["maximo"] == 50


def test_instanciar_toma_los_valores_y_conserva_el_resto():
    placa = plantillas.cargar_catalogo()["placa-con-agujeros"]

    programa = plantillas.instanciar(placa, {"width": 60, "depth": 50, "thick": 6})
    params = programa["parts"][0]["params"]

    assert (params["width"], params["depth"], params["thick"]) == (60, 50, 6)
    assert params["bolt_count"] == placa["programa"]["parts"][0]["params"]["bolt_count"]
    assert programa["parts"][0]["material"] == "steel"


@pytest.mark.parametrize(("nombre", "valor"), [("width", 0.5), ("depth", 10), ("thick", 1)])
def test_ac2_un_valor_fuera_de_rango_nombra_parametro_valor_y_rango(nombre, valor):
    placa = plantillas.cargar_catalogo()["placa-con-agujeros"]

    with pytest.raises(plantillas.ErrorParametro) as info:
        plantillas.instanciar(placa, {nombre: valor})

    mensaje = str(info.value)
    assert nombre in mensaje
    assert "entre" in mensaje
    assert "mm" in mensaje
    assert str(valor) in mensaje


def test_un_parametro_desconocido_se_rechaza_con_su_nombre():
    placa = plantillas.cargar_catalogo()["placa-con-agujeros"]

    with pytest.raises(plantillas.ErrorParametro) as info:
        plantillas.instanciar(placa, {"grosor": 6})

    assert "grosor" in str(info.value)


def test_un_contador_no_acepta_fracciones():
    placa = plantillas.cargar_catalogo()["placa-con-agujeros"]

    with pytest.raises(plantillas.ErrorParametro) as info:
        plantillas.instanciar(placa, {"bolt_count": 3.5})

    assert "bolt_count" in str(info.value)
    assert "entero" in str(info.value)


def test_derivar_parametros_expone_los_numericos_con_mas_menos_50():
    programa = {
        "parts": [
            {
                "id": "p",
                "type": "spacer",
                "material": "steel",
                "params": {"outer_d": 30, "bore_d": 12, "height": 20},
            }
        ],
        "mates": [],
    }

    parametros = {p["nombre"]: p for p in plantillas.derivar_parametros(programa)}

    assert parametros["outer_d"]["defecto"] == 30
    assert parametros["outer_d"]["minimo"] == 15
    assert parametros["outer_d"]["maximo"] == 45
    assert parametros["height"]["unidad"] == "mm"


def test_derivar_parametros_no_expone_textos_booleanos_ni_apagados():
    programa = {
        "parts": [
            {
                "id": "p",
                "type": "screw",
                "material": "steel",
                "params": {
                    "size": "M5-0.8",
                    "length": 20,
                    "simple": True,
                    "fastener_type": "iso4762",
                    "boss_d": 0,
                },
            }
        ],
        "mates": [],
    }

    nombres = {p["nombre"] for p in plantillas.derivar_parametros(programa)}

    assert nombres == {"length"}


def test_derivar_parametros_marca_los_enteros():
    programa = {
        "parts": [
            {
                "id": "p",
                "type": "plate",
                "material": "steel",
                "params": {"width": 100, "bolt_count": 4},
            }
        ],
        "mates": [],
    }

    parametros = {p["nombre"]: p for p in plantillas.derivar_parametros(programa)}

    assert parametros["bolt_count"]["entero"] is True
    assert parametros["width"]["entero"] is False


def test_guardar_listar_y_obtener_la_propia():
    programa = plantillas.instanciar(
        plantillas.cargar_catalogo()["placa-con-agujeros"], {"thick": 8}
    )

    guardada = plantillas.guardar("ana", "Mi placa", programa)

    assert guardada["usuario"] == "ana"
    assert [p["id"] for p in plantillas.listar_guardadas("ana")] == [guardada["id"]]
    assert plantillas.obtener(guardada["id"], "ana")["nombre"] == "Mi placa"
    assert plantillas.obtener("placa-con-agujeros", "ana")["origen"] == "catalogo"


def test_un_usuario_no_ve_ni_obtiene_la_plantilla_de_otro():
    guardada = plantillas.guardar(
        "ana", "Mi placa", plantillas.cargar_catalogo()["placa-con-agujeros"]["programa"]
    )

    assert plantillas.listar_guardadas("beto") == []
    with pytest.raises(plantillas.ErrorPlantilla) as info:
        plantillas.obtener(guardada["id"], "beto")
    assert "no existe" in str(info.value)


def test_el_indice_guardado_es_acumulativo_y_no_expone_el_usuario_en_la_lista():
    programa = plantillas.cargar_catalogo()["espaciador"]["programa"]
    primera = plantillas.guardar("ana", "Uno", programa)
    segunda = plantillas.guardar("ana", "Dos", programa)

    assert [p["id"] for p in plantillas.listar_guardadas("ana")] == [primera["id"], segunda["id"]]
    datos = json.loads(Path(plantillas.ruta_guardadas()).read_text(encoding="utf-8"))
    assert datos["version"] == 1
    assert all("programa" in entrada for entrada in datos["plantillas"])


def test_los_tipos_del_catalogo_existen_en_el_pipeline():
    """La lista liviana de tipos no puede despegarse del `CATALOGO` real (SPEC-050)."""
    assert set(plantillas.FAMILIA_DEL_TIPO) <= set(pipeline.CATALOGO)


@pytest.mark.parametrize("plantilla_id", sorted(plantillas.cargar_catalogo()))
def test_cada_plantilla_del_catalogo_pasa_el_verificador_con_sus_defectos(plantilla_id):
    """RF-2: el programa base de cada plantilla pasa la misma verificación que el texto."""
    plantilla = plantillas.cargar_catalogo()[plantilla_id]

    informe = pipeline.verificar_programa(plantillas.instanciar(plantilla))

    assert informe is not None


def test_un_valor_fuera_de_la_lista_permitida_nombra_los_permitidos():
    brida = plantillas.cargar_catalogo()["brida"]

    with pytest.raises(plantillas.ErrorParametro) as info:
        plantillas.instanciar(brida, {"flange_class": 200})

    mensaje = str(info.value)
    assert "flange_class" in mensaje
    assert "150, 300, 400" in mensaje
    assert "200" in mensaje
    assert (
        plantillas.instanciar(brida, {"flange_class": 300})["parts"][0]["params"]["flange_class"]
        == 300
    )


def test_verificar_detecta_valores_permitidos_fuera_del_rango(tmp_path):
    texto = Path(plantillas.RUTA_CATALOGO).read_text(encoding="utf-8")
    roto = tmp_path / "plantillas.toml"
    roto.write_text(
        texto.replace("valores = [150, 300, 400, 600, 900, 1500, 2500]", "valores = [150, 9000]"),
        encoding="utf-8",
    )

    problemas = plantillas.verificar(roto)

    assert any("flange_class" in problema for problema in problemas)


def test_un_entero_enorme_se_rechaza_como_parametro_y_no_como_fallo():
    placa = plantillas.cargar_catalogo()["placa-con-agujeros"]

    with pytest.raises(plantillas.ErrorParametro) as info:
        plantillas.instanciar(placa, {"width": 10**400})

    assert "width" in str(info.value)


def test_una_brida_guardada_hereda_los_valores_permitidos_del_catalogo():
    programa = plantillas.instanciar(plantillas.cargar_catalogo()["brida"])

    parametros = {p["nombre"]: p for p in plantillas.derivar_parametros(programa)}

    clase = parametros["flange_class"]
    assert clase["valores"] == [150, 300, 400, 600, 900, 1500, 2500]
    assert clase["unidad"] == "u"
    assert clase["entero"] is True
    assert clase["defecto"] == 150
    with pytest.raises(plantillas.ErrorParametro):
        plantillas.instanciar({"programa": programa, "parametros": [clase]}, {"flange_class": 200})
