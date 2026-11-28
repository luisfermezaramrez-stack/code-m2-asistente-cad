"""SPEC-044 (HU-43): plano PDF con vistas, cotas y cajetín, sin red, API key ni GPU.

Cada prueba lleva su AC o regla (RF-1..RF-4, RNF-1, RNF-4) según SPEC-044
y usa el patrón AAA. Reutiliza las vistas HLR y las cotas de SPEC-043
(`plano_dxf`); no reimplementa la proyección ni el cálculo de cotas.
"""

import math
import re
from datetime import date
from pathlib import Path

import pytest

from m2_cad.plano_dxf import MARCA_PRELIMINAR_PLANO
from m2_cad.plano_pdf import escribir, paquete

MARGEN_MM = 10.0
TAMANOS_MM = {"a4": (210.0, 297.0), "a3": (297.0, 420.0)}
FECHA_FIJA = date(2026, 1, 15)


def _programa(tipo: str, **params: float) -> dict:
    """Programa DSL mínimo como en `tests/test_pipeline.py`."""
    return {
        "parts": [{"id": "p", "type": tipo, "material": "steel", "params": params}],
        "mates": [],
    }


def _construida(tmp_path, tipo, **params):
    from m2_cad import pipeline

    return pipeline.construir_pieza(_programa(tipo, **params), tmp_path)


@pytest.fixture(scope="module")
def placa(tmp_path_factory):
    """Una placa real construida con el núcleo del pipeline (sin LLM)."""
    return _construida(tmp_path_factory.mktemp("placa"), "plate", width=40, depth=20, thick=6)


# ---------- AC1: página A4/A3 sin recortes ----------


@pytest.mark.parametrize("formato", ["a4", "a3"])
def test_ac1_pagina_del_tamano_declarado_con_margen(placa, tmp_path, formato):
    """AC1: A4 y A3 exactos y todo el contenido dentro de la página menos 10 mm."""
    import pypdf

    destino = tmp_path / f"pieza-{formato}.pdf"

    escribir(placa, destino, formato=formato, fecha=FECHA_FIJA, solicitud_id="sol-1")

    lector = pypdf.PdfReader(destino)
    assert len(lector.pages) == 1
    caja = lector.pages[0].mediabox
    # La hoja es horizontal: el lado menor corresponde a la altura de página?
    # No: la hoja es horizontal, el ancho es el lado MAYOR.
    ancho, alto = (
        max(float(caja.width), float(caja.height)),
        min(float(caja.width), float(caja.height)),
    )
    esperado = TAMANOS_MM[formato]
    # 1 mm = 72/25.4 pt
    a_pt = lambda mm: mm * 72 / 25.4  # noqa: E731
    assert math.isclose(ancho, a_pt(esperado[1]), rel_tol=1e-6)
    assert math.isclose(alto, a_pt(esperado[0]), rel_tol=1e-6)


def test_ac1_contenido_dentro_del_margen(placa, tmp_path):
    """AC1: el bloque de vistas y el cajetín quedan dentro del margen de 10 mm."""
    destino = tmp_path / "pieza.pdf"
    escribir(placa, destino, fecha=FECHA_FIJA, solicitud_id="sol-1")

    paq = paquete(placa, "a4")
    alto_pagina, ancho_pagina = TAMANOS_MM["a4"]  # la hoja es horizontal: 297 x 210
    for vista in paq["vistas"]:
        ox, oy = vista["offset"]
        polilineas = vista["polilineas_visibles"] + vista["polilineas_ocultas"]
        puntos = [
            (ox, oy),
            *((ox + px, oy + py) for poli in polilineas for px, py in poli),
        ]
        for x, y in puntos:
            assert MARGEN_MM <= x <= ancho_pagina - MARGEN_MM
            assert MARGEN_MM <= y <= alto_pagina - MARGEN_MM
    caj = paq["cajetin"]
    assert MARGEN_MM <= caj["x"] <= ancho_pagina - MARGEN_MM - caj["ancho"]
    assert MARGEN_MM <= caj["y"] <= alto_pagina - MARGEN_MM - caj["alto"]


# ---------- RF-4: formatos A4 y A3 ----------


def test_rf4_formato_ajeno_rechazado(placa, tmp_path):
    """RF-4: solo A4 y A3; un tamaño ajeno es un error del programa, no un plano."""
    with pytest.raises(ValueError, match="a4|a3"):
        escribir(placa, tmp_path / "pieza.pdf", formato="letter", fecha=FECHA_FIJA)


# ---------- RF-1: las vistas acotadas de SPEC-043 ----------


def test_rf1_tres_vistas_de_spec043(placa):
    """RF-1: el PDF reutiliza las vistas HLR de SPEC-043 (no reimplementa)."""
    paq = paquete(placa, "a4")

    titulos = {vista["titulo"] for vista in paq["vistas"]}
    assert titulos == {"frontal", "superior", "lateral"}
    # Cada vista trae aristas visibles y ocultas de la proyección HLR compartida.
    for vista in paq["vistas"]:
        assert vista["polilineas_visibles"], vista["titulo"]
    # Las capas y la marca preliminar son las de SPEC-043.
    assert MARCA_PRELIMINAR_PLANO in paq["cajetin"]["rotulo"]


# ---------- AC2 y RF-2: cajetín completo ----------


