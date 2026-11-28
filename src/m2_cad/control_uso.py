"""Topes de uso, presupuesto diario e idempotencia de ``/generar`` (HU-32).

El estado vive en el proceso porque el servicio corre con ``--workers 1``. La
interfaz de ``ControlUso`` permite sustituirlo por un almacén compartido si el
despliegue escala, sin cambiar la API.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class ErrorControlUso(HTTPException):
    """Fallo tipado del control de uso; ``clase`` alimenta el seguimiento."""

    clase = "ErrorControlUso"
    tipo = "uso"

    def __init__(self, detail: str, *, headers: dict[str, str] | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail, headers=headers
        )


class LimiteVentanaExcedido(ErrorControlUso):
    """RF-1/AC3: demasiadas solicitudes de una sesión en la ventana."""

    clase = "LimiteVentanaExcedido"
    tipo = "ventana"

    def __init__(self, limite: int, ventana_segundos: int, reintentar_en: int) -> None:
        super().__init__(
            f"Límite de {limite} solicitudes por {ventana_segundos} s excedido para esta sesión.",
            headers={
                "X-Limite-Tipo": self.tipo,
                "Retry-After": str(max(1, reintentar_en)),
            },
        )


class PresupuestoExcedido(ErrorControlUso):
    """RF-2/AC1: el gasto acumulado del día alcanzó el presupuesto."""

    clase = "PresupuestoExcedido"
    tipo = "presupuesto"

    def __init__(self, presupuesto: float) -> None:
        super().__init__(
            f"Presupuesto diario de {presupuesto:.4f} USD agotado.",
            headers={"X-Limite-Tipo": self.tipo},
        )


class ConflictoIdempotencia(HTTPException):
    """RF-4: la clave ya se usó con otro texto, sesión o transporte."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="La clave de idempotencia ya fue usada con otra solicitud.",
            headers={"X-Limite-Tipo": "idempotencia"},
        )
        self.clase = "ConflictoIdempotencia"
        self.tipo = "idempotencia"


def _entero(env: Mapping[str, str], nombre: str, por_defecto: int, minimo: int = 0) -> int:
    """Lee un entero no negativo; un valor inválido no rompe el arranque."""
    crudo = env.get(nombre)
    if crudo is None or not crudo.strip():
        return por_defecto
    try:
        valor = int(crudo)
    except ValueError:
        logger.warning("Variable %s inválida (%r); se usa %s", nombre, crudo, por_defecto)
        return por_defecto
    if valor < minimo:
        logger.warning("Variable %s debe ser >= %d; se usa %s", nombre, minimo, por_defecto)
        return por_defecto
    return valor


def _flotante(env: Mapping[str, str], nombre: str, por_defecto: float) -> float:
    """Lee un float finito no negativo; un valor inválido no rompe el arranque."""
    crudo = env.get(nombre)
    if crudo is None or not crudo.strip():
        return por_defecto
    try:
        valor = float(crudo)
    except ValueError:
        logger.warning("Variable %s inválida (%r); se usa %s", nombre, crudo, por_defecto)
        return por_defecto
    if not math.isfinite(valor) or valor < 0:
        logger.warning("Variable %s debe ser finita y >= 0; se usa %s", nombre, por_defecto)
        return por_defecto
    return valor


@dataclass(frozen=True)
class ConfiguracionUso:
    """Configuración efectiva; cero desactiva cada control."""

    limite_ventana: int = 0
    ventana_segundos: int = 60
    presupuesto_diario_usd: float = 0.0

    @classmethod
    def desde_entorno(cls, entorno: Mapping[str, str] | None = None) -> ConfiguracionUso:
        env = os.environ if entorno is None else entorno
        return cls(
            limite_ventana=_entero(env, "M2_LIMITE_SOLICITUDES_VENTANA", 0),
            ventana_segundos=_entero(env, "M2_VENTANA_SEGUNDOS", 60, minimo=1),
            presupuesto_diario_usd=_flotante(env, "M2_PRESUPUESTO_DIARIO_USD", 0.0),
        )


@dataclass
class RegistroIdempotencia:
    """Reserva de una clave, con la respuesta original cuando ya terminó."""

    solicitud_id: str
    huella: str
    transporte: str
    respuesta: dict[str, str] | None = None
    cabeceras: dict[str, str] = field(default_factory=dict)
    estado_final: dict | None = None


