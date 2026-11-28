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


_SIN_MATERIAL = object()


def _programa(material: object = _SIN_MATERIAL, *, tipo: str = "plate") -> dict:
    params = (
        {"width": 100, "depth": 50, "thick": 5}
        if tipo == "plate"
        else {"outer_d": 20, "bore_d": 8, "height": 10}
    )
    parte: dict = {"id": "p", "type": tipo, "params": params}
    if material is not _SIN_MATERIAL:
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
    filas = _filas(pipeline.construir_pieza(_programa(), tmp_path).bom_csv)

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


def _csv_del_kit(programa: dict) -> str:
    """CSV que producía el kit para el mismo programa (referencia de RNF-3)."""
    from collections import Counter, defaultdict

    from constraint_kit import bom as bom_kit
    from constraint_kit import builder as kit_builder

    _, partes = kit_builder.build_assembly(programa)
    masa_por_tipo: dict[str, float] = defaultdict(float)
    for parte in partes:
        masa_por_tipo[parte["type"]] += parte.get("mass_g") or 0.0
    resumen = {
        "bom": dict(Counter(parte["type"] for parte in partes)),
        "mass_by_type": dict(masa_por_tipo),
        "mass_g": sum(masa_por_tipo.values()),
        "part_count": len(partes),
    }
    return bom_kit.bom_document(resumen, fmt="csv")


def test_rnf3_las_cuatro_columnas_historicas_coinciden_byte_a_byte_con_el_kit(tmp_path):
    """El prefijo histórico del CSV no cambia ni en formato ni en fin de línea."""
    programa = _programa("steel")

    esperado = _csv_del_kit(programa)
    obtenido = pipeline.construir_pieza(programa, tmp_path).bom_csv.read_bytes().decode("utf-8")

    assert "\r\n" in obtenido
    assert obtenido.replace("\r\n", "").count("\n") == 0, "quedan saltos LF sueltos"
    filas_esperadas = esperado.split("\r\n")
    filas_obtenidas = obtenido.split("\r\n")
    assert len(filas_obtenidas) == len(filas_esperadas)
    for esperada, obtenida in zip(filas_esperadas, filas_obtenidas, strict=True):
        if not esperada:
            assert obtenida == ""
            continue
        assert obtenida.split(",")[:4] == esperada.split(","), obtenida


def test_un_material_sin_precio_falla_antes_de_exportar(tmp_path, monkeypatch):
    """Configuración de precios incompleta: no se escribe STEP ni GLB."""
    tabla = materiales.RUTA_TABLA.read_text(encoding="utf-8").replace(
        "precio_usd_kg = 1.20", "precio_usd_kg = 0"
    )
    ruta = tmp_path / "materiales.toml"
    ruta.write_text(tabla, encoding="utf-8")
    monkeypatch.setenv("M2_MATERIALES", str(ruta))
    destino = tmp_path / "salida"

    with pytest.raises(pipeline.ErrorPipeline) as info:
        pipeline.construir_pieza(_programa("steel"), destino)

    assert "steel" in str(info.value)
    assert not (destino / "pieza.step").exists()
    assert not (destino / "pieza.glb").exists()
    assert not (destino / "pieza.csv").exists()


@pytest.mark.parametrize(
    ("material", "fragmento"),
    [
        ("", "la pieza «p» no indica un material válido"),
        ("   ", "la pieza «p» no indica un material válido"),
        (None, "la pieza «p» no indica un material válido"),
        (5, "la pieza «p» no indica un material válido"),
        (["steel"], "la pieza «p» no indica un material válido"),
        ("aluminium", "el material «aluminium» no está entre los materiales soportados"),
    ],
)
def test_ac3_el_motivo_es_legible_para_cualquier_valor(material, fragmento, tmp_path):
    with pytest.raises(pipeline.PiezaDeclinada) as info:
        pipeline.construir_pieza(_programa(material), tmp_path)

    mensaje = str(info.value)
    assert fragmento in mensaje
    assert "«»" not in mensaje
    assert "'steel'" not in mensaje
    if "material válido" in mensaje:
        assert "steel," in mensaje, "el motivo lista los materiales soportados"
    assert info.value.causa is declinacion.Causa.MATERIAL_NO_SOPORTADO


def test_el_costo_de_linea_sale_del_unitario_redondeado():
    """Factura: unitario redondeado, línea = unitario x cantidad y total = suma de líneas.

    Tres espaciadores de nailon con 2,95 g cada uno: el costo exacto por unidad es
    0,0826 USD y el de la línea 0,2478. Redondear cada uno por separado daba 0,08 y
    0,25, y la fila no cuadraba.
    """
    partes = [{"type": "spacer", "material": "nylon", "mass_g": 2.95} for _ in range(3)]

    filas = list(
        csv.reader(pipeline._csv_materiales(pipeline._resumen_materiales(partes)).splitlines())
    )

    unitario = float(filas[1][5])
    linea = float(filas[1][6])
    assert unitario == 0.08
    assert linea == round(unitario * 3, 2)
    assert linea == 0.24
    assert filas[3][0] == "TOTAL"
    assert float(filas[3][6]) == round(linea, 2)
