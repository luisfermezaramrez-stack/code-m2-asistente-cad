"""Plano PDF con vistas, cotas y cajetín (SPEC-044, HU-43).

Reutiliza las vistas HLR y los valores de cotas de SPEC-043
(`m2_cad.plano_dxf`): no reimplementa la proyección ni el cálculo de cotas.
Separa el cálculo puro en `paquete()` (posiciones en mm, escala y textos del
cajetín) del dibujo en `escribir()` sobre el backend PDF de matplotlib,
dependencia ya presente por `vtk` y promovida a directa (RNF-4).

Determinismo (RNF-1): el bloque de metadatos PDF se fija (`CreationDate`
nulo y `Producer` propio); la única huella variable admisible es la fecha
del cajetín, que las pruebas y el pipeline inyectan.
"""

from __future__ import annotations

from datetime import date
from math import dist, isclose
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from cadquery import importers

from m2_cad.plano_dxf import (
    MARCA_PRELIMINAR_PLANO,
    cotas_generales_de_vista,
    polilinea_de,
    proyeccion_hlr,
)

matplotlib.use("Agg")  # sin pantalla (RNF-2)

#: Verse de página (alto, ancho) en mm de cada formato admitido, en horizontal.
TAMANOS_MM = {"a4": (210.0, 297.0), "a3": (297.0, 420.0)}
MARGEN_MM = 10.0
_ANCHO_CAJETIN = 85.0
_ALTO_CAJETIN = 32.0
_PATA_COTA = 5.0  # distancia de la línea de cota al borde de la vista
_HOLGURA_TEXTO = 4.0  # sitio del rótulo de la cota bajo la línea
_GAPO_VISTAS = 15.0  # hueco entre recuadros de vista
_SERIE_ESCALAS = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)


def paquete(
    resultado: object,
    formato: str = "a4",
    *,
    fecha: date | None = None,
    solicitud_id: str = "—",
) -> dict:
    """Cálculo puro del plano: vistas, cotas, escala y cajetín (RF-1..RF-3).

    Devuelve `escala` (numerador, denominador), `vistas` (título, offset en
    página, polilíneas en coordenadas de vista y cotas ya en página) y
    `cajetin` (posición, tamaño, líneas, rótulo y escala). `escribir` dibuja
    exactamente este dict; las pruebas lo verifican sin abrir matplotlib.
    """
    if formato not in TAMANOS_MM:
        raise ValueError(f"formato {formato!r} no admitido; use a4 o a3 (RF-4)")
    alto_pagina, ancho_pagina = TAMANOS_MM[formato]
    caja = tuple(resultado.caja_mm)  # type: ignore[index]
    reserva = _PATA_COTA + _HOLGURA_TEXTO
    alto_util = alto_pagina - MARGEN_MM - (MARGEN_MM + _ALTO_CAJETIN + reserva)
    ancho_util = ancho_pagina - 2 * MARGEN_MM - 2 * reserva

    den = _denominador_necesario(caja, ancho_util, alto_util)
    factor = 1.0 / den
    vistas = _vistas_acotadas(resultado, caja, factor, ancho_pagina, alto_pagina)
    cajetin = _cajetin(resultado, den, ancho_pagina, fecha or date.today(), solicitud_id)
    return {"formato": formato, "escala": (1, den), "vistas": vistas, "cajetin": cajetin}


def _denominador_necesario(
    caja: tuple[float, float, float], ancho_util: float, alto_util: float
) -> int:
    """Denominador de la serie 1:1, 1:2, 1:5... en el que el bloque de vistas cabe (RF-3)."""
    for den in _SERIE_ESCALAS:
        factor = 1.0 / den
        dims = {vista: cotas_generales_de_vista(caja, vista) for vista in _VISTAS_ORDEN}
        ancho_bloque = factor * (
            max(dims["frontal"][0], dims["superior"][0]) + _GAPO_VISTAS + dims["lateral"][0]
        )
        alto_bloque = factor * (dims["frontal"][1] + _GAPO_VISTAS + dims["superior"][1])
        if ancho_bloque <= ancho_util and alto_bloque <= alto_util:
            return den
    raise ValueError("la pieza no cabe en la hoja ni con escala 1:1000")


_VISTAS_ORDEN = ("frontal", "superior", "lateral")


