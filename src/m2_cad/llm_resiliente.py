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
# Sólo estos 5xx son transitorios; 501 y 505 no se reintentan.
_ESTADOS_TRANSITORIOS = frozenset({500, 502, 503, 504})
# La espera se corta en tramos para atender la cancelación del trabajo SSE.
_PASO_ESPERA = 0.05


class ConfiguracionInvalida(ValueError):
    """Variable de entorno de HU-25 con un valor inválido."""


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
        raise ConfiguracionInvalida(f"{nombre} debe ser un entero.") from exc
    if not 0 <= valor <= maximo:
        raise ConfiguracionInvalida(f"{nombre} debe estar entre 0 y {maximo}.")
    return valor


def _config_float(nombre: str, defecto: float, maximo: float) -> float:
    try:
        valor = float(os.getenv(nombre, str(defecto)))
    except ValueError as exc:
        raise ConfiguracionInvalida(f"{nombre} debe ser un número.") from exc
    if not 0 <= valor <= maximo or not float("-inf") < valor < float("inf"):
        raise ConfiguracionInvalida(f"{nombre} debe estar entre 0 y {maximo}.")
    return valor


def _huella_credencial() -> str:
    """Huella no reversible de la credencial activa; la clave nunca se guarda."""
    clave = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


def _clave_normalizada(cuerpo: dict, url: str, credencial: str | None) -> str:
    """Normaliza endpoint y cuerpo; la credencial entra sólo en la caché en memoria."""
    datos: dict[str, object] = {"url": url, "cuerpo": cuerpo}
    if credencial is not None:
        datos["credencial"] = credencial
    serializado = json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def clave_cuerpo(cuerpo: dict, url: str) -> str:
    """Clave canónica de una petición, sin secretos (HU-44, SPEC-045).

    Es la misma normalización que usa la caché de HU-25, pero sin la huella de la
    credencial: así un artefacto grabado funciona igual en el host con API key y
    en CI sin ella. Nunca incluye cabeceras ni el valor de la clave.
    """
    return _clave_normalizada(cuerpo, url, None)


def _clave(cuerpo: dict, url: str) -> str:
    """La clave de la caché incluye endpoint, prompt, parámetros y credencial."""
    return _clave_normalizada(cuerpo, url, _huella_credencial())


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


def _esperar(segundos: float, cancelado: Callable[[], None] | None) -> None:
    """Espera el backoff en tramos cortos para atender la cancelación del trabajo."""
    if cancelado is None:
        if segundos > 0:
            time.sleep(segundos)
        return
    fin = time.monotonic() + segundos
    while True:
        cancelado()
        restante = fin - time.monotonic()
        if restante <= 0:
            return
        time.sleep(min(restante, _PASO_ESPERA))


def consultar(
    cuerpo: dict,
    *,
    url: str,
    timeout: float,
    proveedor: Callable[..., dict],
    cancelado: Callable[[], None] | None = None,
    validador: Callable[[dict], object] | None = None,
) -> dict:
    """Llama al proveedor con un plazo total y reintentos acotados (HU-25).

    - Reintenta sólo HTTP 500, 502, 503 y 504, timeout y fallo de transporte.
      Cualquier 4xx (401, 402, 429, ...) y los 5xx permanentes no se reintentan.
    - ``timeout`` es el plazo total de todos los intentos, no el de cada uno.
    - ``cancelado`` se invoca antes de cada intento y durante la espera; debe
      lanzar (por ejemplo, ``ControlGeneracion.comprobar_cancelacion``) para
      detener los reintentos y evitar llamadas pagas adicionales.
    - ``validador`` se ejecuta antes de guardar en caché; si lanza, la respuesta
      no se cachea. Así una salida inválida del modelo no se reutiliza durante
      el TTL.
    """
    reiniciar_metricas()
    metricas = _METRICAS.get()
    assert metricas is not None
    # Un trabajo cancelado no debe consumir ni siquiera una respuesta cacheada.
    if cancelado is not None:
        cancelado()

    reintentos_maximos = _config_entera("LLM_MAX_RETRIES", 2, 5)
    base = _config_float("LLM_RETRY_BASE_SECONDS", 0.25, 30)
    espera_maxima = _config_float("LLM_RETRY_MAX_SECONDS", 3.0, 120)
    ttl = _config_entera("LLM_CACHE_TTL_SECONDS", 1800, 2_592_000)
    capacidad = _config_entera("LLM_CACHE_MAX_ITEMS", 256, 10_000)

    clave = _clave(cuerpo, url) if ttl and capacidad else None
    if clave is not None:
        guardada = _buscar(clave)
        if guardada is not None:
            metricas["llm_cache_hit"] = 1
            return guardada
        metricas["llm_cache_miss"] = 1

    limite = time.monotonic() + max(0.0, timeout)
    ultimo_error: Exception | None = None
    for intento in range(reintentos_maximos + 1):
        if cancelado is not None:
            cancelado()
        restante = limite - time.monotonic()
        if restante <= 0:
            break
        if intento:
            metricas["llm_reintentos"] += 1
        try:
            respuesta = proveedor(cuerpo, url=url, timeout=min(timeout, restante))
        except httpx.HTTPStatusError as exc:
            ultimo_error = exc
            if exc.response.status_code not in _ESTADOS_TRANSITORIOS:
                raise
            if intento >= reintentos_maximos:
                raise
        except httpx.TransportError as exc:
            ultimo_error = exc
            if intento >= reintentos_maximos:
                raise
        else:
            if validador is not None:
                validador(respuesta)
            if clave is not None:
                _guardar(clave, respuesta, ttl, capacidad)
            return respuesta
        espera = min(espera_maxima, base * (2**intento) * random.uniform(0.5, 1.5))
        espera = min(espera, max(0.0, limite - time.monotonic()))
        _esperar(espera, cancelado)

    if ultimo_error is not None:
        raise ultimo_error
    raise httpx.ReadTimeout("El plazo total para el LLM se agotó antes del primer intento.")
