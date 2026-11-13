"""Trabajos SSE en memoria; cancelación cooperativa, sin matar hilos CAD."""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable
from queue import Empty, Queue
from threading import Lock, Thread

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from m2_cad.seguimiento import (
    ControlGeneracion,
    GeneracionCancelada,
    SolicitudDeclinada,
)

logger = logging.getLogger(__name__)
Procesador = Callable[[str, ControlGeneracion], dict[str, str]]
AlFinalizar = Callable[[dict], None]
TERMINALES = frozenset({"verificado", "declinado", "error", "cancelado"})


class Trabajo:
    """Un único productor y terminal; la cancelación no adelanta el resultado."""

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self._lock = Lock()
        self._eventos: Queue[dict] = Queue()
        self._ultimo: dict = {"solicitud_id": self.id, "estado": "iniciando", "terminal": False}
        self._secuencia = 0
        self.control = ControlGeneracion(self._informar)

    def estado(self) -> dict:
        with self._lock:
            return {**self._ultimo, "cancelacion_solicitada": self.control.cancelacion.is_set()}

    def cancelar(self) -> dict:
        with self._lock:
            if not self._ultimo["terminal"]:
                self.control.cancelacion.set()
            return {**self._ultimo, "cancelacion_solicitada": self.control.cancelacion.is_set()}

    def _publicar(self, estado: str, **datos: object) -> None:
        with self._lock:
            if self._ultimo["terminal"]:
                return
            self._secuencia += 1
            self._ultimo = {
                "solicitud_id": self.id,
                "secuencia": self._secuencia,
                "estado": estado,
                "terminal": estado in TERMINALES,
                **datos,
            }
            self._eventos.put(
                {**self._ultimo, "cancelacion_solicitada": self.control.cancelacion.is_set()}
            )

    def _informar(self, etapa: str) -> None:
        anterior = self.estado()["estado"]
        if (anterior, etapa) not in {("iniciando", "validando"), ("validando", "generando")}:
            raise ValueError("Transición de progreso inválida.")
        self._publicar(etapa)

    def ejecutar(self, texto: str, procesador: Procesador, al_finalizar: AlFinalizar) -> None:
        """No confirma cancelación hasta que el procesador sale por un punto seguro."""
        try:
            self.control.comprobar_cancelacion()
            resultado = procesador(texto, self.control)
            if resultado.get("resultado") == "declinacion":
                raise SolicitudDeclinada(resultado.get("motivo", "Solicitud fuera de catálogo."))
            if self.estado()["estado"] != "generando":
                raise ValueError("El procesador no informó las etapas reales.")
            terminal = {"estado": "verificado", "resultado": resultado}
        except GeneracionCancelada:
            terminal = {
                "estado": "cancelado",
                "motivo": "El pipeline local se detuvo en un punto seguro.",
                "pipeline_detenido": True,
                "cancelacion_remota_confirmada": False,
            }
        except SolicitudDeclinada as exc:
            terminal = {"estado": "declinado", "motivo": str(exc), "codigo_http": 422}
        except HTTPException as exc:
            terminal = {
                "estado": "error",
                "motivo": str(exc.detail),
                "codigo_http": exc.status_code,
            }
        except Exception:
            logger.exception("Fallo en generación SSE %s", self.id)
            terminal = {
                "estado": "error",
                "motivo": "No fue posible completar la generación.",
                "codigo_http": 500,
            }
        try:
            al_finalizar(terminal)
        except Exception:
            logger.exception("Fallo de registro SSE %s", self.id)
            terminal = {
                "estado": "error",
                "motivo": "No fue posible registrar el resultado.",
                "codigo_http": 500,
            }
        self._publicar(**terminal)

    async def eventos(self, request: Request) -> AsyncIterator[str]:
        """Desconectar solicita cancelación; el hilo conserva su vida hasta salir."""
        ultimo_envio = time.monotonic()
        try:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    evento = self._eventos.get_nowait()
                except Empty:
                    if time.monotonic() - ultimo_envio >= 15:
                        yield ": keep-alive\n\n"
                        ultimo_envio = time.monotonic()
                    await asyncio.sleep(0.05)
                    continue
                yield (
                    f"id: {self.id}:{evento['secuencia']}\n"
                    f"event: {evento['estado']}\n"
                    f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
                )
                ultimo_envio = time.monotonic()
                if evento["terminal"]:
                    return
        finally:
            self.cancelar()


class GestorTrabajos:
    """Retención acotada al proceso; los activos nunca se expulsan del registro."""

    def __init__(self, capacidad: int = 128) -> None:
        self._trabajos: dict[str, Trabajo] = {}
        self._lock = Lock()
        self.capacidad = capacidad

    def crear(self, texto: str, procesador: Procesador, al_finalizar: AlFinalizar) -> Trabajo:
        with self._lock:
            if len(self._trabajos) >= self.capacidad:
                terminado = next(
                    (
                        id_
                        for id_, trabajo in self._trabajos.items()
                        if trabajo.estado()["terminal"]
                    ),
                    None,
                )
                if terminado is None:
                    raise HTTPException(503, "No hay capacidad para otra generación.")
                del self._trabajos[terminado]
            trabajo = Trabajo()
            self._trabajos[trabajo.id] = trabajo
        Thread(
            target=trabajo.ejecutar,
            args=(texto, procesador, al_finalizar),
            daemon=True,
            name=f"cad-{trabajo.id}",
        ).start()
        return trabajo

    def obtener(self, solicitud_id: str) -> Trabajo:
        with self._lock:
            trabajo = self._trabajos.get(solicitud_id)
        if trabajo is None:
            raise HTTPException(404, "Solicitud desconocida o fuera de retención.")
        return trabajo


class RespuestaSSE(StreamingResponse):
    """Solicita cancelación incluso si ASGI falla al enviar cabeceras o datos."""

    def __init__(self, trabajo: Trabajo, request: Request) -> None:
        self.trabajo = trabajo
        super().__init__(
            trabajo.eventos(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "X-Solicitud-ID": trabajo.id,
                "Vary": "Accept",
            },
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.trabajo.cancelar()
