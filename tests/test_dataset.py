"""Contrato HU-02 y rechazos de datos corruptos; sin importar motor CAD ni LLM."""

import copy
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from m2_cad.dataset import (
    COLUMNS,
    FAMILIES,
    PRODUCT_FAMILIES,
    analytical_reference,
    read_dataset,
    validate_dataset,
    validate_row,
)


@pytest.fixture
def rows():
    return read_dataset()


def test_banco_cumple_contrato(rows):
    validate_dataset(rows)


def test_reparto_y_catalogo(rows):
    positives = [r for r in rows if r["resultado_esperado"] != "declinar"]
    negatives = [r for r in rows if r["resultado_esperado"] == "declinar"]
    assert len(positives) == 30
    assert len(negatives) == 10
    assert Counter(r["familia"] for r in positives) == Counter({f: 5 for f in FAMILIES})
    assert {"extrusion", "pipe"} <= set(PRODUCT_FAMILIES)
    assert all(r["familia"] not in PRODUCT_FAMILIES for r in negatives)


@pytest.mark.parametrize("index", range(40))
def test_fila_completa_tipos_unidades_y_referencia(rows, index):
    validate_row(rows[index])


@pytest.mark.parametrize("column", COLUMNS)
@pytest.mark.parametrize("value", ["", "   ", None])
def test_rechaza_celdas_incompletas(rows, column, value):
    row = copy.deepcopy(rows[0])
    row[column] = value
    with pytest.raises(ValueError):
        validate_row(row)


@pytest.mark.parametrize("count", [0, 39, 41])
def test_rechaza_numero_de_filas(rows, count):
    malformed = (rows + [rows[0]])[:count]
    with pytest.raises(ValueError, match="40 filas"):
        validate_dataset(malformed)


def test_rechaza_ids_duplicados(rows):
    rows[1]["id"] = rows[0]["id"]
    with pytest.raises(ValueError, match="IDs duplicados"):
        validate_dataset(rows)


def test_rechaza_parametros_repetidos(rows):
    rows[1]["medidas"] = rows[0]["medidas"]
    rows[1]["resultado_esperado"] = rows[0]["resultado_esperado"]
    with pytest.raises(ValueError, match="Parámetros positivos duplicados"):
        validate_dataset(rows)


def test_rechaza_distribucion_por_familia_incorrecta(rows):
    replacement = copy.deepcopy(rows[5])
    replacement["id"] = rows[0]["id"]
    replacement["solicitud"] = "Otra escuadra con un ancho distinto, descrita en español."
    measures = json.loads(replacement["medidas"])
    measures["parametros"]["width"] += 1
    volume, box = analytical_reference("sheet_bracket", measures["parametros"])
    replacement["medidas"] = json.dumps(measures)
    replacement["resultado_esperado"] = json.dumps({"volumen_mm3": volume, "caja_xyz_mm": box})
    rows[0] = replacement
    with pytest.raises(ValueError, match="cinco por familia"):
        validate_dataset(rows)


def test_rechaza_reparto_positivo_negativo_incorrecto(rows):
    replacement = copy.deepcopy(rows[-1])
    replacement["id"] = "HU02-N11"
    replacement["solicitud"] = "Certifica una nueva estructura mediante cálculo estructural."
    rows[0] = replacement
    with pytest.raises(ValueError, match="30/10"):
        validate_dataset(rows)


@pytest.mark.parametrize("text", ["{}", "[]", "no es JSON", '{"unidad":"mm","unidad":"cm"}'])
def test_rechaza_json_incorrecto(rows, text):
    rows[0]["medidas"] = text
    with pytest.raises(ValueError):
        validate_row(rows[0])


@pytest.mark.parametrize("unit", ["cm", "in", 1, None])
def test_rechaza_unidades_incorrectas(rows, unit):
    measures = json.loads(rows[0]["medidas"])
    measures["unidad"] = unit
    rows[0]["medidas"] = json.dumps(measures)
    with pytest.raises(ValueError, match="mm"):
        validate_row(rows[0])


