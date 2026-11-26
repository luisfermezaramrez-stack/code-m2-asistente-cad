"""Sesiones locales firmadas y control de acceso por usuario (HU-53).

Sin proveedor externo ni dependencias nuevas: la cookie se firma con HMAC-SHA256
y las claves se guardan como hashes PBKDF2-SHA256 definidos por entorno.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import suppress

from fastapi import HTTPException, Request, Response

COOKIE_NOMBRE = "m2_sesion"
ANONIMO = "anónimo"
ITERACIONES = 200_000

_USUARIO_RE = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_HASH_RE = re.compile(
    r"pbkdf2_sha256\$([1-9]\d{0,6})\$([A-Za-z0-9_-]{20,24})\$([A-Za-z0-9_-]{42,44})"
)
_SESION_RE = re.compile(r"v1\.([A-Za-z0-9_-]{1,86})\.([0-9]{1,12})\.([0-9a-f]{64})")


def _codificar(valor: bytes) -> str:
    return base64.urlsafe_b64encode(valor).decode("ascii").rstrip("=")


def _decodificar(valor: str) -> bytes:
    return base64.urlsafe_b64decode(valor + "=" * (-len(valor) % 4))


def _entero_env(nombre: str, predeterminado: int, minimo: int, maximo: int) -> int:
    valor = os.environ.get(nombre)
    if valor is None or not valor.strip():
        return predeterminado
    try:
        numero = int(valor)
    except ValueError as exc:
        raise RuntimeError(f"{nombre} debe ser un entero.") from exc
    if not minimo <= numero <= maximo:
        raise RuntimeError(f"{nombre} debe estar entre {minimo} y {maximo}.")
    return numero


def autenticacion_activa() -> bool:
    """La autenticación está activa por defecto; el modo local se pide explícitamente."""
    valor = os.environ.get("M2_AUTH_ENABLED", "1").strip().lower()
    return valor not in {"0", "false", "no", "off"}


def cookie_segura() -> bool:
    """La cookie exige HTTPS salvo que se active explícitamente HTTP local."""
    valor = os.environ.get("M2_AUTH_COOKIE_SECURE", "1").strip().lower()
    return valor not in {"0", "false", "no", "off"}


def _secreto() -> bytes:
    secreto = os.environ.get("M2_AUTH_SECRET", "").encode("utf-8")
    if len(secreto) < 32:
        raise RuntimeError(
            "Configure M2_AUTH_SECRET con un secreto aleatorio de al menos 32 bytes."
        )
    return secreto


def _ttl() -> int:
    return _entero_env("M2_AUTH_TTL_SECONDS", 86_400, 60, 2_592_000)


def hash_clave(clave: str) -> str:
    """Devuelve un hash PBKDF2-SHA256 con sal aleatoria, listo para M2_AUTH_USERS."""
    if not isinstance(clave, str) or not clave or len(clave) > 256:
        raise ValueError("La clave debe tener entre 1 y 256 caracteres.")
    sal = secrets.token_bytes(16)
    derivacion = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${_codificar(sal)}${_codificar(derivacion)}"


def verificar_clave(clave: str, guardado: str) -> bool:
    """Compara en tiempo constante sin revelar si el usuario existe."""
    coincidencia = _HASH_RE.fullmatch(guardado or "")
    if coincidencia is None:
        return False
    iteraciones, sal, esperado = coincidencia.groups()
    derivacion = hashlib.pbkdf2_hmac(
        "sha256",
        clave.encode("utf-8"),
        _decodificar(sal),
        int(iteraciones),
    )
    return hmac.compare_digest(derivacion, _decodificar(esperado))


def usuarios() -> dict[str, str]:
    """Lee el mapa usuario → hash desde el entorno; nunca desde el repositorio."""
    crudo = os.environ.get("M2_AUTH_USERS", "")
    if not crudo.strip():
        raise RuntimeError("Configure M2_AUTH_USERS con usuarios y hashes PBKDF2.")
    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError as exc:
        raise RuntimeError("M2_AUTH_USERS debe ser JSON válido.") from exc
    if not isinstance(datos, dict) or not datos:
        raise RuntimeError("M2_AUTH_USERS debe contener al menos un usuario.")
    for usuario, guardado in datos.items():
        if (
            not isinstance(usuario, str)
            or _USUARIO_RE.fullmatch(usuario) is None
            or not isinstance(guardado, str)
            or _HASH_RE.fullmatch(guardado) is None
        ):
            raise RuntimeError("M2_AUTH_USERS contiene un usuario o hash inválido.")
    return dict(datos)


@functools.cache
def _hash_ficticio() -> str:
    """Hash descartable: un usuario inexistente cuesta lo mismo que una clave errónea."""
    return hash_clave(secrets.token_urlsafe(16))


def verificar_usuario(usuario: str, clave: str) -> bool:
    """ACE1: credenciales inválidas contestan igual que un usuario inexistente.

    Con un usuario inexistente se deriva igual un PBKDF2 para que el tiempo de
    respuesta no revele qué usuarios existen.
    """
    if not isinstance(usuario, str) or _USUARIO_RE.fullmatch(usuario) is None:
        return False
    guardado = usuarios().get(usuario)
    if guardado is None:
        verificar_clave(clave, _hash_ficticio())
        return False
    return verificar_clave(clave, guardado)


def _firmar(mensaje: str, guardado: str) -> str:
    """HMAC del token ligado al hash vigente del usuario (revocación sin estado)."""
    material = f"{mensaje}\n{guardado}".encode("ascii")
    return hmac.new(_secreto(), material, hashlib.sha256).hexdigest()


def emitir_sesion(usuario: str, *, ahora: int | None = None) -> str:
    """Firma usuario y expiración; el token nunca incluye la clave.

    La firma incorpora el hash guardado del usuario: quitarlo de ``M2_AUTH_USERS`` o
    cambiar su clave invalida las sesiones ya emitidas.
    """
    if _USUARIO_RE.fullmatch(usuario) is None:
        raise ValueError("Nombre de usuario inválido.")
    instante = int(time.time()) if ahora is None else int(ahora)
    mensaje = f"v1.{_codificar(usuario.encode('utf-8'))}.{instante + _ttl()}"
    guardado = usuarios().get(usuario)
    if guardado is None:
        raise ValueError("Usuario desconocido.")
    return f"{mensaje}.{_firmar(mensaje, guardado)}"


def validar_sesion(token: str | None, *, ahora: int | None = None) -> str | None:
    """Devuelve el usuario o None; nunca lanza para un token manipulado."""
    if not token or len(token) > 512:
        return None
    coincidencia = _SESION_RE.fullmatch(token)
    if coincidencia is None:
        return None
    mensaje, firma_recibida = token.rsplit(".", 1)
    try:
        usuario = _decodificar(coincidencia.group(1)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if _USUARIO_RE.fullmatch(usuario) is None:
        return None
    # Un usuario retirado no tiene hash: su firma ya no puede coincidir.
    guardado = usuarios().get(usuario) or _hash_ficticio()
    if not hmac.compare_digest(firma_recibida, _firmar(mensaje, guardado)):
        return None
    instante = int(time.time()) if ahora is None else int(ahora)
    if instante >= int(coincidencia.group(2)):
        return None
    return usuario


def usuario_actual(request: Request) -> str:
    """Dependencia FastAPI: exige sesión salvo en el modo local explícito."""
    if not autenticacion_activa():
        return ANONIMO
    usuario = validar_sesion(request.cookies.get(COOKIE_NOMBRE))
    if usuario is None:
        raise HTTPException(
            401,
            "Inicia sesión para continuar.",
            headers={"WWW-Authenticate": 'Cookie realm="M2 CAD"'},
        )
    return usuario


def usuario_de_sesion(request: Request) -> str:
    """Usuario de la cookie válida o anónimo; nunca lanza (registro de rechazos)."""
    if not autenticacion_activa():
        return ANONIMO
    return validar_sesion(request.cookies.get(COOKIE_NOMBRE)) or ANONIMO


def validar_configuracion() -> None:
    """Falla al arrancar si la autenticación activa no puede funcionar (S7)."""
    if not autenticacion_activa():
        return
    _secreto()
    usuarios()
    _ttl()
    _limites_intentos()


def _limites_intentos() -> tuple[int, int]:
    return (
        _entero_env("M2_AUTH_MAX_INTENTOS", 5, 1, 1_000),
        _entero_env("M2_AUTH_VENTANA_INTENTOS_SEGUNDOS", 300, 1, 86_400),
    )


class IntentosAgotados(HTTPException):
    """429 tipado para el login; indica cuándo reintentar."""

    def __init__(self, espera: int) -> None:
        super().__init__(
            429,
            "Demasiados intentos fallidos. Vuelve a intentarlo más tarde.",
            headers={"Retry-After": str(espera)},
        )


FACTOR_LIMITE_POR_CLIENTE = 4


class LimiteIntentos:
    """Intentos fallidos de login en una ventana deslizante (S7).

    Cada intento se anota antes de derivar la clave, bajo un único lock, así las
    peticiones concurrentes no pasan todas el control. Se cuenta por cliente y
    usuario (``M2_AUTH_MAX_INTENTOS``) y por cliente (4 veces ese valor). Un acierto
    retira sólo su propia marca: entrar con otra cuenta no borra los fallos
    acumulados contra un usuario. El estado vive en el proceso (``--workers 1``).
    """

    def __init__(self, reloj=None) -> None:
        self._reloj = reloj or time.monotonic
        self._lock = threading.Lock()
        self._fallos: dict[str, deque[float]] = defaultdict(deque)

    def _vigentes(self, clave: str, ahora: float, ventana: int) -> deque[float]:
        fallos = self._fallos[clave]
        while fallos and ahora - fallos[0] >= ventana:
            fallos.popleft()
        return fallos

    def intentar(self, cliente: str, usuario: str) -> tuple[tuple[str, ...], float]:
        """Anota un intento o responde 429 si alguno de sus contadores está agotado."""
        maximo, ventana = _limites_intentos()
        claves = (f"par:{cliente}\n{usuario}", f"cliente:{cliente}")
        topes = (maximo, maximo * FACTOR_LIMITE_POR_CLIENTE)
        ahora = self._reloj()
        with self._lock:
            for clave, tope in zip(claves, topes, strict=True):
                fallos = self._vigentes(clave, ahora, ventana)
                if len(fallos) >= tope:
                    raise IntentosAgotados(max(1, math.ceil(ventana - (ahora - fallos[0]))))
            for clave in claves:
                self._fallos[clave].append(ahora)
        return claves, ahora

    def acertar(self, marca: tuple[tuple[str, ...], float]) -> None:
        """Retira la marca del intento exitoso; los demás fallos siguen contando."""
        claves, instante = marca
        with self._lock:
            for clave in claves:
                with suppress(ValueError):
                    self._fallos[clave].remove(instante)


def estado_sesion(request: Request) -> dict[str, bool | str | None]:
    """Estado público para la SPA; no filtra datos del token ni del secreto."""
    if not autenticacion_activa():
        return {"requerido": False, "autenticado": False, "usuario": None}
    usuario = validar_sesion(request.cookies.get(COOKIE_NOMBRE))
    return {"requerido": True, "autenticado": usuario is not None, "usuario": usuario}


NO_ENCONTRADA = "Solicitud desconocida o fuera de retención."


def garantizar_propietario(
    usuario: str, propietario: str | None, detalle: str = NO_ENCONTRADA
) -> None:
    """RF-4: 404 para no revelar la existencia de recursos ajenos.

    ``detalle`` es el mismo texto que da un recurso inexistente, así la respuesta
    no distingue «ajeno» de «no existe».
    """
    if not autenticacion_activa():
        return
    if not propietario or propietario != usuario:
        raise HTTPException(404, detalle)


def fijar_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NOMBRE,
        token,
        max_age=_ttl(),
        path="/",
        httponly=True,
        secure=cookie_segura(),
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


def borrar_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NOMBRE,
        path="/",
        httponly=True,
        secure=cookie_segura(),
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
