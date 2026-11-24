"""Tokens firmados y validación de UUID para descargas CAD (HU-36)."""

import hashlib
import hmac
import os
import re
import time
import uuid

from fastapi import HTTPException

_UUID_RE = re.compile(
    r"(?:[0-9a-f]{32}|"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"v1\.([0-9a-f]{32})\.([0-9]{1,12})\.([0-9a-f]{64})")


def validar_uuid(identificador: str) -> str:
    """Valida el formato UUID y devuelve sus 32 caracteres hexadecimales."""
    if not isinstance(identificador, str) or not _UUID_RE.fullmatch(identificador):
        raise HTTPException(422, "Identificador UUID inválido.")

    return uuid.UUID(identificador).hex


def _obtener_secreto() -> bytes:
    """Exige un secreto persistente; nunca utiliza claves predeterminadas."""
    secreto = os.environ.get("M2_DOWNLOAD_SECRET", "").encode("utf-8")

    if len(secreto) < 32:
        raise RuntimeError(
            "Configure M2_DOWNLOAD_SECRET con un secreto aleatorio de al menos 32 bytes."
        )

    return secreto


def _obtener_ttl() -> int:
    """Duración configurable entre 1 segundo y 30 días."""
    valor = os.environ.get("M2_DOWNLOAD_TTL_SECONDS", "3600")

    try:
        ttl = int(valor)
    except ValueError as exc:
        raise RuntimeError("M2_DOWNLOAD_TTL_SECONDS debe ser un entero.") from exc

    if not 1 <= ttl <= 2_592_000:
        raise RuntimeError("La expiración debe estar entre 1 y 2592000 segundos.")

    return ttl


def emitir_token(solicitud_id: str, *, ahora: int | None = None) -> str:
    """Genera un token HMAC-SHA256 vinculado al UUID y su expiración."""
    identificador = validar_uuid(solicitud_id)
    instante = int(time.time()) if ahora is None else ahora
    expiracion = instante + _obtener_ttl()

    mensaje = f"v1.{identificador}.{expiracion}"
    firma = hmac.new(
        _obtener_secreto(),
        mensaje.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    return f"{mensaje}.{firma}"


def exigir_token(
    solicitud_id: str,
    token: str | None,
    *,
    ahora: int | None = None,
) -> None:
    """Autoriza la solicitud o responde HTTP 403, 410 o 422."""
    identificador = validar_uuid(solicitud_id)

    if not token or len(token) > 256:
        raise HTTPException(403, "Token de descarga inválido.")

    coincidencia = _TOKEN_RE.fullmatch(token)

    if coincidencia is None or coincidencia.group(1) != identificador:
        raise HTTPException(403, "Token de descarga inválido.")

    mensaje, firma_recibida = token.rsplit(".", 1)

    firma_esperada = hmac.new(
        _obtener_secreto(),
        mensaje.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(firma_recibida, firma_esperada):
        raise HTTPException(403, "Token de descarga inválido.")

    expiracion = int(coincidencia.group(2))
    instante = int(time.time()) if ahora is None else ahora

    if instante >= expiracion:
        raise HTTPException(410, "El artefacto ha expirado.")
