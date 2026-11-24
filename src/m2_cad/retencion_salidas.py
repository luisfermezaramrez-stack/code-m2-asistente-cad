"""Retención conservadora de artefactos generados (SPEC-031 AC4).

Solo elimina subdirectorios de nombre UUID hexadecimal bajo outputs/, cuando
TODOS sus elementos son anteriores al límite; ignora enlaces simbólicos.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

_UUID_HEX = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class PoliticaRetencion:
    dias: float
    intervalo_segundos: int


def leer_politica() -> PoliticaRetencion | None:
    """Sin configuración no hay borrado automático (opt-in seguro)."""
    valor = os.getenv("M2_OUTPUT_RETENTION_DAYS", "").strip()
    if not valor:
        return None
    try:
        dias = float(valor)
        intervalo = int(os.getenv("M2_OUTPUT_SWEEP_SECONDS", "3600"))
    except ValueError as exc:
        raise ValueError("Configuración de retención inválida.") from exc
    if not math.isfinite(dias) or not 0 < dias <= 3650:
        raise ValueError("M2_OUTPUT_RETENTION_DAYS debe estar entre 0 y 3650.")
    if not 1 <= intervalo <= 86400:
        raise ValueError("M2_OUTPUT_SWEEP_SECONDS debe estar entre 1 y 86400.")
    return PoliticaRetencion(dias, intervalo)


def _ultima_modificacion(directorio: Path) -> float | None:
    """Devuelve mtime más reciente, o None si hay enlaces o errores de lectura."""
    try:
        if directorio.is_symlink():
            return None
        reciente = directorio.stat().st_mtime
        for ruta, carpetas, archivos in os.walk(directorio, followlinks=False):
            for nombre in carpetas + archivos:
                entrada = Path(ruta) / nombre
                if entrada.is_symlink():
                    return None
                reciente = max(reciente, entrada.stat().st_mtime)
        return reciente
    except OSError:
        return None


def depurar_outputs(
    directorio: Path,
    *,
    dias: float,
    ahora: float | None = None,
) -> list[Path]:
    """Elimina solo carpetas UUID completamente vencidas; nunca sigue symlinks.

    La integración en FastAPI evita ejecutar esto mientras haya trabajos activos.
    """
    if not math.isfinite(dias) or dias <= 0:
        raise ValueError("La retención debe ser positiva.")
    raiz = Path(directorio)
    if raiz.is_symlink() or not raiz.exists():
        return []
    if not raiz.is_dir():
        raise ValueError("outputs debe ser un directorio.")

    limite = (time.time() if ahora is None else ahora) - dias * 86400
    eliminados: list[Path] = []
    for candidato in raiz.iterdir():
        if not _UUID_HEX.fullmatch(candidato.name):
            continue
        if candidato.is_symlink() or not candidato.is_dir():
            continue
        ultima = _ultima_modificacion(candidato)
        if ultima is None or ultima >= limite:
            continue
        # Segunda lectura para evitar borrar una carpeta recién modificada.
        actual = _ultima_modificacion(candidato)
        if actual is None or actual >= limite:
            continue
        try:
            shutil.rmtree(candidato)
        except FileNotFoundError:
            continue  # Otro trabajador ya la eliminó.
        eliminados.append(candidato)
    return eliminados
