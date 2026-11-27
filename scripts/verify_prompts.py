#!/usr/bin/env python3
"""Verifica que ningún prompt cambió sin subir su versión (HU-33, SPEC-034, AC2).

Recorre `prompts/manifest.toml` y exige que el `sha256` declarado coincida con el
contenido de cada archivo, que no haya versiones duplicadas y que cada id declare
exactamente una versión vigente. No usa red, GPU ni el entorno del proyecto:
`prompts.py` solo necesita la biblioteca estándar.

    python scripts/verify_prompts.py                    # verifica el árbol real
    python scripts/verify_prompts.py --raiz /tmp/copia   # verifica otra copia
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# El objetivo del Makefile corre con `uv run --no-project`: se agrega `src` al
# camino de importación para que `m2_cad.prompts` se resuelva sin instalar nada.
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from m2_cad import prompts  # noqa: E402  (import posterior al ajuste de sys.path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verifica los prompts versionados (HU-33).")
    parser.add_argument(
        "--raiz",
        type=Path,
        default=None,
        help="carpeta de prompts a verificar (por defecto prompts/ del repositorio)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    errores = prompts.verificar(raiz=argumentos.raiz)
    if errores:
        print(f"prompts: {len(errores)} error(es) de integridad", file=sys.stderr)
        for error in errores:
            print(f"  - {error}", file=sys.stderr)
        return 1
    raiz = Path(argumentos.raiz) if argumentos.raiz is not None else prompts.RUTA_PROMPTS
    entradas = prompts.cargar_manifiesto(raiz=raiz).get("prompts") or []
    print(f"prompts: {len(entradas)} versión(es) verificadas en {raiz}/, todas con su hash.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
