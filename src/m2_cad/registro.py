"""Registro de solicitudes (HU-06).

Persiste texto original, traducción, resultado, latencia, error y versión del
modelo, excluyendo nombres y correos, para calcular las métricas de los
objetivos 1 y 2 sin revisar casos a mano.

Especificación: specs/004-registro-solicitudes/spec.md
- AC3: en 20 llamadas, 0 campos vacíos.
- AC4: excluye nombres y correos (Ley 1581 de 2012).

HU-33 (specs/034-hu-33-prompts-versionados/spec.md, AC1): cada fila guarda el id y
la versión del prompt usado (`prompt`) y el hash de su contenido (`prompt_hash`).
"""

import csv
import io
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from m2_cad import declinacion
from m2_cad.autenticacion import ANONIMO
from m2_cad.declinacion import NINGUNA
from m2_cad.persistencia_registro import _bloqueo, _publicar_bytes, anexar_sin_duplicar

CAMPOS = [
    "id",
    "hora",
    "texto",
    "traduccion",
    "resultado",
    "latencia_ms",
    "error",
    "version",
    "usuario",
    "causa",
    "prompt",
    "prompt_hash",
]

# Valor de cada columna añadida después de la primera versión del registro.
# HU-53 añadió `usuario`; HU-26 añadió `causa` (etiqueta de la declinación); HU-33
# añade `prompt` (id y versión, p. ej. `planner-v1`) y `prompt_hash` (sha256 del texto).
_DEFECTOS_NUEVAS = {
    "usuario": ANONIMO,
    "causa": NINGUNA,
    "prompt": "no aplica",
    "prompt_hash": "no aplica",
}

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
# HU-33: si la solicitud no llegó al modelo no hay prompt usado, pero el campo nunca
# queda vacío (SPEC-004, AC3).
SIN_PROMPT = "no aplica"
_RUTAS_MIGRADAS: set[Path] = set()


def _asegurar_columnas(ruta: Path) -> None:
    """Añade al CSV las columnas nuevas al final, sin borrar ni alterar sus filas.

    HU-53 añadió `usuario`, HU-26 `causa` y HU-33 `prompt` y `prompt_hash`; un archivo
    de cualquiera de las versiones anteriores (8, 9 o 10 columnas) se migra en una sola
    pasada, en lugar de fallar contra la cabecera. Sólo se añaden columnas cuyo valor por
    defecto está definido: cualquier otra cabecera es un registro ajeno o corrupto y
    sigue fallando.
    """
    if not ruta.exists():
        return
    with _bloqueo(ruta):
        with ruta.open(encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            actuales = lector.fieldnames or []
            if actuales == CAMPOS:
                return
            if not actuales:
                # HU-36: un registro vacío (0 bytes) se reconstruye con su cabecera.
                filas: list[dict[str, str]] = []
                nuevas: list[str] = []
            else:
                if actuales != CAMPOS[: len(actuales)]:
                    raise ValueError("La cabecera del registro no coincide con CAMPOS.")
                nuevas = CAMPOS[len(actuales) :]
                if any(clave not in _DEFECTOS_NUEVAS for clave in nuevas):
                    raise ValueError("La cabecera del registro no coincide con CAMPOS.")
                filas = [
                    {**fila, **{clave: _DEFECTOS_NUEVAS[clave] for clave in nuevas}}
                    for fila in lector
                ]
        salida = io.StringIO(newline="")
        escritor = csv.DictWriter(salida, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(filas)
        _publicar_bytes(ruta, salida.getvalue().encode("utf-8"))


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
    *,
    identificador: str | None = None,
    usuario: str = ANONIMO,
    causa: str | None = None,
    prompt: str | None = None,
    prompt_hash: str | None = None,
) -> dict[str, str]:
    """Registra una solicitud con los campos de la especificación.

    Devuelve la fila escrita. Los campos sin valor conocido quedan con un
    marcador explícito ('ninguno', 'desconocida', '0'), nunca vacíos (AC3).
    """
    fila = {
        "id": identificador or uuid.uuid4().hex,
        "hora": datetime.now(UTC).isoformat(),
        "texto": _sanitizar(_a_valor_conocido(texto, "sin texto")),
        "traduccion": _sanitizar(_a_valor_conocido(traduccion, "sin traduccion")),
        "resultado": _sanitizar(_a_valor_conocido(resultado, "sin resultado")),
        "latencia_ms": _a_valor_conocido(latencia_ms, "0"),
        "error": _a_valor_conocido(error, "ninguno"),
        "version": _a_valor_conocido(version, "desconocida"),
        "usuario": _a_valor_conocido(usuario, ANONIMO),
        "causa": declinacion.normalizar(causa),
        "prompt": _a_valor_conocido(prompt, SIN_PROMPT),
        "prompt_hash": _a_valor_conocido(prompt_hash, SIN_PROMPT),
    }

    destino = Path(ruta).resolve()
    if destino not in _RUTAS_MIGRADAS:
        # Una vez por archivo y proceso: evita leer la cabecera en cada escritura.
        _asegurar_columnas(destino)
        _RUTAS_MIGRADAS.add(destino)
    return anexar_sin_duplicar(Path(ruta), fila, CAMPOS)
