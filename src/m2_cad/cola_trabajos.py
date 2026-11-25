"""Cola persistente de trabajos SSE apoyada en SPEC-031 (HU-45).

El archivo se publica con ``_publicar_bytes`` bajo ``_bloqueo``: cada lectura ve un
JSON completo y cada evento SSE se escribe entero, sin ventanas a medias.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from m2_cad.persistencia_registro import _bloqueo, _publicar_bytes

logger = logging.getLogger(__name__)

RUTA_DEFAULT = Path("data/cola.json")
VERSION = 1
TERMINALES = frozenset({"verificado", "declinado", "error", "cancelado"})
CLAVES_PUBLICAS = (
    "resultado",
    "motivo",
    "codigo_http",
    "pipeline_detenido",
    "cancelacion_remota_confirmada",
)


def _ahora() -> str:
    return datetime.now(UTC).isoformat()


def _codificar(datos: Any) -> str:
    return json.dumps(datos, ensure_ascii=False, sort_keys=True, default=str)


class ColaTrabajos:
    """Estado persistente de la cola; subclases de api no son necesarias."""

    def __init__(self, ruta: Path | str | None = None, propietario: str | None = None) -> None:
        self.ruta = Path(ruta or os.environ.get("M2_COLA_PATH") or RUTA_DEFAULT)
        self.propietario = propietario or uuid.uuid4().hex[:12]

    def _cargar(self) -> dict:
        if not self.ruta.exists():
            return {"version": VERSION, "aceptando": True, "trabajos": {}}
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        if datos.get("version") != VERSION:
            raise ValueError(f"Versión de cola no soportada: {datos.get('version')!r}")
        datos.setdefault("aceptando", True)
        datos.setdefault("trabajos", {})
        return datos

    @contextmanager
    def _editar(self) -> Iterator[dict]:
        with _bloqueo(self.ruta):
            datos = self._cargar()
            yield datos
            _publicar_bytes(self.ruta, _codificar(datos).encode("utf-8"))

    @staticmethod
    def _estado_publico(trabajo: dict) -> dict:
        ultimo = trabajo.get("ultimo") or {}
        extras = {clave: ultimo[clave] for clave in CLAVES_PUBLICAS if clave in ultimo}
        return {
            "solicitud_id": trabajo["id"],
            "estado": trabajo["estado"],
            "terminal": trabajo["estado"] in TERMINALES,
            "cancelacion_solicitada": bool(trabajo["cancelacion_solicitada"]),
            "secuencia": trabajo["secuencia"],
            **extras,
        }

    def encolar(
        self,
        texto: str,
        *,
        solicitud_id: str | None = None,
        request_id: str | None = None,
        configuracion: dict | None = None,
        ruta_registro: Path | str | None = None,
    ) -> TrabajoPersistido:
        """Acepta un trabajo nuevo; el worker lo ejecutará fuera de la API (AC3)."""
        identificador = solicitud_id or uuid.uuid4().hex
        trabajo = {
            "id": identificador,
            "texto": texto,
            "request_id": request_id or identificador,
            "estado": "iniciando",
            "secuencia": 0,
            "eventos": [],
            "ultimo": {},
            "cancelacion_solicitada": False,
            "en_proceso": False,
            "propietario": None,
            "intentos": 0,
            "registrado": False,
            "medicion": {},
            "configuracion": configuracion or {},
            "ruta_registro": str(ruta_registro or Path("data/registro.csv")),
            "creado_en": _ahora(),
            "actualizado_en": _ahora(),
        }
        with self._editar() as datos:
            if not datos["aceptando"]:
                raise HTTPException(503, "El servicio está drenando; no acepta nuevas solicitudes.")
            datos["trabajos"][identificador] = trabajo
        return TrabajoPersistido(self, identificador)

    def reanudar(self) -> int:
        """RF-3: devuelve a pendientes los trabajos de un worker caído."""
        cuenta = 0
        with self._editar() as datos:
            for trabajo in datos["trabajos"].values():
                if trabajo["en_proceso"]:
                    # El nuevo worker vuelve a emitir desde 'validando': se conserva
                    # la secuencia, pero no se reenvían eventos de la ejecución caída.
                    trabajo["estado"] = "iniciando"
                    trabajo["eventos"] = []
                    trabajo["ultimo"] = {}
                    trabajo["en_proceso"] = False
                    trabajo["propietario"] = None
                    trabajo["actualizado_en"] = _ahora()
                    cuenta += 1
        if cuenta:
            logger.info("trabajos reanudados tras reinicio: %d", cuenta)
        return cuenta

    def reclamar(self) -> dict | None:
        """Toma un trabajo de forma atómica; nunca devuelve uno terminal (RF-2)."""
        with self._editar() as datos:
            if not datos["aceptando"]:
                return None
            candidato = next(
                (
                    trabajo
                    for trabajo in datos["trabajos"].values()
                    if trabajo["estado"] not in TERMINALES and not trabajo["en_proceso"]
                ),
                None,
            )
            if candidato is None:
                return None
            candidato["en_proceso"] = True
            candidato["propietario"] = self.propietario
            candidato["intentos"] += 1
            candidato["actualizado_en"] = _ahora()
            return copy.deepcopy(candidato)

    def estado(self, solicitud_id: str) -> dict:
        with _bloqueo(self.ruta):
            trabajo = self._cargar()["trabajos"].get(solicitud_id)
        if trabajo is None:
            raise HTTPException(404, "Solicitud desconocida o fuera de retención.")
        return self._estado_publico(trabajo)

    def eventos_desde(self, solicitud_id: str, secuencia: int) -> list[dict]:
        with _bloqueo(self.ruta):
            trabajo = self._cargar()["trabajos"].get(solicitud_id)
        if trabajo is None:
            raise HTTPException(404, "Solicitud desconocida o fuera de retención.")
        return copy.deepcopy([e for e in trabajo["eventos"] if e["secuencia"] > secuencia])

    def publicar_evento(self, solicitud_id: str, estado: str, **datos: Any) -> dict:
        """Publica un evento completo y actualiza el estado del trabajo."""
        with self._editar() as registro:
            trabajo = registro["trabajos"].get(solicitud_id)
            if trabajo is None:
                raise HTTPException(404, "Solicitud desconocida o fuera de retención.")
            if trabajo["estado"] in TERMINALES:
                return self._estado_publico(trabajo)
            trabajo["secuencia"] += 1
            evento = {
                "solicitud_id": solicitud_id,
                "secuencia": trabajo["secuencia"],
                "estado": estado,
                "terminal": estado in TERMINALES,
                "cancelacion_solicitada": bool(trabajo["cancelacion_solicitada"]),
                **datos,
            }
            trabajo["eventos"].append(evento)
            trabajo["ultimo"] = evento
            trabajo["estado"] = estado
            trabajo["actualizado_en"] = _ahora()
            if evento["terminal"]:
                trabajo["en_proceso"] = False
            return self._estado_publico(trabajo)

    def guardar_medicion(self, solicitud_id: str, medicion: dict) -> None:
        with self._editar() as datos:
            trabajo = datos["trabajos"].get(solicitud_id)
            if trabajo is not None:
                trabajo["medicion"] = json.loads(_codificar(medicion))

    def marcar_registrado(self, solicitud_id: str) -> None:
        with self._editar() as datos:
            trabajo = datos["trabajos"].get(solicitud_id)
            if trabajo is not None:
                trabajo["registrado"] = True

    def cancelar(self, solicitud_id: str) -> dict:
        """Solicita cancelación cooperativa; no adelanta el estado terminal."""
        with self._editar() as datos:
            trabajo = datos["trabajos"].get(solicitud_id)
            if trabajo is None:
                raise HTTPException(404, "Solicitud desconocida o fuera de retención.")
            if trabajo["estado"] not in TERMINALES:
                trabajo["cancelacion_solicitada"] = True
            return self._estado_publico(trabajo)

    def cerrar(self) -> None:
        """RF-4: deja de aceptar trabajos nuevos sin interrumpir los activos."""
        with self._editar() as datos:
            datos["aceptando"] = False

    def abrir(self) -> None:
        with self._editar() as datos:
            datos["aceptando"] = True

    def esta_aceptando(self) -> bool:
        with _bloqueo(self.ruta):
            return bool(self._cargar()["aceptando"])

    def hay_trabajos_activos(self) -> bool:
        with _bloqueo(self.ruta):
            return any(t["estado"] not in TERMINALES for t in self._cargar()["trabajos"].values())


class TrabajoPersistido:
    """Vista de un trabajo en cola con la interfaz de ``Trabajo`` (RNF-1)."""

    def __init__(self, cola: ColaTrabajos, solicitud_id: str) -> None:
        self.cola = cola
        self.id = solicitud_id

    def estado(self) -> dict:
        return self.cola.estado(self.id)

    def cancelar(self) -> dict:
        return self.cola.cancelar(self.id)

    async def eventos(self, request: Request) -> AsyncIterator[str]:
        """SSE lee eventos ya completos; el drenaje nunca corta un evento a medias."""
        ultimo_envio = time.monotonic()
        secuencia = 0
        try:
            while True:
                if await request.is_disconnected():
                    return
                eventos = self.cola.eventos_desde(self.id, secuencia)
                if eventos:
                    for evento in eventos:
                        secuencia = evento["secuencia"]
                        yield (
                            f"id: {self.id}:{evento['secuencia']}\n"
                            f"event: {evento['estado']}\n"
                            f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
                        )
                        ultimo_envio = time.monotonic()
                        if evento["terminal"]:
                            return
                    continue
                if time.monotonic() - ultimo_envio >= 15:
                    yield ": keep-alive\n\n"
                    ultimo_envio = time.monotonic()
                await asyncio.sleep(0.05)
        finally:
            self.cancelar()
