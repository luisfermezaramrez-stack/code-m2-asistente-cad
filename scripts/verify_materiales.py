#!/usr/bin/env python3
"""Verifica la tabla versionada de materiales y precios (HU-48, SPEC-049, RF-3).

Exige que `data/materiales.toml` declare la versión, la moneda y la unidad del precio,
que estén los ocho materiales canónicos y ninguno de más, que cada uno tenga densidad y
precio positivos y que los alias no choquen entre sí. No usa red, GPU ni el entorno del
proyecto: `materiales.py` solo necesita la biblioteca estándar.

    python scripts/verify_materiales.py                       # verifica el árbol real
    python scripts/verify_materiales.py --tabla /tmp/otra.toml  # verifica otra tabla
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# El objetivo del Makefile corre con `uv run --no-project`: se agrega `src` al
# camino de importación para que `m2_cad.materiales` se resuelva sin instalar nada.
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from m2_cad import materiales  # noqa: E402  (import posterior al ajuste de sys.path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica la tabla de materiales (HU-48).")
    parser.add_argument(
        "--tabla",
        type=Path,
        default=None,
        help="archivo a verificar (por defecto data/materiales.toml del repositorio)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    problemas = materiales.verificar(destino=argumentos.tabla)
    if problemas:
        print(f"materiales: {len(problemas)} problema(s) en la tabla", file=sys.stderr)
        for problema in problemas:
            print(f"  - {problema}", file=sys.stderr)
        return 1
    tabla = materiales.cargar(argumentos.tabla)
    print(
        f"materiales: {len(materiales.SOPORTADOS)} materiales verificados en "
        f"{materiales.ruta_tabla() if argumentos.tabla is None else argumentos.tabla}, "
        f"{len(tabla)} con precio."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
