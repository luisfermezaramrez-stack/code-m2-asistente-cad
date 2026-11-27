"""Almacén de versiones de una pieza y diff estructurado de programas (HU-35).

Especificación: specs/036-hu-35-edicion-iterativa/spec.md
- RF-2 (S2): el resultado de una edición incluye el diff entre el programa DSL
  previo y el nuevo, como estructura comprobable y no como texto.
- RF-4 (S4): una edición verificada produce una nueva versión de la pieza y
  conserva la anterior; nunca se sobrescribe una versión existente.
- RF-5 (S5): cada solicitud mantiene un historial de versiones consultable.
- RNF-3 (S9): cada versión registra el prompt usado y su hash (SPEC-034).

Un índice por solicitud en `data/versiones/<solicitud_id>.json` (o bajo
`M2_VERSIONES_DIR`), escrito entero y de forma atómica con el bloqueo por ruta de
`persistencia_registro`, el mismo mecanismo del registro CSV (HU-30): el archivo
nunca queda a medias y dos procesos no se pisan.

Solo biblioteca estándar: el módulo se importa sin el kernel CAD, sin red y sin GPU.
El contrato público está congelado en `specs/036-hu-35-edicion-iterativa/plan.md`.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from m2_cad.persistencia_registro import _bloqueo, _publicar_bytes

#: Directorio por defecto del índice de versiones; la variable lo sobreescribe.
RUTA_VERSIONES = Path("data/versiones")
VARIABLE_ENTORNO = "M2_VERSIONES_DIR"

#: Id de solicitud aceptado: uuid en forma canónica, con guiones o sin ellos.
_PATRON_SOLICITUD = re.compile(
    r"\A(?:[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\Z"
)
_GUIONES = "-"


class ErrorVersiones(ValueError):
    """El id de solicitud o el índice de versiones no son utilizables."""


def ruta_versiones() -> Path:
    """Directorio efectivo del índice: `M2_VERSIONES_DIR` si está definido."""
    valor = os.environ.get(VARIABLE_ENTORNO)
    return Path(valor) if valor else RUTA_VERSIONES


def validar_solicitud_id(solicitud_id: str) -> str:
    """Devuelve el fragmento canónico de nombre de archivo del id de solicitud.

    Acepta solo un uuid hexadecimal en minúscula (32 caracteres, con o sin
    guiones) y rechaza cualquier otra cosa —barras, `..`, espacios o vacío— para
    que el índice no pueda salir nunca de su directorio (S10).
    """
    texto = solicitud_id if isinstance(solicitud_id, str) else ""
    if not _PATRON_SOLICITUD.match(texto):
        raise ErrorVersiones(
            f"«{texto}» no es un id de solicitud válido: se espera un uuid hexadecimal."
        )
    return texto.replace(_GUIONES, "")


def diff_programas(previo: dict, nuevo: dict) -> list[dict]:
    """Diff estructurado entre dos programas DSL (S2/RF-2).

    Recorre diccionarios por clave ordenada y listas por índice, y produce
    entradas `{"ruta", "antes", "despues"}`: `antes` falta cuando la clave se
    agrega y `despues` cuando se quita. Un valor que no es escalar viaja entero.
    El resultado es determinista para el mismo par de programas. La ruta raíz
    (`""`) solo aparece si ambos programas son escalares.
    """
    cambios: list[dict] = []
    _diferenciar("", previo, nuevo, cambios)
    return cambios


def _es_escalar(valor: object) -> bool:
    return not isinstance(valor, (dict, list))


def _hija(ruta: str, clave: object) -> str:
    """Ruta de una clave de diccionario (`parts[0].params`) o del índice 0 de una lista."""
    if isinstance(clave, int):
        return f"{ruta}[{clave}]"
    return f"{ruta}.{clave}" if ruta else str(clave)


def _diferenciar(ruta: str, previo: object, nuevo: object, cambios: list[dict]) -> None:
    """Acumula en `cambios` las diferencias entre `previo` y `nuevo`."""
    if isinstance(previo, dict) and isinstance(nuevo, dict):
        for clave in sorted(set(previo) | set(nuevo), key=str):
            destino = _hija(ruta, clave)
            if clave not in previo:
                cambios.append({"ruta": destino, "despues": nuevo[clave]})
            elif clave not in nuevo:
                cambios.append({"ruta": destino, "antes": previo[clave]})
            else:
                _diferenciar(destino, previo[clave], nuevo[clave], cambios)
        return
    if isinstance(previo, list) and isinstance(nuevo, list):
        for indice in range(max(len(previo), len(nuevo))):
            destino = _hija(ruta, indice)
            if indice >= len(previo):
                cambios.append({"ruta": destino, "despues": nuevo[indice]})
            elif indice >= len(nuevo):
                cambios.append({"ruta": destino, "antes": previo[indice]})
            else:
                _diferenciar(destino, previo[indice], nuevo[indice], cambios)
        return
    if _es_escalar(previo) and _es_escalar(nuevo) and previo == nuevo:
        return
    if not _es_escalar(previo) or not _es_escalar(nuevo):
        # Un cambio de forma (lista por diccionario, escalar por lista) viaja entero.
        if previo != nuevo:
            cambios.append({"ruta": ruta, "antes": previo, "despues": nuevo})
        return
    cambios.append({"ruta": ruta, "antes": previo, "despues": nuevo})


def _indice(solicitud_id: str, directorio: Path | None) -> Path:
    """Ruta del índice JSON de una solicitud, con el directorio ya validado."""
    fragmento = validar_solicitud_id(solicitud_id)
    base = Path(directorio) if directorio is not None else ruta_versiones()
    return base / f"{fragmento}.json"


def _leer(destino: Path) -> list[dict]:
    """Lee el índice del disco; `[]` si no existe y `ErrorVersiones` si está roto."""
    if not destino.exists():
        return []
    try:
        versiones = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ErrorVersiones(f"El índice de versiones {destino} no se pudo leer: {exc}.") from exc
    if not isinstance(versiones, list) or any(not isinstance(v, dict) for v in versiones):
        raise ErrorVersiones(f"El índice de versiones {destino} no es una lista de versiones.")
    return versiones


def leer_versiones(solicitud_id: str, *, directorio: Path | None = None) -> list[dict]:
    """Historial de la solicitud en orden ascendente de `version` (S5)."""
    versiones = _leer(_indice(solicitud_id, directorio))
    return sorted(versiones, key=lambda version: version["version"])


def ultima_version(solicitud_id: str, *, directorio: Path | None = None) -> dict | None:
    """Versión de número más alto, o `None` si la solicitud no tiene historial."""
    versiones = leer_versiones(solicitud_id, directorio=directorio)
    return versiones[-1] if versiones else None


def nueva_version(versiones: list[dict]) -> int:
    """Próximo número de versión: `max + 1`, o 1 si el historial está vacío."""
    return max((version["version"] for version in versiones), default=0) + 1


def registrar_version(
    solicitud_id: str,
    *,
    usuario: str,
    programa: dict,
    artefactos: list[str],
    prompt: str,
    prompt_hash: str,
    diff: list[dict] | None = None,
    causa: str | None = None,
    version: int | None = None,
    directorio: Path | None = None,
) -> dict:
    """Agrega una versión al historial y publica el índice completo (S4, S5, S9).

    La escritura es atómica y va bajo el bloqueo por ruta del índice, así que el
    archivo nunca queda a medias y dos escritores no se pisan. Nunca sobrescribe:
    si la versión pedida ya existe, lanza `ErrorVersiones`.
    """
    destino = _indice(solicitud_id, directorio)
    with _bloqueo(destino):
        versiones = _leer(destino)
        numero = version if version is not None else nueva_version(versiones)
        if any(existente.get("version") == numero for existente in versiones):
            raise ErrorVersiones(
                f"La solicitud {validar_solicitud_id(solicitud_id)} ya tiene la versión {numero}."
            )
        entrada = {
            "version": numero,
            "hora": datetime.now(UTC).isoformat(),
            "programa": programa,
            "artefactos": [str(artefacto) for artefacto in artefactos],
            "diff": diff if diff is not None else [],
            "prompt": prompt,
            "prompt_hash": prompt_hash,
            "usuario": usuario,
        }
        if causa is not None:
            entrada["causa"] = causa
        versiones.append(entrada)
        _publicar_bytes(
            destino, json.dumps(versiones, ensure_ascii=False, indent=2).encode("utf-8")
        )
    return entrada