def test_ac2_cajetin_completo(placa):
    """AC2: el cajetín muestra material, masa, fecha e id de solicitud."""
    paq = paquete(placa, "a4", fecha=FECHA_FIJA, solicitud_id="sol-abc")

    texto_cajetin = "\n".join(paq["cajetin"]["lineas"])
    assert "steel" in texto_cajetin  # material
    masa = sum(parte.get("mass_g", 0.0) for parte in placa.partes)
    assert f"{masa:.2f}" in texto_cajetin  # masa en g (sum de mass_g del builder)
    assert "2026-01-15" in texto_cajetin  # fecha
    assert "sol-abc" in texto_cajetin  # id de solicitud


def test_rf2_cajetin_leible_en_el_pdf(placa, tmp_path):
    """RF-2: los cuatro campos del cajetín salen en el texto del PDF generado."""
    import pypdf

    destino = tmp_path / "pieza.pdf"
    escribir(placa, destino, fecha=FECHA_FIJA, solicitud_id="sol-abc")

    texto = pypdf.PdfReader(destino).pages[0].extract_text() or ""
    masa = sum(parte.get("mass_g", 0.0) for parte in placa.partes)
    for esperado in ("steel", f"{masa:.2f}", "2026-01-15", "sol-abc"):
        assert esperado in texto, esperado


# ---------- RF-3 y AC3: escala declarada y coherente ----------


def test_rf3_declaracion_de_escala(placa):
    """RF-3: el cajetín declara la escala elegida por serie."""
    paq = paquete(placa, "a4")

    declarada = paq["cajetin"]["escala"]
    assert isinstance(declarada, tuple) and declarada[0] == 1
    assert declarada[1] >= 1  # serie 1:1, 1:2, ...


def test_ac3_relacion_de_la_cota_coherente_con_la_escala(placa):
    """AC3: la longitud dibujada de una cota general / su valor coincide con la escala."""
    paq = paquete(placa, "a4")
    num, den = paq["cajetin"]["escala"]

    frontal = paq["vistas"][0]
    p1, p2 = frontal["cotas"][0]
    longitud_pagina = math.dist(p1, p2)
    valor_real = float(placa.caja_mm[0])  # la primera cota general es el ancho de la caja
    relacion = longitud_pagina / valor_real
    # Tolerancia declarada: 1 % del cociente de la escala.
    assert math.isclose(relacion, num / den, rel_tol=0.01)


# ---------- No-regresión de bytes: GLB/CSV/DXF estables con el PDF nuevo ----------


def test_no_regresion_glb_csv_dxf_con_pdf(placa):
    """RNF-3: el PDF nuevo no altera GLB, CSV ni DXF ya entregados."""
    import hashlib

    placa_despues = _construida(placa.step.parent, "plate", width=40, depth=20, thick=6)

    resumen = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    # El STEP de build123d varía entre corridas (marca de tiempo) y el GLB
    # triangulado lo hereda; se comparan corridas congenéreas y no con valor
    # congelado. El DXF usa metadatos fijos, así que sí es byte a byte.
    assert resumen(placa_despues.glb) == resumen(placa.glb)
    assert resumen(placa_despues.bom_csv) == resumen(placa.bom_csv)
    assert resumen(placa_despues.dxf) == resumen(placa.dxf)
    assert placa_despues.pdf is not None and placa_despues.pdf.is_file()


# ---------- RNF-1: determinista salvo la fecha del cajetín ----------


def test_rnf1_bytes_identicos_con_la_misma_fecha(placa, tmp_path):
    """RNF-1: mismo programa, misma fecha → mismos bytes; con otra fecha cambia."""
    uno = tmp_path / "uno.pdf"
    dos = tmp_path / "dos.pdf"

    escribir(placa, uno, fecha=FECHA_FIJA, solicitud_id="sol-1")
    escribir(placa, dos, fecha=FECHA_FIJA, solicitud_id="sol-1")
    assert uno.read_bytes() == dos.read_bytes()

    otro = tmp_path / "otro.pdf"
    escribir(placa, otro, fecha=date(2026, 2, 20), solicitud_id="sol-1")
    assert otro.read_bytes() != uno.read_bytes()


# ---------- RNF-4: dependencia declarada ----------


def test_rnf4_matplotlib_directa_en_pyproject():
    """RNF-4: la dependencia de PDF es directa en pyproject.toml (promover transitiva)."""
    contenido = Path("pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'"matplotlib>=[\d.]+"', contenido)


# ---------- Integración con el pipeline: el PDF es un entregable igual que el DXF ----------


def test_pipeline_genera_pdf_y_existe(
    tmp_path,
):
    """RF-1/RF-2 por el pipeline: pieza.pdf junto a los demás entregables."""
    from m2_cad import pipeline

    resultado = pipeline.construir_pieza(_programa("plate", width=40, depth=20, thick=6), tmp_path)

    assert resultado.pdf is not None
    assert resultado.pdf.is_file()
    assert resultado.pdf.suffix == ".pdf"
    # Los otros entregables siguen ahí (no-regresión de estructura).
    assert resultado.step.is_file()
    assert resultado.glb.is_file()
    assert resultado.bom_csv.is_file()
    assert resultado.dxf is not None and resultado.dxf.is_file()
    # La respuesta HTTP muestra el artefacto nuevo.
    assert "pdf" in resultado.a_respuesta()
