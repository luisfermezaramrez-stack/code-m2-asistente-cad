"""Genera o comprueba el contrato OpenAPI v1 congelado (SPEC-032, HU-31).

Requiere las dependencias Python; no inicia servicios, usa red ni claves.
"""

import argparse
import sys
from pathlib import Path

from m2_cad.api import app
from m2_cad.contrato_api import RUTA_CONTRATO, serializar_contrato


def synchronize(contenido: str, destino: Path, *, check: bool) -> int:
    """Escribe el contrato o verifica que coincida sin modificarlo."""
    if check:
        if not destino.is_file() or destino.read_text(encoding="utf-8") != contenido:
            print(
                "Contrato OpenAPI v1 desactualizado. Ejecuta: make api-contract",
                file=sys.stderr,
            )
            return 1
        print("Contrato OpenAPI v1 actualizado.")
        return 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"Contrato OpenAPI v1 escrito en {destino}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada para `make api-contract` y `make api-contract-check`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Comprueba sin escribir.")
    argumentos = parser.parse_args(argv)
    return synchronize(serializar_contrato(app.openapi()), RUTA_CONTRATO, check=argumentos.check)


if __name__ == "__main__":
    raise SystemExit(main())
