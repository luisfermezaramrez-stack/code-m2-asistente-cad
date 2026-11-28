"""Motivo público de los fallos conocidos del pipeline (SPEC-066, HU-65).

Un fallo conocido trae un motivo accionable; el resto sigue siendo genérico para no
exponer detalles internos. Lo usan el seguimiento SSE y el worker de la cola, de modo
que un mismo fallo se explica igual por los dos caminos.
"""

from __future__ import annotations

from m2_cad import materiales
from m2_cad.pipeline import ErrorGeneracion, ModeloNoDisponible

# ErrorMateriales arrastra la ruta absoluta del archivo en el contenedor: al usuario se
# le da la condición y la acción, no la ruta interna del despliegue.
MENSAJE_DATOS = "Faltan los datos del despliegue: no se encontró la tabla de materiales."


def motivo_publico(exc: BaseException) -> str | None:
    """Motivo publicable para un fallo conocido; ``None`` si debe seguir siendo genérico."""
    if isinstance(exc, materiales.ErrorMateriales):
        return MENSAJE_DATOS
    if isinstance(exc, (ModeloNoDisponible, ErrorGeneracion)):
        return str(exc)
    return None
