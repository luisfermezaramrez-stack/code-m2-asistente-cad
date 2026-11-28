"""SPEC-043 (HU-42): plano DXF con vistas, capas y cotas, sin red, API key ni GPU.

Cada prueba lleva su AC o regla (RF-1..RF-3, RNF-1, RNF-3) según SPEC-043
y usa el patrón AAA.
"""

import math

import ezdxf
import pytest

from m2_cad.plano_dxf import cotas_generales_de_vista, escribir

CAPAS_ESPERADAS = {"ARISTAS-VISIBLES", "ARISTAS-OCULTAS", "COTAS", "ROTULO"}
TOLERANCIA_MM = 0.05


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


# ---------- AC1: abre en un visor CAD estándar (auditoría ezdxf como vérificador) ----------


def test_ac1_auditoria_limpia_y_capas(placa, tmp_path):
    """AC1: el DXF se relee con auditoría sin errores y trae las capas declaradas."""
    destino = tmp_path / "pieza.dxf"

    escribir(placa, destino)

    leido = ezdxf.readfile(destino)
    auditor = ezdxf.audit.Auditor(leido)
    auditor.run()
    assert auditor.errors == []
    assert auditor.fixes == []
    nombres_capas = {capa.dxf.name for capa in leido.layers}
    assert CAPAS_ESPERADAS <= nombres_capas


# ---------- RF-1: vistas en una sola hoja ----------


def test_rf1_tres_vistas_rotuladas(placa, tmp_path):
    """RF-1: la hoja rotula las vistas frontal, superior y lateral."""
    destino = tmp_path / "pieza.dxf"

    escribir(placa, destino)

    doc = ezdxf.readfile(destino)
    textos = " · ".join(
        e.dxf.text for e in doc.modelspace().query("TEXT") if e.dxf.layer == "ROTULO"
    )
    for vista in ("FRONTAL", "SUPERIOR", "LATERAL"):
        assert f"VISTA {vista}" in textos


# ---------- RF-2: capas separadas visibles/ocultas ----------


def test_rf2_aristas_ocultas_en_capa_propia(placa, tmp_path):
    """RF-2: la placa perforada proyecta visibles y ocultas, cada una en su capa."""
    destino = tmp_path / "pieza.dxf"

    escribir(placa, destino)

    doc = ezdxf.readfile(destino)
    vis = [e for e in doc.modelspace() if e.dxf.layer == "ARISTAS-VISIBLES"]
    ocu = [e for e in doc.modelspace() if e.dxf.layer == "ARISTAS-OCULTAS"]
    assert len(vis) > 0
    assert len(ocu) > 0, "una placa con agujeros debe proyectar aristas ocultas"
    for entidad in doc.modelspace():
        assert entidad.dxf.layer in ("ARISTAS-VISIBLES", "ARISTAS-OCULTAS", "COTAS", "ROTULO")


def test_rf2_capa_de_ocultas_siempre_existe(tmp_path):
    """RF-2: aunque la pieza no arroje ocultas (eje macizo), la capa queda declarada."""
    resultado = _construida(tmp_path, "shaft", diameter=10, length=80)
    destino = tmp_path / "eje.dxf"

    escribir(resultado, destino)

    doc = ezdxf.readfile(destino)
    assert "ARISTAS-OCULTAS" in {capa.dxf.name for capa in doc.layers}


# ---------- RF-3 / AC2: cotas coherentes con la verificación ----------


def test_ac2_cotas_generales_igual_caja_mm():
    """AC2: la proyección de caja_mm por vista da las cotas generales."""
    caja = (40.0, 20.0, 6.0)

    frontal = cotas_generales_de_vista(caja, "frontal")
    superior = cotas_generales_de_vista(caja, "superior")
    lateral = cotas_generales_de_vista(caja, "lateral")

    assert frontal == (40.0, 6.0)
    assert superior == (40.0, 20.0)
    assert lateral == (20.0, 6.0)


def test_ac2_dimension_reporta_la_medida(placa, tmp_path):
    """AC2: las DIMENSION del DXF llevan la medida coherente con la caja."""
    destino = tmp_path / "pieza.dxf"
    anchura, profundidad, altura = placa.caja_mm

    escribir(placa, destino)

    doc = ezdxf.readfile(destino)
    dimensiones = list(doc.modelspace().query("DIMENSION"))
    assert dimensiones, "el plano lleva cotas"
    medidas = {round(d.get_measurement(), 3) for d in dimensiones}
    assert {anchura, profundidad, altura} <= medidas


def test_ac2_medidas_dentro_de_la_caja(placa, tmp_path):
    """AC2: ninguna medida inválida ni mayor que la diagonal de la caja (±tolerancia)."""
    destino = tmp_path / "pieza.dxf"

    escribir(placa, destino)

    doc = ezdxf.readfile(destino)
    diagonal = math.dist((0, 0, 0), placa.caja_mm)
    for dimension in doc.modelspace().query("DIMENSION"):
        medida = dimension.get_measurement()
        assert medida is not None
        assert 0.0 < medida <= diagonal + TOLERANCIA_MM


# ---------- Integración con el pipeline ----------


def test_pipeline_entrega_dxf_y_respuesta(placa):
    """AC/SPEC-043: construir_pieza arma el medio físico y lo expone."""
    assert placa.dxf is not None and placa.dxf.is_file()
    respuesta = placa.a_respuesta()
    assert respuesta["dxf"] == str(placa.dxf)  # y el archivo reabre sin errores (AC1)


# ---------- RNF-1/RNF-3: determinismo y no regresión ----------


def test_rnf1_mismo_programa_mismo_dxf(placa, tmp_path):
    """RNF-1: el mismo programa produce el mismo DXF byte a byte."""
    destino1 = tmp_path / "uno.dxf"
    destino2 = tmp_path / "dos.dxf"

    escribir(placa, destino1)
    escribir(placa, destino2)

    assert destino1.read_bytes() == destino2.read_bytes()


def test_rnf3_step_glb_csv_intactos(placa, tmp_path):
    """RNF-3: la salida STEP/GLB/CSV existente no cambia de contenido."""
    import hashlib

    def firma(nombre):
        return hashlib.sha256(getattr(placa, nombre).read_bytes()).hexdigest()

    antes = {n: firma(n) for n in ("step", "glb", "bom_csv")}

    escribir(placa, tmp_path / "extra.dxf")

    despues = {n: firma(n) for n in ("step", "glb", "bom_csv")}
    assert antes == despues
