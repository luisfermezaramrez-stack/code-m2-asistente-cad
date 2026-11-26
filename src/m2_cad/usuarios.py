"""Utilidad HU-53 para generar hashes de clave sin versionar secretos.

Uso: ``python -m m2_cad.usuarios hash`` o ``make hash-clave``. La clave se lee
de ``M2_CLAVE_NUEVA`` cuando está definida; si no, se pide por prompt oculto.
"""

from __future__ import annotations

import argparse
import getpass
import os

from m2_cad.autenticacion import hash_clave, verificar_clave


def _clave() -> str:
    return os.environ.get("M2_CLAVE_NUEVA") or getpass.getpass("Clave: ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="accion", required=True)
    sub.add_parser("hash", help="Imprime un hash PBKDF2 para M2_AUTH_USERS.")
    verificar = sub.add_parser("verificar", help="Comprueba una clave contra un hash.")
    verificar.add_argument("hash")
    args = parser.parse_args()

    clave = _clave()
    if args.accion == "hash":
        print(hash_clave(clave))
        return 0
    valida = verificar_clave(clave, args.hash)
    print("válida" if valida else "inválida")
    return 0 if valida else 1


if __name__ == "__main__":
    raise SystemExit(main())
