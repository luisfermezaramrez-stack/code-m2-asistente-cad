"""Genera o comprueba TypeScript desde app.openapi(); SPEC-028, AC1/AC2.

Requiere las dependencias Python y npm instaladas; no inicia servicios.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from m2_cad.api import app

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "frontend/src/generated/api.ts"


def generate_types(schema: dict) -> str:
    """Convierte el esquema en memoria usando el generador fijado por npm."""
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Falta Node. Instala Node 24 y ejecuta make frontend-install.")
    result = subprocess.run(
        [node, str(ROOT / "frontend/scripts/generate-api-types.mjs")],
        input=json.dumps(schema, ensure_ascii=False, sort_keys=True),
        capture_output=True,
        encoding="utf-8",
        check=False,
        cwd=ROOT,
    )
    if result.returncode:
        raise RuntimeError(
            "No se pudieron generar los tipos. Ejecuta make frontend-install.\n" + result.stderr
        )
    return result.stdout.replace("\r\n", "\n")


def synchronize(content: str, destination: Path, *, check: bool) -> int:
    """Comprueba sin escribir o actualiza el archivo con saltos LF en toda plataforma."""
    if check:
        if not destination.exists() or destination.read_text(encoding="utf-8") != content:
            print("Tipos OpenAPI desactualizados. Ejecuta: make api-types", file=sys.stderr)
            return 1
        print("Tipos OpenAPI actualizados.")
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8", newline="\n")
    print("Tipos OpenAPI generados.")
    return 0


def main() -> int:
    """Punto de entrada para make api-types y make api-types-check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compara sin modificar el archivo.")
    args = parser.parse_args()
    try:
        return synchronize(generate_types(app.openapi()), DESTINATION, check=args.check)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
