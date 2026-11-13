"""Control cooperativo independiente del motor CAD y del transporte HTTP."""

from collections.abc import Callable
from threading import Event


class GeneracionCancelada(RuntimeError):
    """El pipeline alcanzó un punto seguro y dejó de ejecutar etapas locales."""


class SolicitudDeclinada(RuntimeError):
    """Declinación de dominio, distinta de un error de validación o de servicio."""


class ControlGeneracion:
    """Notifica etapas reales y comprueba cancelación entre llamadas bloqueantes."""

    def __init__(self, informar: Callable[[str], None]) -> None:
        self.cancelacion = Event()
        self._informar = informar

    def comprobar_cancelacion(self) -> None:
        if self.cancelacion.is_set():
            raise GeneracionCancelada("El pipeline local se detuvo en un punto seguro.")

    def informar(self, etapa: str) -> None:
        self.comprobar_cancelacion()
        self._informar(etapa)