@pytest.mark.parametrize("value", [True, "40", -1, 0, float("inf"), float("nan")])
def test_rechaza_parametros_no_numericos_o_degenerados(rows, value):
    measures = json.loads(rows[0]["medidas"])
    measures["parametros"]["width"] = value
    rows[0]["medidas"] = json.dumps(measures)
    with pytest.raises(ValueError):
        validate_row(rows[0])


@pytest.mark.parametrize("value", [True, "6000", 0, -1, float("inf"), float("nan"), 1e100])
def test_rechaza_volumen_invalido(rows, value):
    result = json.loads(rows[0]["resultado_esperado"])
    result["volumen_mm3"] = value
    rows[0]["resultado_esperado"] = json.dumps(result)
    with pytest.raises(ValueError):
        validate_row(rows[0])


@pytest.mark.parametrize(
    "box", [[40, 30], [40, 30, 5, 1], [40, 30, True], [40, 0, 5], [40, "30", 5], [1, 1, 1]]
)
def test_rechaza_caja_invalida(rows, box):
    result = json.loads(rows[0]["resultado_esperado"])
    result["caja_xyz_mm"] = box
    rows[0]["resultado_esperado"] = json.dumps(result)
    with pytest.raises(ValueError):
        validate_row(rows[0])


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -1])
def test_rechaza_caja_no_finita(rows, value):
    result = json.loads(rows[0]["resultado_esperado"])
    result["caja_xyz_mm"][0] = value
    rows[0]["resultado_esperado"] = json.dumps(result)
    with pytest.raises(ValueError):
        validate_row(rows[0])


@pytest.mark.parametrize(
    "index,key,value", [(0, "bolt_count", True), (15, "flange_class", 150.0), (25, "simple", 1)]
)
def test_rechaza_confusion_entre_booleanos_y_numeros(rows, index, key, value):
    measures = json.loads(rows[index]["medidas"])
    measures["parametros"][key] = value
    rows[index]["medidas"] = json.dumps(measures)
    with pytest.raises(ValueError):
        validate_row(rows[index])


def test_detecta_referencia_analitica_incorrecta(rows):
    result = json.loads(rows[0]["resultado_esperado"])
    result["volumen_mm3"] /= 2
    rows[0]["resultado_esperado"] = json.dumps(result)
    with pytest.raises(ValueError, match="Volumen distinto"):
        validate_row(rows[0])


def test_negativo_no_inventa_dimensiones_y_exige_motivo(rows):
    row = next(r for r in rows if r["resultado_esperado"] == "declinar")
    measures = json.loads(row["medidas"])
    measures["parametros"] = {"width": 100}
    row["medidas"] = json.dumps(measures)
    with pytest.raises(ValueError, match="inventar dimensiones"):
        validate_row(row)
    del measures["parametros"]
    measures["motivo_esperado"] = ""
    row["medidas"] = json.dumps(measures)
    with pytest.raises(ValueError, match="motivo"):
        validate_row(row)


def test_no_declina_familias_del_producto(rows):
    row = next(r for r in rows if r["resultado_esperado"] == "declinar")
    for family in PRODUCT_FAMILIES:
        row["familia"] = family
        with pytest.raises(ValueError, match="dentro del alcance"):
            validate_row(row)


def test_rechaza_cabecera_incompatible(tmp_path):
    path = tmp_path / "incompatible.csv"
    path.write_text("id,familia,solicitud,medidas,resultado_esperado,extra\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Cabecera"):
        read_dataset(path)


def test_validacion_sin_site_packages_ni_motor():
    """-S excluye site-packages: la validación solo dispone de la biblioteca estándar."""
    src = Path(__file__).resolve().parents[1] / "src"
    code = (
        f"import sys; sys.path.insert(0, {str(src)!r}); "
        "from m2_cad.dataset import read_dataset, validate_dataset; "
        "validate_dataset(read_dataset()); "
        "assert not any(m in sys.modules for m in "
        "('cadquery', 'build123d', 'constraint_kit', 'llama_cpp'))"
    )
    result = subprocess.run([sys.executable, "-S", "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
