"""Registro de solicitudes (HU-06).

Persiste texto original, traducción, resultado, latencia, error y versión del
modelo, excluyendo nombres y correos, para calcular las métricas de los
objetivos 1 y 2 sin revisar casos a mano.

Especificación: specs/004-registro-solicitudes/spec.md
- AC3: en 20 llamadas, 0 campos vacíos.
- AC4: excluye nombres y correos (Ley 1581 de 2012).
"""

import csv
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

CAMPOS = [
    "id",
    "hora",
    "texto",
    "traduccion",
    "resultado",
    "latencia_ms",
    "error",
    "version",
]

RUTA_DEFAULT = Path("data/registro.csv")

# Ley 1581 de 2012: el registro no puede contener correos ni nombres
# declarados por el usuario. Se reemplazan por marcadores explícitos para
# mantener la regla AC3 (ningún campo vacío) y la trazabilidad del texto.
PATRON_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PATRON_NOMBRE = re.compile(
    r"\b(?:me llamo|mi nombre es|soy)\s+"
    r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,2}",
    re.IGNORECASE,
)


# HU-14: la solicitud llega en español al modelo; no hay traducción que registrar.
SIN_TRADUCCION = "no aplica"


def _sanitizar(texto: str) -> str:
    """Excluye correos y nombres declarados del texto dado (AC4)."""
    texto = PATRON_CORREO.sub("[correo eliminado]", texto)
    return PATRON_NOMBRE.sub("[nombre eliminado]", texto)


def _a_valor_conocido(valor: object, reemplazo: str) -> str:
    """Convierte cualquier valor en una cadena no vacía (AC3)."""
    texto = str(valor) if valor is not None else reemplazo
    return texto if texto.strip() else reemplazo


def registrar(
    texto: str,
    traduccion: str,
    resultado: object,
    latencia_ms: float,
    error: str | None = None,
    version: str | None = None,
    ruta: Path = RUTA_DEFAULT,
) -> dict[str, str]:
    """Registra una solicitud con los 8 campos de la especificación.

    Devuelve la fila escrita. Los campos sin valor conocido quedan con un
    marcador explícito ('ninguno', 'desconocida', '0'), nunca vacíos (AC3).
    """
    fila = {
        "id": uuid.uuid4().hex,
        "hora": datetime.now(UTC).isoformat(),
        "texto": _sanitizar(_a_valor_conocido(texto, "sin texto")),
        "traduccion": _sanitizar(_a_valor_conocido(traduccion, "sin traduccion")),
        "resultado": _sanitizar(_a_valor_conocido(resultado, "sin resultado")),
        "latencia_ms": _a_valor_conocido(latencia_ms, "0"),
        "error": _a_valor_conocido(error, "ninguno"),
        "version": _a_valor_conocido(version, "desconocida"),
    }

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    archivo_nuevo = not ruta.exists()

    with open(ruta, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
        if archivo_nuevo:
            escritor.writeheader()
        escritor.writerow(fila)

    return fila