def _vistas_acotadas(
    resultado: object,
    caja: tuple[float, float, float],
    factor: float,
    ancho_pagina: float,
    alto_pagina: float,
) -> list[dict]:
    """Tres vistas en página: frontal abajo-izquierda, superior encima, lateral a la derecha.

    Las cotas generales salen de `cotas_generales_de_vista` (SPEC-043); la
    línea de cota corre a `_PATA_COTA` del recuadro y guarda la holgura del
    texto, dentro del margen de página (AC1).
    """
    shape = importers.importStep(str(resultado.step)).val()  # type: ignore[attr-defined]
    x0 = MARGEN_MM + _PATA_COTA + _HOLGURA_TEXTO
    y0 = MARGEN_MM + _ALTO_CAJETIN + _PATA_COTA + _HOLGURA_TEXTO  # cajetín abajo-derecha
    posicion = {
        "frontal": (x0, y0),
        "lateral": (x0 + factor * caja[0] + _GAPO_VISTAS, y0),
        "superior": (x0, y0 + factor * caja[2] + _GAPO_VISTAS),
    }
    vistas = []
    for titulo in _VISTAS_ORDEN:
        visibles, ocultas = proyeccion_hlr(shape, titulo)
        ancho_v, alto_v = cotas_generales_de_vista(caja, titulo)
        px, py = posicion[titulo]
        polilineas_v = [polilinea_de(a) for a in visibles]
        polilineas_o = [polilinea_de(a) for a in ocultas]
        puntos = [punto for lista in (polilineas_v, polilineas_o) for pl in lista for punto in pl]
        if puntos:
            offset = (px - min(p[0] for p in puntos), py - min(p[1] for p in puntos))
        else:  # la vista no arrojó aristas; igual se dibuja su recuadro y cota
            offset = (px, py)
        cotas = _cotas_generales_en_pagina(caja, titulo, offset, factor, ancho_v, alto_v)
        vistas.append(
            {
                "titulo": titulo,
                "offset": offset,
                "polilineas_visibles": polilineas_v,
                "polilineas_ocultas": polilineas_o,
                "ancho": factor * ancho_v,
                "alto": factor * alto_v,
                "cotas": cotas,
            }
        )
    return vistas


