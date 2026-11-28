"""SPEC-049 (HU-48) AC2, AC3 y RNF-3: material en el BOM y guard de material.

El BOM se escribe en M2 (no via `constraint_kit.bom`) pre-agregando por tipo y
material. El modelo no se invoca: se construye un programa DSL a mano.
"""

import csv
from pathlib import Path

import pytest
from constraint_kit.parts import DENSITY_G_MM3

from m2_cad import declinacion, materiales, pipeline

COLUMNAS_PREVIAS = ["part_type", "qty", "total_mass_g", "unit_mass_g"]
COLUMNAS_NUEVAS = ["material", "unit_cost_usd", "total_cost_usd"]


def _programa(material: object, *, tipo: str = "plate") -> dict:
    params = (
        {"width": 100, "depth": 50, "thick": 5}
        if tipo == "plate"
        else {"outer_d": 20, "bore_d": 8, "height": 10}
    )
    parte: dict = {"id": "p", "type": tipo, "params": params}
    if material is not None:
        parte["material"] = material
    return {"parts": [parte], "mates": []}


def _filas(ruta: Path) -> list[list[str]]:
    with open(ruta, encoding="utf-8") as archivo:
        return list(csv.reader(archivo))


def test_ac2_el_csv_lleva_material_masa_y_costo(tmp_path):
    resultado = pipeline.construir_pieza(_programa("aluminum"), tmp_path)
    filas = _filas(resultado.bom_csv)

    assert filas[0] == COLUMNAS_PREVIAS + COLUMNAS_NUEVAS
    linea = filas[1]
    assert linea[0] == "plate"
    assert linea[1] == "1"
    assert linea[4] == "aluminum"

    masa_esperada = resultado.volumen_mm3 * DENSITY_G_MM3["aluminum"]
    assert float(linea[2]) == pytest.approx(masa_esperada, abs=0.05)
    assert float(linea[3]) == pytest.approx(masa_esperada, abs=0.05)

    costo_esperado = round(
        masa_esperada / 1000 * materiales.cargar()["aluminum"]["precio_usd_kg"], 2
    )
    assert float(linea[5]) == pytest.approx(costo_esperado, abs=0.02)
    assert float(linea[6]) == pytest.approx(costo_esperado, abs=0.02)

    total = filas[-1]
    assert total[0] == "TOTAL"
    assert total[1] == "1"
    assert float(total[2]) == pytest.approx(masa_esperada, abs=0.05)
    assert total[4] == ""
    assert float(total[6]) == pytest.approx(costo_esperado, abs=0.02)


def test_la_masa_usa_la_densidad_del_material_no_la_del_acero(tmp_path):
    aluminio = _filas(pipeline.construir_pieza(_programa("aluminum"), tmp_path / "al").bom_csv)
    acero = _filas(pipeline.construir_pieza(_programa("steel"), tmp_path / "st").bom_csv)

    proporcion = float(aluminio[1][2]) / float(acero[1][2])
    assert proporcion == pytest.approx(DENSITY_G_MM3["aluminum"] / DENSITY_G_MM3["steel"], rel=1e-3)


def test_el_alias_al_llega_al_csv_como_aluminum(tmp_path):
    filas = _filas(pipeline.construir_pieza(_programa("al"), tmp_path).bom_csv)

    assert filas[1][4] == "aluminum"


def test_el_csv_agrupa_por_tipo_y_material_y_suma_el_total():
    partes = [
        {"type": "plate", "material": "steel", "mass_g": 100.0},
        {"type": "plate", "material": "steel", "mass_g": 100.0},
        {"type": "spacer", "material": "aluminum", "mass_g": 10.0},
    ]

    texto = pipeline._csv_materiales(pipeline._resumen_materiales(partes))
    filas = list(csv.reader(texto.splitlines()))

    assert filas[0] == COLUMNAS_PREVIAS + COLUMNAS_NUEVAS
    assert [fila[:2] + [fila[4]] for fila in filas[1:3]] == [
        ["plate", "2", "steel"],
        ["spacer", "1", "aluminum"],
    ]
    precio_acero = materiales.cargar()["steel"]["precio_usd_kg"]
    assert float(filas[1][3]) == pytest.approx(100.0)
    assert float(filas[1][6]) == pytest.approx(round(200.0 / 1000 * precio_acero, 2))
    assert filas[3] == []
    assert filas[4][0] == "TOTAL"
    assert filas[4][1] == "3"
    assert float(filas[4][2]) == pytest.approx(210.0)


@pytest.mark.parametrize("ajeno", ["titanium", "iron", "petg", "acero", "bronze"])
def test_ac3_declina_un_material_no_soportado_nombrandolo(ajeno, tmp_path):
    with pytest.raises(pipeline.PiezaDeclinada) as info:
        pipeline.construir_pieza(_programa(ajeno), tmp_path)

    assert ajeno in str(info.value)
    assert info.value.causa is declinacion.Causa.MATERIAL_NO_SOPORTADO
    assert not (tmp_path / "pieza.csv").exists()


def test_ac3_el_motivo_declara_que_haria_falta(tmp_path):
    with pytest.raises(pipeline.PiezaDeclinada) as info:
        pipeline.construir_pieza(_programa("titanium"), tmp_path)

    mensaje = str(info.value)
    assert "titanium" in mensaje
    assert "material" in mensaje.lower()
    assert declinacion.Causa.MATERIAL_NO_SOPORTADO.value in {
        causa.value for causa in declinacion.Causa
    }


def test_un_programa_sin_material_sigue_usando_acero(tmp_path):
    filas = _filas(pipeline.construir_pieza(_programa(None), tmp_path).bom_csv)

    assert filas[1][4] == "steel"


def test_rnf3_el_consumidor_previo_lee_sus_cuatro_columnas(tmp_path):
    resultado = pipeline.construir_pieza(_programa("steel"), tmp_path)

    with open(resultado.bom_csv, encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        assert list(lector.fieldnames or [])[:4] == COLUMNAS_PREVIAS
        primera = next(lector)

    # Las claves que el formato anterior garantizaba siguen existiendo y con su valor.
    assert primera["part_type"] == "plate"
    assert primera["qty"] == "1"
    assert float(primera["total_mass_g"]) > 0
    assert float(primera["unit_mass_g"]) > 0


def test_una_tabla_de_precios_ilegible_es_error_del_servicio(tmp_path, monkeypatch):
    """Un archivo de precios roto no puede culpar al usuario ni inventar el costo."""
    monkeypatch.setenv("M2_MATERIALES", str(tmp_path / "no-existe.toml"))

    with pytest.raises(pipeline.ErrorPipeline) as info:
        pipeline.construir_pieza(_programa("steel"), tmp_path)

    assert "no existe la tabla de materiales" in str(info.value)


def test_un_programa_declinado_no_pasa_por_el_guard(tmp_path):
    """Los casos `declina` del corpus llegan como {"unsupported": …}: sin partes."""
    with pytest.raises(pipeline.PiezaDeclinada) as info:
        pipeline.construir_pieza({"unsupported": "engranajes"}, tmp_path)

    assert info.value.causa is declinacion.Causa.FAMILIA_NO_SOPORTADA
