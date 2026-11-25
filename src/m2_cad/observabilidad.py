"""Observabilidad central del paquete: logs JSON y trazas correlacionadas (HU-24).

Especificación: specs/025-hu-24-logging-estructurado/spec.md
- AC1: reconstruir una solicitud filtrando por un único `request_id`.
- AC2: una línea JSON por evento con nivel, módulo, mensaje y marca de tiempo.
- AC3: ningún secreto aparece en los registros ante un error del proveedor.
- RF-5: reutilizar un `X-Request-ID` válido y generarlo si falta o no es válido.

Los identificadores se propagan con `contextvars`: no es necesario pasarlos a cada llamada
de logging. El hilo de un trabajo SSE recibe una copia del contexto de la solicitud.
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import UTC, datetime

from m2_cad.registro import _sanitizar

VARIABLE_NIVEL = "M2_LOG_LEVEL"
NIVEL_PREDETERMINADO = "INFO"
NIVELES = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
LONGITUD_MAXIMA = 4000
MARCADOR = "[REDACTADO]"

VARIABLES_SENSIBLES = (
    "LLM_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "M2_DOWNLOAD_SECRET",
    "MLFLOW_TRACKING_TOKEN",
    "AWS_SECRET_ACCESS_KEY",
)

_PATRON_NOMBRE_SECRETO = re.compile(
    r"(?i)\b(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|secret|token)"
    r"(['\"]?\s*[:=]\s*['\"]?)(?:bearer\s+)?[^\s,;'\"})]+"
)
_PATRON_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]+")
_PATRON_CLAVE = re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{8,}\b")

_REQUEST_ID: ContextVar[str | None] = ContextVar("m2_request_id", default=None)
_JOB_ID: ContextVar[str | None] = ContextVar("m2_job_id", default=None)


def redactar(texto: object) -> str:
    """Elimina PII y secretos de un texto antes de escribirlo en el log (AC3)."""
    resultado = _sanitizar(str(texto))
    for variable in VARIABLES_SENSIBLES:
        valor = os.environ.get(variable, "")
        if len(valor) >= 6:
            resultado = resultado.replace(valor, MARCADOR)
    resultado = _PATRON_NOMBRE_SECRETO.sub(rf"\1\2{MARCADOR}", resultado)
    resultado = _PATRON_BEARER.sub(f"Bearer {MARCADOR}", resultado)
    return _PATRON_CLAVE.sub(MARCADOR, resultado)[:LONGITUD_MAXIMA]


def request_id_actual() -> str | None:
    """Devuelve el `request_id` del contexto actual, si hay uno."""
    return _REQUEST_ID.get()


def job_id_actual() -> str | None:
    """Devuelve el `job_id` del contexto actual, si hay uno."""
    return _JOB_ID.get()


@contextmanager
def contexto_solicitud(
    *, request_id: str | None = None, job_id: str | None = None
) -> Iterator[None]:
    """Activa los ids de correlación en el ámbito actual y los restaura al salir."""
    token_request: Token[str | None] | None = (
        _REQUEST_ID.set(request_id) if request_id is not None else None
    )
    token_job: Token[str | None] | None = _JOB_ID.set(job_id) if job_id is not None else None
    try:
        yield
    finally:
        if token_job is not None:
            _JOB_ID.reset(token_job)
        if token_request is not None:
            _REQUEST_ID.reset(token_request)


class ContextoFilter(logging.Filter):
    """Inyecta `request_id` y `job_id` en cada registro del contexto activo (RF-2)."""

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _REQUEST_ID.get()
        job_id = _JOB_ID.get()
        if request_id is not None:
            record.request_id = request_id
        if job_id is not None:
            record.job_id = job_id
        return True


class JsonFormatter(logging.Formatter):
    """Serializa cada registro como una línea JSON (AC2), redactando su contenido."""

    def format(self, record: logging.LogRecord) -> str:
        datos: dict[str, object] = {
            "nivel": record.levelname,
            "modulo": record.name,
            "mensaje": redactar(record.getMessage()),
            "marca_tiempo": datetime.fromtimestamp(record.created, UTC).isoformat(),
        }
        if getattr(record, "request_id", None):
            datos["request_id"] = str(record.request_id)
        if getattr(record, "job_id", None):
            datos["job_id"] = str(record.job_id)
        if record.exc_info:
            datos["excepcion"] = redactar(self.formatException(record.exc_info))
        detalles = getattr(record, "datos", None)
        if isinstance(detalles, dict):
            datos["detalles"] = {clave: redactar(valor) for clave, valor in detalles.items()}
        return json.dumps(datos, ensure_ascii=False, sort_keys=True)


def configurar_logging() -> None:
    """Aplica la configuración central con el nivel indicado por `M2_LOG_LEVEL` (RNF-3)."""
    nivel = os.environ.get(VARIABLE_NIVEL, NIVEL_PREDETERMINADO).strip().upper()
    if nivel not in NIVELES:
        nivel = NIVEL_PREDETERMINADO
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonFormatter}},
            "filters": {"contexto": {"()": ContextoFilter}},
            "handlers": {
                "consola": {
                    "level": nivel,
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json",
                    "filters": ["contexto"],
                }
            },
            "loggers": {
                "m2_cad": {
                    "handlers": ["consola"],
                    "level": nivel,
                    # caplog y otras herramientas siguen viendo los registros.
                    "propagate": True,
                }
            },
        }
    )
