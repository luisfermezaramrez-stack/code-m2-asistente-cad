#!/usr/bin/env python3
"""Valida la política de excepciones de seguridad (SPEC-029, HU-28, RF-4).

Comprueba los dos archivos de `security/` contra el esquema de
`security/politica-excepciones.md`: cada excepción necesita `justificacion`
(≥ 20 caracteres), `aprobado_por` y una `revision` ISO vigente (hoy o después y
como máximo 180 días vista), además de los campos de su herramienta. También
rechaza claves desconocidas y entradas que no sean tablas.

    python scripts/security_excepciones.py validar

Códigos de salida: 0 política válida, 1 errores acumulados.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "src") not in sys.path:
    sys.path.insert(0, str(RAIZ / "src"))

from m2_cad import seguridad_ci  # noqa: E402

ARCHIVOS = (
    ("secretos", seguridad_ci.RUTA_EXCEPCIONES_SECRETOS),
    ("dependencias", seguridad_ci.RUTA_EXCEPCIONES_DEPENDENCIAS),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida la política de excepciones de seguridad (SPEC-029, HU-28)."
    )
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    subcomandos.add_parser("validar", help="valida security/excepciones-*.toml")
    return parser


def validar(hoy: date | None = None) -> list[str]:
    """Errores acumulados de los dos archivos, en español (lista vacía = válidos)."""
    hoy = hoy or date.today()
    errores: list[str] = []
    for herramienta, ruta in ARCHIVOS:
        archivo = RAIZ / ruta
        if not archivo.is_file():
            errores.append(f"{ruta}: falta el archivo de excepciones")
            continue
        try:
            datos = seguridad_ci.leer_toml(archivo)
        except (tomllib.TOMLDecodeError, OSError) as error:
            errores.append(f"{ruta}: TOML inválido: {error}")
            continue
        errores.extend(
            f"{ruta}: {mensaje}"
            for mensaje in seguridad_ci.validar_excepciones(datos, herramienta, hoy)
        )
    return errores


def main(argv: list[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    if argumentos.comando != "validar":  # pragma: no cover - argparse lo impide
        return 2
    errores = validar()
    if errores:
        print("La política de excepciones no es válida:")
        for error in errores:
            print(f"- {error}")
        print(
            "RESULTADO: la política de excepciones falla; corrige los errores o retira "
            "la excepción de security/ (ver security/politica-excepciones.md)."
        )
        return 1
    print(
        "OK: la política de excepciones es válida (justificación, aprobador y fecha de "
        "revisión vigentes en security/excepciones-secretos.toml y "
        "security/excepciones-dependencias.toml)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
