#!/usr/bin/env python3
"""Verifica el corpus dorado del núcleo determinista (HU-23, SPEC-024).

Recorre `data/corpus_dorado.json` construyendo cada programa DSL y comparando el
resultado con lo congelado: `acepta` con la huella del STEP, o `declina`. No usa
GPU, red ni API key: parte de programas, no de texto, y nunca invoca al modelo.

    python scripts/verify_corpus_dorado.py            # verifica (lo que corre CI)
    python scripts/verify_corpus_dorado.py --write    # regenera tras un cambio intencional
"""

import argparse
import sys
import tempfile
from pathlib import Path

from m2_cad import corpus_dorado


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Corpus dorado del núcleo determinista (HU-23).")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=corpus_dorado.DEFAULT_PATH,
        help="ruta del corpus congelado (por defecto data/corpus_dorado.json)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenera el corpus con lo que el núcleo produce hoy (queda visible en el diff)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    try:
        casos = corpus_dorado.cargar_corpus(argumentos.corpus, estricto=not argumentos.write)
    except corpus_dorado.ErrorCorpus as error:
        print(f"corpus inválido: {error}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="corpus-dorado-") as temporal:
        directorio = Path(temporal)
        if argumentos.write:
            regenerados = corpus_dorado.regenerar(casos, directorio)
            corpus_dorado.escribir_corpus(regenerados, argumentos.corpus)
            print(f"corpus regenerado: {len(regenerados)} casos en {argumentos.corpus}")
            return 0
        try:
            divergencias = corpus_dorado.comparar(casos, directorio)
        except corpus_dorado.ErrorCorpus as error:
            print(f"corpus inválido: {error}", file=sys.stderr)
            return 2

    if divergencias:
        print(f"corpus dorado: {len(divergencias)} divergencia(s)", file=sys.stderr)
        for divergencia in divergencias:
            print(f"  - {corpus_dorado.describir(divergencia)}", file=sys.stderr)
        return 1
    print(f"corpus dorado: {len(casos)} casos sin divergencias")
    return 0


if __name__ == "__main__":
    sys.exit(main())
