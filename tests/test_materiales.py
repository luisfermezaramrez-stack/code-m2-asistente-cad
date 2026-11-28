"""SPEC-049 (HU-48) RF-3: tabla versionada de precios de materiales.

La tabla es la fuente única de precios y de la lista canónica de materiales; estas
pruebas fijan que no se despegue del kit ni del prompt. Sin red ni servicios.
"""

import tomllib
from pathlib import Path

import pytest
from constraint_kit.parts import DENSITY_G_MM3

from m2_cad import materiales

CANONICOS = ("steel", "stainless", "aluminum", "brass", "copper", "abs", "pla", "nylon")


def _escribir_tabla(directorio: Path, texto: str) -> Path:
    ruta = directorio / "materiales.toml"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _tabla_valida(**cambios: object) -> str:
    """Tabla mínima válida, con la posibilidad de alterar una entrada."""
    lineas = ["version = 1", 'moneda = "USD"', 'unidad_precio = "kg"', ""]
    for nombre in CANONICOS:
        precio = cambios.get(nombre, 2.0)
        lineas.extend(
            [
                "[[materiales]]",
                f'nombre = "{nombre}"',
                f"densidad_g_mm3 = {DENSITY_G_MM3[nombre]}",
                f"precio_usd_kg = {precio}",
                'fuente = "prueba"',
                'actualizado = "2026-11-27"',
                "",
            ]
        )
    return "\n".join(lineas)


def test_la_tabla_versionada_no_tiene_problemas():
    assert materiales.verificar() == []


def test_los_materiales_soportados_son_los_ocho_del_prompt():
    assert materiales.SOPORTADOS == CANONICOS


def test_la_tabla_declara_su_version_y_su_unidad_de_precio():
    datos = tomllib.loads(Path(materiales.RUTA_TABLA).read_text(encoding="utf-8"))

    assert datos["version"] == 1
    assert datos["moneda"] == "USD"
    assert datos["unidad_precio"] == "kg"


@pytest.mark.parametrize("material", CANONICOS)
def test_cada_material_usa_la_densidad_del_kit_y_tiene_precio_positivo(material):
    entrada = materiales.cargar()[material]

    assert entrada["densidad_g_mm3"] == DENSITY_G_MM3[material]
    assert entrada["precio_usd_kg"] > 0


def test_el_precio_por_gramo_sale_de_la_tabla():
    entrada = materiales.cargar()["aluminum"]

    assert materiales.precio_usd_g("aluminum") == pytest.approx(entrada["precio_usd_kg"] / 1000)


@pytest.mark.parametrize("pedido", ["al", "AL", " al "])
def test_el_alias_al_se_normaliza_a_aluminum(pedido):
    assert materiales.normalizar(pedido) == "aluminum"


@pytest.mark.parametrize("pedido", [" Aluminum ", "STEEL", "nylon"])
def test_un_material_canonico_se_normaliza_sin_cambiar_de_nombre(pedido):
    assert materiales.normalizar(pedido) == pedido.strip().lower()


@pytest.mark.parametrize("ajeno", ["titanium", "iron", "petg", "acero", "", None, 7])
def test_lo_que_no_es_canonico_no_se_normaliza(ajeno):
    assert materiales.normalizar(ajeno) is None


def test_un_precio_desconocido_es_un_error_de_configuracion():
    with pytest.raises(materiales.ErrorMateriales) as info:
        materiales.precio_usd_g("titanium")

    assert "titanium" in str(info.value)


def test_la_ruta_de_la_tabla_se_configura_por_entorno(tmp_path, monkeypatch):
    ruta = _escribir_tabla(tmp_path, _tabla_valida(aluminum=9.5))
    monkeypatch.setenv("M2_MATERIALES", str(ruta))

    assert materiales.precio_usd_g("aluminum") == pytest.approx(9.5 / 1000)
    assert materiales.verificar() == []


def test_verificar_detecta_un_material_faltante(tmp_path, monkeypatch):
    # El encabezado más los siete primeros bloques dejan la tabla sin `nylon`.
    recortado = "[[materiales]]".join(_tabla_valida().split("[[materiales]]")[:8])
    monkeypatch.setenv("M2_MATERIALES", str(_escribir_tabla(tmp_path, recortado)))

    problemas = materiales.verificar()

    assert any("nylon" in problema for problema in problemas)


def test_verificar_detecta_una_densidad_que_no_coincide_con_el_kit(tmp_path, monkeypatch):
    texto = _tabla_valida().replace(
        f"densidad_g_mm3 = {DENSITY_G_MM3['steel']}", "densidad_g_mm3 = 0.1", 1
    )
    monkeypatch.setenv("M2_MATERIALES", str(_escribir_tabla(tmp_path, texto)))

    problemas = materiales.verificar()

    assert any("steel" in problema and "densidad" in problema for problema in problemas)


def test_verificar_detecta_un_precio_no_positivo(tmp_path, monkeypatch):
    texto = _tabla_valida(brass=0.0)
    monkeypatch.setenv("M2_MATERIALES", str(_escribir_tabla(tmp_path, texto)))

    problemas = materiales.verificar()

    assert any("brass" in problema and "precio" in problema for problema in problemas)


def test_verificar_detecta_un_alias_que_choca_con_un_material_canonico(tmp_path, monkeypatch):
    texto = _tabla_valida().replace('nombre = "steel"', 'nombre = "steel"\nalias = ["brass"]', 1)
    monkeypatch.setenv("M2_MATERIALES", str(_escribir_tabla(tmp_path, texto)))

    problemas = materiales.verificar()

    assert any("brass" in problema and "alias" in problema for problema in problemas)