def _cotas_generales_en_pagina(
    caja: tuple[float, float, float],
    titulo: str,
    offset: tuple[float, float],
    factor: float,
    ancho_v: float,
    alto_v: float,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Par de puntos de página de cada línea de cota general de la vista (AC3).

    Frontal y superior llevan la cota horizontal del ancho bajo la vista;
    lateral lleva la cota vertical del ancho proyectado a la izquierda.
    """
    ox, oy = offset
    if titulo == "lateral":
        return [
            ((ox - _PATA_COTA, oy), (ox - _PATA_COTA, oy + factor * alto_v)),
        ]
    return [((ox, oy - _PATA_COTA), (ox + factor * ancho_v, oy - _PATA_COTA))]


def _cajetin(
    resultado: object,
    denominador: int,
    ancho_pagina: float,
    fecha: date,
    solicitud_id: str,
) -> dict:
    """Datos del cajetín: material, masa, fecha, solicitud, escala y rótulo (AC2, RF-2 y RF-3)."""
    partes = getattr(resultado, "partes", None) or []
    materiales = (
        " · ".join(dict.fromkeys(str(parte.get("material", "—")) for parte in partes)) or "—"
    )
    masa_g = sum(float(parte.get("mass_g", 0.0)) for parte in partes)
    return {
        "x": ancho_pagina - MARGEN_MM - _ANCHO_CAJETIN,
        "y": MARGEN_MM,
        "ancho": _ANCHO_CAJETIN,
        "alto": _ALTO_CAJETIN,
        "rotulo": MARCA_PRELIMINAR_PLANO,
        "escala": (1, denominador),
        "lineas": [
            f"MATERIAL: {materiales}",
            f"MASA: {masa_g:.2f} g",
            f"FECHA: {fecha:%Y-%m-%d}",
            f"SOLICITUD: {solicitud_id}",
            f"ESCALA 1:{denominador}",
        ],
    }


def escribir(
    resultado: object,
    destino: str | Path,
    formato: str = "a4",
    *,
    fecha: date | None = None,
    solicitud_id: str = "—",
) -> None:
    """Escribe el plano PDF de la pieza verificada en `destino` (AC1, AC2, AC3)."""
    paq = paquete(resultado, formato, fecha=fecha, solicitud_id=solicitud_id)
    alto_pagina, ancho_pagina = TAMANOS_MM[paq["formato"]]

    figura = plt.figure(figsize=(ancho_pagina / 25.4, alto_pagina / 25.4))
    ejes = figura.add_axes([0.0, 0.0, 1.0, 1.0])
    ejes.set_xlim(0, ancho_pagina)
    ejes.set_ylim(0, alto_pagina)
    ejes.set_aspect("equal")
    ejes.axis("off")

    for vista in paq["vistas"]:
        ox, oy = vista["offset"]
        ejes.add_patch(
            plt.Rectangle(
                (ox, oy),
                vista["ancho"],
                vista["alto"],
                fill=False,
                edgecolor="0.7",
                linewidth=0.25,
            )
        )
        for pl in vista["polilineas_visibles"]:
            ejes.plot([ox + x for x, _ in pl], [oy + y for _, y in pl], "k-", lw=0.35)
        for pl in vista["polilineas_ocultas"]:
            ejes.plot(
                [ox + x for x, _ in pl], [oy + y for _, y in pl], color="0.45", ls="--", lw=0.25
            )
        for (x1, y1), (x2, y2) in vista["cotas"]:
            ejes.plot([x1, x2], [y1, y2], "k-", lw=0.25)
            _marcas_cota(ejes, x1, y1, x2, y2)
            _texto_cota(ejes, (x1, y1), (x2, y2), den=paq["escala"][1], titulo=vista["titulo"])

    _dibujar_cajetin(ejes, paq["cajetin"])

    figura.savefig(
        Path(destino),
        format="pdf",
        metadata={  # RNF-1: metadatos fijos; la fecha variable vive solo en el cajetín
            "Creator": "m2-cad",
            "Producer": "m2-cad",
            "Title": "Plano de diseño preliminar",
            "CreationDate": None,
        },
    )
    plt.close(figura)


def _marcas_cota(ejes, x1: float, y1: float, x2: float, y2: float) -> None:
    """Trazos de 2 mm en cada extremo de la línea de cota."""
    if isclose(y1, y2):  # horizontal
        ejes.plot([x1, x1], [y1 - 1, y1 + 1], "k-", lw=0.25)
        ejes.plot([x2, x2], [y1 - 1, y1 + 1], "k-", lw=0.25)
    else:  # vertical
        ejes.plot([x1 - 1, x1 + 1], [y1, y1], "k-", lw=0.25)
        ejes.plot([x1 - 1, x1 + 1], [y2, y2], "k-", lw=0.25)


def _texto_cota(ejes, extremo1, extremo2, den, titulo) -> None:
    """Rotula la cota con la medida real (longitud dibujada / escala), no la dibujada (AC3)."""
    x1, y1 = extremo1
    x2, y2 = extremo2
    valor = dist(extremo1, extremo2) * den
    x_medio, y_medio = (x1 + x2) / 2, (y1 + y2) / 2
    es_vertical = not isclose(y1, y2)
    ejes.text(
        x_medio + (-1.5 if es_vertical else 0.0),
        y_medio + (0.0 if es_vertical else -1.5),
        f"{valor:g}",
        fontsize=6,
        ha="center",
        va="center",
    )


def _dibujar_cajetin(ejes, cajetin: dict) -> None:
    """Cajetín abajo-derecha: rótulo de diseño preliminar y ficha técnica (AC2)."""
    ejes.add_patch(
        plt.Rectangle(
            (cajetin["x"], cajetin["y"]),
            cajetin["ancho"],
            cajetin["alto"],
            fill=False,
            edgecolor="black",
            linewidth=0.5,
        )
    )
    alto_linea = 4.5
    ejes.text(
        cajetin["x"] + 3,
        cajetin["y"] + cajetin["alto"] - 4,
        cajetin["rotulo"],
        fontsize=5.5,
        va="top",
        color="black",
    )
    for i, linea in enumerate(cajetin["lineas"]):
        ejes.text(
            cajetin["x"] + 3,
            cajetin["y"] + cajetin["alto"] - 10 - i * alto_linea,
            linea,
            fontsize=5.5,
            va="top",
        )
