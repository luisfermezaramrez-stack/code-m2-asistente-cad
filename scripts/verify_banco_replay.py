#!/usr/bin/env python3
"""Verifica el banco HU-02 en modo replay con respuestas grabadas (HU-44, SPEC-045).

Sin banderas corre lo que ejecuta CI: valida el artefacto y las 40 respuestas, corre
el pipeline real con el proveedor grabado y falla si no se alcanza el umbral. No usa
red, API key, GPU ni tokens.

    python scripts/verify_banco_replay.py                       # verificación de CI
    python scripts/verify_banco_replay.py --solo-verificar      # sólo esquema y cobertura
    python scripts/verify_banco_replay.py --grabar              # regraba con el proveedor real
"""

import argparse
import os
import sys
from pathlib import Path

from m2_cad import banco, banco_replay, dataset


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Banco HU-02 en modo replay (HU-44).")
    parser.add_argument(
        "--respuestas",
        type=Path,
        default=banco_replay.DEFAULT_PATH,
        help="artefacto de respuestas grabadas",
    )
    parser.add_argument("--banco", type=Path, default=dataset.DEFAULT_PATH)
    parser.add_argument("--salida", type=Path, default=Path("outputs/banco-replay"))
    parser.add_argument(
        "--umbral",
        type=float,
        default=1.0,
        help="aceptación mínima; el proceso falla si no se alcanza",
    )
    parser.add_argument(
        "--solo-verificar",
        action="store_true",
        help="valida esquema, prompt, modelo y cobertura sin ejecutar el banco",
    )
    parser.add_argument(
        "--grabar",
        action="store_true",
        help="graba respuestas del proveedor real (gasta tokens; requiere API key)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    filas = dataset.read_dataset(args.banco)
    try:
        if args.grabar:
            datos = banco_replay.grabar(filas, ruta=args.respuestas)
            print(f"grabadas {len(datos['respuestas'])} respuestas en {args.respuestas}")
            return 0
        preparado = banco_replay.preparar(filas, args.respuestas)
        if args.solo_verificar:
            print(
                f"replay válido: {len(preparado['respuestas'])} respuestas, "
                f"prompt {preparado['prompt']['etiqueta']}, origen {preparado['origen']}"
            )
            return 0
    except banco_replay.ErrorReplay as error:
        print(f"replay inválido: {error}", file=sys.stderr)
        return 2

    # AC1/RNF-1: la corrida de CI es observabilidad del pipeline, no un experimento
    # de MLflow; el baseline real se registra en el workflow programado.
    os.environ["MLFLOW_TRACKING_ENABLED"] = "0"
    return banco.main(
        [
            "--banco",
            str(args.banco),
            "--salida",
            str(args.salida),
            "--respuestas",
            str(args.respuestas),
            "--umbral",
            str(args.umbral),
            "--replay",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
