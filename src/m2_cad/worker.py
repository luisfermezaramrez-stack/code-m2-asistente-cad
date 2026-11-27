"""Worker de la cola persistente de trabajos SSE (HU-45).

Proceso separado de la API: reclama trabajos, ejecuta el pipeline y publica cada
evento en la cola. ``python -m m2_cad.worker`` es el entrypoint de despliegue.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import signal
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType

from fastapi import HTTPException

from m2_cad import seguimiento
from m2_cad.autenticacion import ANONIMO
from m2_cad.cola_trabajos import ColaTrabajos
from m2_cad.control import ControlGeneracion, GeneracionCancelada, SolicitudDeclinada
from m2_cad.observabilidad import contexto_solicitud
from m2_cad.registro import SIN_TRADUCCION, registrar

logger = logging.getLogger(__name__)

ProcesadorSSE = Callable[[str, ControlGeneracion, dict], dict[str, str]]
TRANSICIONES = {("iniciando", "validando"), ("validando", "generando")}


def cargar_procesador(ruta: str) -> ProcesadorSSE:
    """Resuelve ``modulo:funcion`` (o ``modulo.funcion``) sin importar la API por defecto."""
    if ":" in ruta:
        nombre_modulo, _, nombre_funcion = ruta.partition(":")
    else:
        nombre_modulo, _, nombre_funcion = ruta.rpartition(".")
    if not nombre_modulo or not nombre_funcion:
        raise ValueError(f"Procesador inválido: {ruta!r}; use modulo:funcion")
    return getattr(importlib.import_module(nombre_modulo), nombre_funcion)


def registrar_terminal(
    trabajo: dict,
    terminal: dict,
    medido: dict,
    configuracion: seguimiento.Configuracion,
    ruta_registro: Path,
) -> None:
    """Registra y mide una vez por trabajo; el id deduplica reanudaciones (RNF-3)."""
    from m2_cad.api import (
        _ESTADOS_CORRIDA_SSE,
        _registrar_version_inicial,
        medir_solicitud,
    )

    inicio = datetime.fromisoformat(trabajo["creado_en"])
    latencia_ms = (datetime.now(UTC) - inicio).total_seconds() * 1000
    registrar(
        texto=trabajo["texto"],
        traduccion=SIN_TRADUCCION,
        resultado=terminal.get("resultado"),
        latencia_ms=latencia_ms,
        error=terminal.get("motivo"),
        version=seguimiento.version_modelo(),
        ruta=ruta_registro,
        identificador=trabajo["id"],
        usuario=trabajo.get("usuario") or ANONIMO,
        causa=medido.get("causa"),
        prompt=medido.get("prompt"),
        prompt_hash=medido.get("prompt_hash"),
    )
    corrida = seguimiento.iniciar_corrida(
        configuracion.experimento_generacion,
        nombre=trabajo["id"],
        tags={
            "solicitud_id": trabajo["id"],
            "request_id": trabajo["request_id"],
            "job_id": trabajo["id"],
            "transporte": "sse",
            "usuario": trabajo.get("usuario") or ANONIMO,
        },
        configuracion=configuracion,
    )
    estado = _ESTADOS_CORRIDA_SSE.get(terminal["estado"], "error")
    if estado == "entregada":
        # HU-35: con la cola activa la pieza la construye este worker, así que es él
        # quien deja la versión 1 del historial (la misma función que las rutas API).
        _registrar_version_inicial(trabajo["id"], trabajo.get("usuario") or ANONIMO, medido)
    medir_solicitud(
        corrida,
        medido,
        configuracion,
        estado=estado,
        latencia_ms=latencia_ms,
        motivo_declinacion=terminal.get("motivo") if estado == "declinada" else None,
        error=f"HTTP {terminal.get('codigo_http', 500)}" if estado == "error" else None,
    )


def ejecutar(
    trabajo: dict,
    procesador: ProcesadorSSE,
    cola: ColaTrabajos,
    *,
    ruta_registro: Path | None = None,
    finalizador: Callable[[dict, dict, dict, seguimiento.Configuracion, Path], None] | None = None,
) -> dict:
    """Ejecuta un trabajo reclamado y publica su estado terminal."""
    identificador = trabajo["id"]
    medido: dict = dict(trabajo.get("medicion") or {})
    configuracion = seguimiento.Configuracion(**(trabajo.get("configuracion") or {}))
    ruta = Path(ruta_registro or trabajo.get("ruta_registro") or "data/registro.csv")
    finalizar = finalizador or registrar_terminal

    def informar(etapa: str) -> None:
        anterior = cola.estado(identificador)["estado"]
        if (anterior, etapa) not in TRANSICIONES:
            raise ValueError(f"Transición de progreso inválida: {anterior} -> {etapa}")
        if cola.estado(identificador)["cancelacion_solicitada"]:
            control.cancelacion.set()
        cola.publicar_evento(identificador, etapa)

    control = ControlGeneracion(informar)
    with contexto_solicitud(request_id=trabajo["request_id"], job_id=identificador):
        try:
            control.comprobar_cancelacion()
            resultado = procesador(trabajo["texto"], control, medido)
            if resultado.get("resultado") == "declinacion":
                raise SolicitudDeclinada(resultado.get("motivo", "Solicitud fuera del catálogo."))
            if cola.estado(identificador)["estado"] != "generando":
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
            logger.exception("Fallo en el worker %s", identificador)
            terminal = {
                "estado": "error",
                "motivo": "No fue posible completar la generación.",
                "codigo_http": 500,
            }

    cola.guardar_medicion(identificador, medido)
    if not trabajo.get("registrado"):
        try:
            finalizar(
                trabajo, {"solicitud_id": identificador, **terminal}, medido, configuracion, ruta
            )
        except Exception:
            logger.exception("Fallo de registro del trabajo %s", identificador)
            terminal = {
                "estado": "error",
                "motivo": "No fue posible registrar el resultado.",
                "codigo_http": 500,
            }
        cola.marcar_registrado(identificador)

    estado = terminal.pop("estado")
    return cola.publicar_evento(identificador, estado, **terminal)


def consumir(
    cola: ColaTrabajos,
    procesador: ProcesadorSSE,
    *,
    intervalo: float = 0.2,
    una_vez: bool = False,
    ruta_registro: Path | None = None,
    finalizador: Callable[[dict, dict, dict, seguimiento.Configuracion, Path], None] | None = None,
) -> int:
    """Drena los trabajos pendientes; con SIGTERM no toma nuevos y termina el actual."""
    cola.reanudar()
    procesados = 0
    while True:
        trabajo = cola.reclamar()
        if trabajo is None:
            if una_vez or (not cola.esta_aceptando() and not cola.hay_trabajos_activos()):
                return procesados
            time.sleep(intervalo)
            continue
        ejecutar(
            trabajo,
            procesador,
            cola,
            ruta_registro=ruta_registro,
            finalizador=finalizador,
        )
        procesados += 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HU-45: worker de la cola persistente")
    parser.add_argument("--cola", type=Path, default=None, help="Ruta del JSON de la cola")
    parser.add_argument(
        "--procesador",
        default="m2_cad.api:procesar_con_progreso",
        help="Procesador SSE modulo:funcion",
    )
    parser.add_argument("--registro", type=Path, default=None, help="CSV de registro")
    parser.add_argument("--intervalo", type=float, default=0.2)
    parser.add_argument("--una-vez", action="store_true", help="Procesa a lo sumo un trabajo")
    args = parser.parse_args(argv)

    cola = ColaTrabajos(args.cola)
    try:
        procesador = cargar_procesador(args.procesador)
    except (ImportError, AttributeError, ValueError) as exc:
        parser.exit(2, f"Procesador inválido: {exc}\n")

    def drenar(_senal: int, _marco: FrameType | None) -> None:
        logger.info("drenaje solicitado: no se aceptarán trabajos nuevos")
        cola.cerrar()

    signal.signal(signal.SIGTERM, drenar)
    signal.signal(signal.SIGINT, drenar)
    procesados = consumir(
        cola,
        procesador,
        intervalo=args.intervalo,
        una_vez=args.una_vez,
        ruta_registro=args.registro,
    )
    print(f"worker: {procesados} trabajos procesados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
