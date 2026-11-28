#!/usr/bin/env python3
"""Verifica el catálogo versionado de plantillas (HU-49, SPEC-050, RF-1, RNF-3).

Exige versión, ids únicos, tipos del motor, familias del banco, un programa con una
sola pieza, material soportado y parámetros con etiqueta, unidad y rango coherente
(el valor por defecto dentro de `[minimo, maximo]`). No usa red, GPU ni el entorno
del proyecto: `plantillas.py` solo necesita la biblioteca estándar para esta puerta.

    python scripts/verify_plantillas.py                    # verifica el árbol real
    python scripts/verify_plantillas.py --catalogo /tmp/x.toml
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# El objetivo del Makefile corre con `uv run --no-project`: se agrega `src` al
# camino de importación para que `m2_cad.plantillas` se resuelva sin instalar nada.
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from m2_cad import plantillas  # noqa: E402  (import posterior al ajuste de sys.path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica el catálogo de plantillas (HU-49).")
    parser.add_argument(
        "--catalogo",
        type=Path,
        default=None,
        help="catálogo a verificar (por defecto data/plantillas.toml del repositorio)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    problemas = plantillas.verificar(destino=argumentos.catalogo)
    if problemas:
        print(f"plantillas: {len(problemas)} problema(s) en el catálogo", file=sys.stderr)
        for problema in problemas:
            print(f"  - {problema}", file=sys.stderr)
        return 1
    catalogo = plantillas.cargar_catalogo(argumentos.catalogo)
    ruta = argumentos.catalogo or plantillas.ruta_catalogo()
    print(f"plantillas: {len(catalogo)} plantillas verificadas en {ruta}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
