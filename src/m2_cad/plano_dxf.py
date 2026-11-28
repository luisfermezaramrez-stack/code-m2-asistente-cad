"""Plano DXF con vistas ortogonales de la pieza verificada (SPEC-043, HU-42).

Dado el resultado del pipeline (que ya cita su STEP en `outputs/`), arma una
hoja DXF con las vistas frontal, superior y lateral proyectadas por HLR, capas
de aristas visibles y ocultas, cotas generales y cotas por arista (AC1, AC2,
RF-1..RF-3). El resultado es determinista: el mismo programa produce el mismo
DXF byte a byte (RNF-1).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ezdxf
from cadquery import importers
from cadquery.occ_impl.shapes import Compound
from OCP.BRepLib import BRepLib
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape

if TYPE_CHECKING:
    from cadquery.occ_impl.shapes import Edge

    from m2_cad.pipeline import ResultadoPieza

#: Marca del rótulo, coherente con la regla de dominio de las salidas preliminares.
MARCA_PRELIMINAR_PLANO = "DISEÑO PRELIMINAR — no usar para fabricación"

# Cabecera con fecha fija: sin ella ezdxf sella la hora de creación y el mismo
# programa produciría DXF distintos (RNF-1). Fecha juliana arbitraria y estable.
FECHA_FIJA = 2460000.5

#: Dirección de cámara y eje X del proyector de cada vista (SPEC-043 RF-1).
_VISTAS = {
    "frontal": ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0, 2)),
    "superior": ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0, 1)),
    "lateral": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1, 2)),
}

CAPAS = {
    "ARISTAS-VISIBLES": {"color": 7},
    "ARISTAS-OCULTAS": {"color": 8, "linetype": "DASHED"},
    "COTAS": {"color": 3},
    "ROTULO": {"color": 4},
}

_LADO_VISTA = 15.0  # hueco entre recuadros de vista
_PATA_COTA = 5.0  # distancia de la cota general al borde de la vista
_TOLERANCIA_DISCRETIZACION = 0.5  # mm entre puntos de una curva proyectada
_LONGITUD_MINIMA_COTA = 1.0  # mm, las tiras más cortas no llevan cota


def cotas_generales_de_vista(
    caja_mm: tuple[float, float, float], vista: str
) -> tuple[float, float]:
    """Dimensiones (ancho, alto) de la caja proyectada en el plano de la vista (AC2)."""
    ancho, alto = _VISTAS[vista][2]
    return (caja_mm[ancho], caja_mm[alto])


def proyeccion_hlr(shape: object, vista: str) -> tuple[list[Edge], list[Edge]]:
    """Aristas visibles y ocultas de `shape` proyectadas según la vista (RF-1, RF-2).

    Usa el mismo mecanismo HLR del exportador SVG de CadQuery; después de
    `HLRToShape` las aristas viven en el plano del proyector y sus puntos son
    2D (compárese `cadquery/occ_impl/exporters/svg.py`).
    """
    camara, ejex, _ = _VISTAS[vista]
    hlr = HLRBRep_Algo()
    hlr.Add(shape.wrapped)  # type: ignore[attr-defined]
    hlr.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(), gp_Dir(*camara), gp_Dir(*ejex))))
    hlr.Update()
    hlr.Hide()
    aristas_hlr = HLRBRep_HLRToShape(hlr)
    visibles = _recoger(
        aristas_hlr.VCompound, aristas_hlr.Rg1LineVCompound, aristas_hlr.OutLineVCompound
    )
    ocultas = _recoger(
        aristas_hlr.HCompound, aristas_hlr.Rg1LineHCompound, aristas_hlr.OutLineHCompound
    )
    return visibles, ocultas


def _recoger(*componentes) -> list[Edge]:
    """Junta las aristas de los compuestos del HLR (pudiendo quedar nulos)."""
    aristas: list[Edge] = []
    compuestos = []
    for componente in componentes:
        compuesto = componente()
        if compuesto.IsNull():
            continue
        compuestos.append(compuesto)
        aristas.extend(Compound(compuesto).Edges())
    # CadQuery exige reconstruir la geometría de fondo o el acceso luego falla.
    for compuesto in compuestos:
        BRepLib.BuildCurves3d_s(compuesto, 1e-6)
    return aristas


def polilinea_de(arista: Edge) -> list[tuple[float, float]]:
    """Discretiza una arista proyectada a puntos 2D del plano de la vista.

    Tras `HLRToShape` las coordenadas del plano son (x, y) para cualquier
    dirección de cámara (compárese `cadquery.occ_impl.exporters.svg`).
    """
    try:
        n = (
            2
            if arista.geomType() == "LINE"
            else max(8, int(arista.Length() / _TOLERANCIA_DISCRETIZACION))
        )
    except Exception:  # pragma: no cover - curva degenerada del HLR
        return []
    return [(arista.positionAt(i / (n - 1)).x, arista.positionAt(i / (n - 1)).y) for i in range(n)]


def _cotas_generales(msp, caja_vista: tuple[float, float], offset: tuple[float, float]) -> None:
    """Cotas generales de la vista, coherentes con la verificación (AC2, RF-3)."""
    ancho, alto = caja_vista
    ox, oy = offset
    atribs = {"dimstyle": "M2", "layer": "COTAS"}
    msp.add_linear_dim(
        p1=(ox, oy), p2=(ox + ancho, oy), base=(ox, oy - _PATA_COTA), dxfattribs=atribs
    ).render()
    msp.add_linear_dim(
        p1=(ox, oy),
        p2=(ox, oy + alto),
        base=(ox - _PATA_COTA, oy),
        angle=90,
        dxfattribs=atribs,
    ).render()


def extremos_de(arista: Edge) -> tuple[tuple[float, float], tuple[float, float]]:
    primero = arista.positionAt(0.0)
    ultimo = arista.positionAt(1.0)
    return (
        (primero.x, primero.y),
        (ultimo.x, ultimo.y),
    )


def _cotas_por_arista(msp, aristas: list[Edge], offset: tuple[float, float]) -> None:
    """Cota una vez cada arista recta visible del plano (RF-3, alcance honesto).

    Deduplica por extremos redondeados; la disposición evita choques con un
    desplazamiento escalonado, pero no se promete un layout libre de traslapes
    (SPEC-043 la completa la acotación de fabricación de SPEC-049).
    """
    atribs = {"dimstyle": "M2", "layer": "COTAS"}
    vistas: dict[tuple, tuple[tuple[float, float], tuple[float, float]]] = {}
    for arista in aristas:
        if arista.geomType() != "LINE":
            continue
        (x1, y1), (x2, y2) = extremos_de(arista)
        p1 = (x1 + offset[0], y1 + offset[1])
        p2 = (x2 + offset[0], y2 + offset[1])
        if ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 < _LONGITUD_MINIMA_COTA:
            continue
        clave = tuple(
            sorted([(round(p1[0], 2), round(p1[1], 2)), (round(p2[0], 2), round(p2[1], 2))])
        )
        vistas.setdefault(clave, (p1, p2))
    for indice, (p1, p2) in enumerate(vistas.values()):
        distancia = 1.5 + (indice % 4) * 2.0
        try:
            msp.add_aligned_dim(p1=p1, p2=p2, distance=distancia, dxfattribs=atribs).render()
        except Exception:  # pragma: no cover - cota degenerada
            continue


def _recuadro(
    msp, caja_vista: tuple[float, float], offset: tuple[float, float], titulo: str
) -> None:
    """Marco y rótulo de la vista, con la marca preliminar (RF-1)."""
    ancho, alto = caja_vista
    ox, oy = offset
    margen = _PATA_COTA + 3.0
    msp.add_lwpolyline(
        [
            (ox - margen, oy - margen),
            (ox + ancho + margen, oy - margen),
            (ox + ancho + margen, oy + alto + margen),
            (ox - margen, oy + alto + margen),
        ],
        close=True,
        dxfattribs={"layer": "ROTULO"},
    )
    msp.add_text(
        f"VISTA {titulo.upper()} — {MARCA_PRELIMINAR_PLANO}",
        dxfattribs={"layer": "ROTULO", "height": 3.0},
    ).set_placement((ox - margen, oy + alto + margen + 1.5))


def escribir(resultado: "ResultadoPieza", destino: Path) -> None:
    """Escribe el plano DXF de la pieza verificada en `destino` (AC1, RF-1..RF-3)."""
    # RNF-1: el DXF del mismo programa es byte a byte igual; ezdxf trae un
    # modo oficial de metadatos fijos para pruebas deterministas. Se activa
    # antes de `ezdxf.new` (la marca de creación se sella ahí, no al guardar).
    previo = ezdxf.options.write_fixed_meta_data_for_testing
    ezdxf.options.write_fixed_meta_data_for_testing = True
    try:
        _escribir(resultado, destino)
    finally:
        ezdxf.options.write_fixed_meta_data_for_testing = previo


def _escribir(resultado: "ResultadoPieza", destino: Path) -> None:
    shape = importers.importStep(str(resultado.step)).val()
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$TDCREATE"] = FECHA_FIJA
    doc.header["$TDUPDATE"] = FECHA_FIJA
    doc.header["$TDINDWG"] = 0.0
    for capa, atributos in CAPAS.items():
        doc.layers.add(capa, **atributos)
    doc.dimstyles.new("M2", dxfattribs={"dimtxt": 3, "dimasz": 2, "dimexo": 1, "dimdec": 2})

    msp = doc.modelspace()
    # Frontal abajo-izquierda, lateral a la derecha de la frontal y superior arriba
    # (disposición de plano tradicional, SPEC-043 RF-1).
    posicion = {
        "frontal": (0.0, 0.0),
        "lateral": (resultado.caja_mm[0] + _LADO_VISTA, 0.0),
        "superior": (0.0, resultado.caja_mm[2] + _LADO_VISTA),
    }
    for vista in ("frontal", "superior", "lateral"):
        visibles, ocultas = proyeccion_hlr(shape, vista)
        polilineas = {
            "ARISTAS-VISIBLES": [polilinea_de(a) for a in visibles],
            "ARISTAS-OCULTAS": [polilinea_de(a) for a in ocultas],
        }
        puntos = [punto for lista in polilineas.values() for pl in lista for punto in pl]
        if puntos:
            offset = (
                posicion[vista][0] - min(x for x, _ in puntos),
                posicion[vista][1] - min(y for _, y in puntos),
            )
        else:  # la vista no arrojó aristas; igual se dibuja su recuadro
            offset = posicion[vista]
        for capa, lista in polilineas.items():
            for pl in lista:
                msp.add_lwpolyline(
                    [(x + offset[0], y + offset[1]) for x, y in pl],
                    dxfattribs={"layer": capa},
                )
        _cotas_generales(msp, cotas_generales_de_vista(resultado.caja_mm, vista), offset)
        _cotas_por_arista(msp, visibles, offset)
        _recuadro(msp, cotas_generales_de_vista(resultado.caja_mm, vista), offset, vista)

    doc.saveas(Path(destino))