class ControlUso:
    """Contadores por sesión, gasto del día y cache de idempotencia en memoria."""

    def __init__(
        self,
        configuracion: ConfiguracionUso | None = None,
        *,
        reloj: Callable[[], float] | None = None,
        hoy: Callable[[], date] | None = None,
    ) -> None:
        self.configuracion = configuracion or ConfiguracionUso.desde_entorno()
        self._reloj = reloj or time.monotonic
        self._hoy = hoy or (lambda: datetime.now(timezone.utc).date())
        self._lock = threading.Lock()
        self._ventanas: dict[str, deque[float]] = defaultdict(deque)
        self._gasto: dict[date, float] = defaultdict(float)
        self._generaciones: dict[date, int] = defaultdict(int)
        self._idempotencia: dict[str, RegistroIdempotencia] = {}

    def reservar(self, sesion: str) -> None:
        """RF-3: verifica topes y contabiliza antes de crear el trabajo."""
        ahora = self._reloj()
        with self._lock:
            dia = self._hoy()
            presupuesto = self.configuracion.presupuesto_diario_usd
            if presupuesto > 0 and self._gasto[dia] >= presupuesto:
                raise PresupuestoExcedido(presupuesto)

            self._ocupar_ventana(sesion, ahora)

    def reservar_ventana(self, sesion: str) -> None:
        """Solo el tope por ventana, para construcciones sin LLM ni gasto (HU-49)."""
        ahora = self._reloj()
        with self._lock:
            self._ocupar_ventana(sesion, ahora)

    def _ocupar_ventana(self, sesion: str, ahora: float) -> None:
        """Cuenta una solicitud en la ventana de la sesión; requiere `self._lock`."""
        limite = self.configuracion.limite_ventana
        if limite <= 0:
            return
        ventana = self.configuracion.ventana_segundos
        cola = self._ventanas[sesion]
        while cola and ahora - cola[0] >= ventana:
            cola.popleft()
        if len(cola) >= limite:
            espera = max(1, math.ceil(ventana - (ahora - cola[0])))
            raise LimiteVentanaExcedido(limite, ventana, espera)
        cola.append(ahora)

    def registrar_gasto(self, costo_usd: float, *, dia: date | None = None) -> None:
        """AC4: suma el costo ya calculado por el seguimiento, nunca uno inventado.

        ``dia`` atribuye el gasto al día UTC en que terminó un trabajo de la cola
        (HU-45); sin él cuenta para hoy.
        """
        if not math.isfinite(costo_usd) or costo_usd < 0:
            logger.warning("Costo ignorado por no ser finito y no negativo: %r", costo_usd)
            return
        with self._lock:
            dia = dia or self._hoy()
            self._gasto[dia] += costo_usd
            self._generaciones[dia] += 1

    def gasto_acumulado(self) -> dict:
        """RF-5: agregado del día en UTC, sin identificadores de cliente."""
        with self._lock:
            dia = self._hoy()
            return {
                "fecha": dia,
                "costo_usd": self._gasto[dia],
                "moneda": "USD",
                "generaciones": self._generaciones[dia],
                "presupuesto_diario_usd": self.configuracion.presupuesto_diario_usd,
                "limite_solicitudes_ventana": self.configuracion.limite_ventana,
                "ventana_segundos": self.configuracion.ventana_segundos,
            }

    @staticmethod
    def _huella(sesion: str, texto: str, transporte: str) -> str:
        material = json.dumps(
            [sesion, texto, transporte], ensure_ascii=False, separators=(",", ":")
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def reservar_idempotencia(
        self,
        clave: str | None,
        sesion: str,
        texto: str,
        transporte: str,
        solicitud_id: str,
    ) -> tuple[bool, RegistroIdempotencia]:
        """Devuelve ``(es_reintento, registro)`` de forma atómica (AC2)."""
        if not clave:
            return False, RegistroIdempotencia(solicitud_id, "", transporte)
        huella = self._huella(sesion, texto, transporte)
        with self._lock:
            registro = self._idempotencia.get(clave)
            if registro is not None:
                if registro.huella != huella or registro.transporte != transporte:
                    raise ConflictoIdempotencia()
                return True, registro
            registro = RegistroIdempotencia(
                solicitud_id=solicitud_id, huella=huella, transporte=transporte
            )
            self._idempotencia[clave] = registro
            return False, registro

    def liberar_idempotencia(self, clave: str | None, registro: RegistroIdempotencia) -> None:
        """Deshace la reserva si la solicitud fue rechazada o falló."""
        if not clave:
            return
        with self._lock:
            if self._idempotencia.get(clave) is registro:
                del self._idempotencia[clave]

    def vincular_idempotencia(
        self, clave: str | None, registro: RegistroIdempotencia, solicitud_id: str
    ) -> None:
        """Asocia la clave al id real del trabajo SSE, que difiere del de la solicitud."""
        if not clave:
            return
        with self._lock:
            if self._idempotencia.get(clave) is registro:
                registro.solicitud_id = solicitud_id

    def confirmar_idempotencia(
        self,
        clave: str | None,
        registro: RegistroIdempotencia,
        *,
        respuesta: dict[str, str] | None = None,
        cabeceras: Mapping[str, str] | None = None,
        estado_final: dict | None = None,
    ) -> None:
        """Guarda lo necesario para repetir la generación sin pagarla de nuevo."""
        if not clave:
            return
        with self._lock:
            if self._idempotencia.get(clave) is not registro:
                return
            registro.respuesta = respuesta
            registro.cabeceras = dict(cabeceras or {})
            if estado_final is not None:
                registro.estado_final = estado_final
