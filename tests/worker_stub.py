"""Procesador simulado para probar el worker de HU-45 en otro proceso."""

import os
from pathlib import Path


def procesar(texto: str, control, medido: dict | None = None) -> dict[str, str]:
    """Emite las etapas reales y deja constancia del PID que ejecutó el trabajo."""
    control.informar("validando")
    control.informar("generando")
    if medido is not None:
        medido["tokens_entrada"] = 120
        medido["tokens_salida"] = 40
    Path(os.environ["M2_WORKER_MARKER"]).write_text(str(os.getpid()), encoding="utf-8")
    return {"resultado": "pieza.step", "texto": texto}
