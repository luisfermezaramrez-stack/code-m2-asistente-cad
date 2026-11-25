"""Contrato OpenAPI congelado de la API v1 (SPEC-032, HU-31).

El documento versionado es una fotografía del esquema público: cualquier cambio
de ruta o de campo sin una subida de versión se detecta en CI.
"""

import json
from pathlib import Path

RUTA_CONTRATO = Path(__file__).resolve().parents[2] / "contracts" / "openapi-v1.json"


def cargar_contrato(ruta: Path | None = None) -> dict:
    """Lee el contrato congelado desde disco sin modificarlo."""
    destino = ruta or RUTA_CONTRATO
    return json.loads(destino.read_text(encoding="utf-8"))


def serializar_contrato(esquema: dict) -> str:
    """Serializa el esquema de forma determinista (UTF-8, claves ordenadas, LF)."""
    return json.dumps(esquema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _primera_diferencia(actual: object, esperado: object, ruta: str = "$") -> str | None:
    """Localiza la primera divergencia para dar un mensaje de error accionable."""
    if type(actual) is not type(esperado):
        return ruta
    if isinstance(actual, dict) and isinstance(esperado, dict):
        for clave in sorted(set(actual) | set(esperado)):
            if clave not in actual or clave not in esperado:
                return f"{ruta}.{clave}"
            diferencia = _primera_diferencia(actual[clave], esperado[clave], f"{ruta}.{clave}")
            if diferencia:
                return diferencia
        return None
    if isinstance(actual, list) and isinstance(esperado, list):
        if len(actual) != len(esperado):
            return f"{ruta}[longitud]"
        for indice, (valor, referencia) in enumerate(zip(actual, esperado, strict=True)):
            diferencia = _primera_diferencia(valor, referencia, f"{ruta}[{indice}]")
            if diferencia:
                return diferencia
        return None
    if actual != esperado:
        return ruta
    return None


def validar_contrato(generado: dict, congelado: dict) -> None:
    """Falla si el esquema generado diverge del contrato congelado (AC2)."""
    if generado == congelado:
        return
    diferencia = _primera_diferencia(generado, congelado)
    raise AssertionError(
        f"Contrato OpenAPI v1 desactualizado en {diferencia}. "
        "Sube la versión de la API y regenera contracts/openapi-v1.json con make api-contract."
    )
