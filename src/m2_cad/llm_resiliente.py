"""Reintentos HTTP y caché local del LLM (HU-25 / SPEC-026).

No almacena claves API ni cabeceras; sólo la respuesta JSON del proveedor.
La caché es por proceso: no sustituye idempotencia ni controles de costo (HU-32).
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import random
import time
from collections import OrderedDict
from collections.abc import Callable
from contextvars import ContextVar
from threading import Lock

import httpx

# Métricas separadas por hilo/contexto de ejecución de cada generación.
_METRICAS: ContextVar[dict[str, int] | None] = ContextVar("hu25_metricas", default=None)
_CACHE: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_CERROJO = Lock()


def reiniciar_metricas() -> None:
    """Evita reutilizar métricas de una generación anterior en el mismo hilo."""
    _METRICAS.set({"llm_reintentos": 0, "llm_cache_hit": 0, "llm_cache_miss": 0})


def metricas_actuales() -> dict[str, int]:
    """Métricas acumuladas de la llamada actual, sin datos sensibles."""
    return dict(_METRICAS.get() or {})


def _config_entera(nombre: str, defecto: int, maximo: int) -> int:
    try:
        valor = int(os.getenv(nombre, str(defecto)))
    except ValueError as exc:
        raise ValueError(f"{nombre} debe ser un entero.") from exc
    if not 0 <= valor <= maximo:
        raise ValueError(f"{nombre} debe estar entre 0 y {maximo}.")
    return valor


def _config_float(nombre: str, defecto: float, maximo: float) -> float:
    try:
        valor = float(os.getenv(nombre, str(defecto)))
    except ValueError as exc:
        raise ValueError(f"{nombre} debe ser un número.") from exc
    if not 0 <= valor <= maximo or not float("-inf") < valor < float("inf"):
        raise ValueError(f"{nombre} debe estar entre 0 y {maximo}.")
    return valor


def _clave(cuerpo: dict, url: str) -> str:
    """La clave incluye prompt, modelo, parámetros y endpoint (sólo hash)."""
    datos = json.dumps(
        {"url": url, "cuerpo": cuerpo}, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(datos.encode("utf-8")).hexdigest()


def _buscar(clave: str) -> dict | None:
    with _CERROJO:
        entrada = _CACHE.get(clave)
        if entrada is None:
            return None
        vencimiento, respuesta = entrada
        if time.monotonic() >= vencimiento:
            del _CACHE[clave]
            return None
        _CACHE.move_to_end(clave)
        resultado = copy.deepcopy(respuesta)
    # El usage del primer cobro no se atribuye nuevamente a esta solicitud.
    resultado["usage"] = {}
    return resultado


def _guardar(clave: str, respuesta: dict, ttl: int, capacidad: int) -> None:
    # Nunca conservar credenciales ni cabeceras: únicamente campos del JSON del LLM.
    if not isinstance(respuesta, dict):
        return
    opciones = respuesta.get("choices")
    if not isinstance(opciones, list) or not opciones:
        return
    try:
        contenido = opciones[0]["message"]["content"]
    except (KeyError, TypeError, IndexError):
        return
    if not isinstance(contenido, str):
        return
    limpio = {
        clave_respuesta: copy.deepcopy(respuesta[clave_respuesta])
        for clave_respuesta in ("model", "choices", "usage", "id")
        if clave_respuesta in respuesta
    }
    with _CERROJO:
        _CACHE[clave] = (time.monotonic() + ttl, limpio)
        _CACHE.move_to_end(clave)
        while len(_CACHE) > capacidad:
            _CACHE.popitem(last=False)


def consultar(
    cuerpo: dict,
    *,
    url: str,
    timeout: float,
    proveedor: Callable[..., dict],
) -> dict:
    """Llama al proveedor, reintentando sólo 5xx, timeout y fallo de transporte.

    429 NO se reintenta para preservar el mensaje y límite del proveedor.
    Sólo cachea respuestas HTTP exitosas con contenido; no cachea errores.
    """
    reintentos_maximos = _config_entera("LLM_MAX_RETRIES", 2, 5)
    base = _config_float("LLM_RETRY_BASE_SECONDS", 0.25, 30)
    espera_maxima = _config_float("LLM_RETRY_MAX_SECONDS", 3.0, 120)
    ttl = _config_entera("LLM_CACHE_TTL_SECONDS", 1800, 2_592_000)
    capacidad = _config_entera("LLM_CACHE_MAX_ITEMS", 256, 10_000)

    reiniciar_metricas()
    metricas = _METRICAS.get()
    assert metricas is not None

    clave = _clave(cuerpo, url) if ttl and capacidad else None
    if clave is not None:
        guardada = _buscar(clave)
        if guardada is not None:
            metricas["llm_cache_hit"] = 1
            return guardada
        metricas["llm_cache_miss"] = 1

    for intento in range(reintentos_maximos + 1):
        try:
            respuesta = proveedor(cuerpo, url=url, timeout=timeout)
            if clave is not None:
                _guardar(clave, respuesta, ttl, capacidad)
            return respuesta
        except httpx.HTTPStatusError as exc:
            transitorio = 500 <= exc.response.status_code < 600
            if not transitorio or intento >= reintentos_maximos:
                raise
        except httpx.TransportError:
            if intento >= reintentos_maximos:
                raise
        metricas["llm_reintentos"] += 1
        espera = min(espera_maxima, base * (2**intento) * random.uniform(0.5, 1.5))
        if espera > 0:
            time.sleep(espera)

    raise AssertionError("Bucle de reintentos finalizado sin resultado.")
