"""API REST para la generación preliminar de componentes CAD (HU-06)."""

import ast
import asyncio
import csv
import logging
import os
import tempfile
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from m2_cad import declinacion, seguimiento, versiones
from m2_cad.autenticacion import (
    ANONIMO,
    LimiteIntentos,
    autenticacion_activa,
    borrar_cookie,
    emitir_sesion,
    estado_sesion,
    fijar_cookie,
    garantizar_propietario,
    usuario_actual,
    usuario_de_sesion,
    validar_configuracion,
    verificar_usuario,
)
from m2_cad.cola_trabajos import ColaTrabajos, TrabajoPersistido
from m2_cad.contratos import EstadoTrabajo
from m2_cad.control import ControlGeneracion, SolicitudDeclinada
from m2_cad.control_uso import ControlUso, ErrorControlUso, RegistroIdempotencia
from m2_cad.observabilidad import (
    configurar_logging,
    contexto_solicitud,
    job_id_actual,
    request_id_actual,
)
from m2_cad.registro import RUTA_DEFAULT, SIN_TRADUCCION, registrar
from m2_cad.retencion_salidas import depurar_outputs, leer_politica
from m2_cad.seguridad_descargas import emitir_token, exigir_token, validar_uuid
from m2_cad.trabajos import GestorTrabajos, RespuestaSSE, Trabajo
from m2_cad.web import configurar_web

Procesador = Callable[[str, dict | None], dict[str, str]]
ProcesadorSSE = Callable[[str, ControlGeneracion, dict | None], dict[str, str]]


async def _limpieza_periodica(politica) -> None:
    """Limpieza no invasiva: no se ejecuta si existe un trabajo en proceso."""
    while True:
        try:
            if not (gestor_trabajos.hay_trabajos_activos() or cola_trabajos.hay_trabajos_activos()):
                await asyncio.to_thread(depurar_outputs, Path("outputs"), dias=politica.dias)
        except Exception:
            logger.exception("No se pudo aplicar la política de retención.")
        await asyncio.sleep(politica.intervalo_segundos)


@asynccontextmanager
async def _ciclo_aplicacion(_: FastAPI):
    """Abre la cola al arrancar y detiene la retención al cerrar (HU-45, RF-4).

    Con autenticación activa, una configuración inválida impide arrancar (HU-53)
    en lugar de responder 500 en cada inicio de sesión.
    """
    validar_configuracion()
    cola_trabajos.abrir()
    politica = leer_politica()
    tarea = asyncio.create_task(_limpieza_periodica(politica)) if politica else None
    try:
        yield
    finally:
        if tarea is not None:
            tarea.cancel()
            with suppress(asyncio.CancelledError):
                await tarea


logger = logging.getLogger(__name__)
configurar_logging()  # RF-1: configuración central desde la importación del módulo.

VERSION_API = "1.0.0"
PREFIJO_V1 = "/v1"
# RFC 9745: `Deprecation` es una fecha HTTP estructurada (@epoch), no un booleano.
# 2026-11-25T00:00:00Z, fecha de publicación de v1 (SPEC-032).
DEPRECACION_RUTAS_PLANAS = "@1795564800"
# Plazo de convivencia de 90 días; configurable si se retrasa el despliegue.
SUNSET_RUTAS_PLANAS = os.getenv("M2_SUNSET_RUTAS_PLANAS", "Tue, 23 Feb 2027 00:00:00 GMT")

app = FastAPI(
    title="M2 CAD Assistant API",
    lifespan=_ciclo_aplicacion,
    version=VERSION_API,
    description="Servicio de generación preliminar de componentes CAD.",
)
gestor_trabajos = GestorTrabajos()
cola_trabajos = ColaTrabajos()
control_uso = ControlUso()
router = APIRouter(prefix=PREFIJO_V1)


class SolicitudGenerar(BaseModel):
    """Define y valida la entrada del servicio CAD."""

    texto: str = Field(
        min_length=1,
        max_length=1000,
        description="Descripción técnica de la pieza en español.",
    )

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        """Rechaza solicitudes sin contenido significativo."""
        if not valor.strip():
            raise ValueError("La descripción no puede estar vacía.")

        return valor.strip()


limite_login = LimiteIntentos()


def obtener_limite_login() -> LimiteIntentos:
    """Límite de intentos de login del proceso; sustituible en pruebas (HU-53)."""
    return limite_login


class Credenciales(BaseModel):
    """Credenciales HU-53; la clave nunca se registra ni se devuelve."""

    usuario: str = Field(min_length=1, max_length=64)
    clave: str = Field(min_length=1, max_length=256)


class RespuestaUso(BaseModel):
    """Gasto acumulado del día y topes vigentes (HU-32, RF-5)."""

    fecha: date
    costo_usd: float
    moneda: str
    generaciones: int
    presupuesto_diario_usd: float
    limite_solicitudes_ventana: int
    ventana_segundos: int


class SolicitudEdicion(BaseModel):
    """Instrucción de cambio en español sobre la pieza previa (HU-35, RF-1)."""

    instruccion: str = Field(
        min_length=1,
        max_length=1000,
        description="Cambio pedido en español, aplicado sobre el programa vigente.",
    )

    @field_validator("instruccion")
    @classmethod
    def validar_instruccion(cls, valor: str) -> str:
        """Rechaza instrucciones sin contenido significativo."""
        if not valor.strip():
            raise ValueError("La instrucción no puede estar vacía.")
        return valor.strip()


class VersionPieza(BaseModel):
    """Una versión de la pieza con su programa y sus artefactos (HU-35, AC3)."""

    version: int
    hora: str
    programa: dict[str, Any]
    artefactos: list[str]
    diff: list[dict[str, Any]] = []
    prompt: str
    prompt_hash: str


class RespuestaVersiones(BaseModel):
    """Historial de versiones de una solicitud, en orden ascendente (HU-35, AC3)."""

    solicitud_id: str
    versiones: list[VersionPieza]


class RespuestaEdicion(BaseModel):
    """Nueva versión verificada de la pieza, con el diff del programa (HU-35, AC1)."""

    solicitud_id: str
    version: int
    prompt: str
    programa: dict[str, Any]
    diff: list[dict[str, Any]]
    step: str
    glb: str
    bom_csv: str
    aviso: str
    volumen_mm3: str
    caja_mm: str
    tiempo_generacion_s: str
    tiempo_construccion_s: str


@router.get("/health")
def health() -> dict[str, str]:
    """Comprueba que el proceso de la API está disponible (AC4: sin credenciales)."""
    return {"status": "ok"}


@router.post("/auth/login")
def iniciar_sesion(
    credenciales: Credenciales,
    request: Request,
    response: Response,
    limite: Annotated[LimiteIntentos, Depends(obtener_limite_login)],
) -> dict[str, bool | str]:
    """AC1: emite una cookie firmada sólo para credenciales válidas.

    Los intentos se anotan y limitan (429 con ``Retry-After``) antes de derivar la
    clave, para frenar la fuerza bruta sin gastar CPU en PBKDF2.
    """
    if not autenticacion_activa():
        raise HTTPException(404, "La autenticación no está activada.")
    cliente = request.client.host if request.client else "desconocido"
    marca = limite.intentar(cliente, credenciales.usuario)
    if not verificar_usuario(credenciales.usuario, credenciales.clave):
        raise HTTPException(401, "Usuario o clave incorrectos.")
    limite.acertar(marca)
    fijar_cookie(response, emitir_sesion(credenciales.usuario))
    return {"autenticado": True, "usuario": credenciales.usuario}


@router.post("/auth/logout")
def cerrar_sesion(response: Response) -> dict[str, bool]:
    """Elimina la cookie de sesión; el cliente debe volver a autenticarse."""
    borrar_cookie(response)
    return {"autenticado": False}


@router.get("/auth/me")
def estado_sesion_actual(request: Request) -> dict[str, bool | str | None]:
    """Expone a la SPA si la sesión es necesaria y cuál es el usuario activo."""
    return estado_sesion(request)


def procesador_no_disponible(texto: str) -> dict[str, str]:
    """Informa que falta la API key del modelo (HU-14, AC3)."""
    raise FalloHTTP(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "El modelo no está configurado: falta DEEPSEEK_API_KEY.",
        "ModeloNoDisponible",
    )


class FalloHTTP(HTTPException):
    """Fallo del pipeline con la clase de la excepción para el seguimiento (AC3)."""

    def __init__(self, status_code: int, detail: str, clase: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.clase = clase


class DeclinacionSolicitud(HTTPException):
    """Declinación con motivo legible, causa y programa, sin cambiar el 422 de HU-05.

    HU-26: `causa` es la etiqueta del catálogo que llega al registro y al seguimiento;
    `motivo` sigue siendo el texto que lee el usuario (RF-4, AC3).
    """

    def __init__(
        self,
        motivo: str,
        programa_json: Path | None = None,
        *,
        causa: declinacion.Causa,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Pieza declinada: {motivo}",
            headers={"X-Resultado-Tipo": "declinacion_explicita"},
        )
        self.motivo = motivo
        self.causa = causa
        self.programa_json = programa_json


def _modelo_configurado() -> bool:
    """Hay modelo: DeepSeek con key (HU-14) o un servidor propio en LLM_BASE_URL."""
    return any(
        os.environ.get(variable) for variable in ("LLM_BASE_URL", "LLM_API_KEY", "DEEPSEEK_API_KEY")
    )


def _registro_disponible() -> bool:
    """Comprueba acceso al registro sin crearlo ni alterar su contenido."""
    ruta = Path(obtener_ruta_registro())
    try:
        if ruta.exists() and not ruta.is_file():
            return False
        # El temporal verifica escritura efectiva, incluso si el CSV aún no existe.
        with tempfile.TemporaryFile(dir=ruta.parent) as temporal:
            temporal.write(b"ready")
        if ruta.exists():
            with ruta.open("rb") as archivo:
                archivo.read(1)
    except OSError:
        return False
    return True


@router.get("/ready")
def ready() -> JSONResponse:
    """Disponibilidad operativa local; /health conserva el contrato de vida."""
    dependencias = {
        "modelo": "ok" if _modelo_configurado() else "no_disponible",
        "registro": "ok" if _registro_disponible() else "no_disponible",
    }
    disponible = all(estado == "ok" for estado in dependencias.values())
    return JSONResponse(
        status_code=200 if disponible else 503,
        content={
            "status": "ok" if disponible else "no_disponible",
            "dependencias": dependencias,
        },
    )


def _preparar_medicion(pipeline, medido: dict, *, prompt=None) -> Callable[[dict], None]:
    """Anota modelo, versión y prompt vigente, y devuelve el receptor del `usage` (HU-16).

    HU-33/AC1: la etiqueta y el hash del prompt cargado viajan con la medición para que
    queden en el registro y en la corrida de MLflow de cada solicitud.
    """
    cargado = prompt if prompt is not None else pipeline.PROMPT_VIGENTE
    medido.update(
        modelo=pipeline.llm.planner_model(),
        version_modelo=seguimiento.version_modelo(),
        temperatura=pipeline.TEMPERATURA_LLM,
        prompt=cargado.etiqueta,
        prompt_hash=cargado.sha256,
    )

    def medir_uso(uso: dict) -> None:
        # En la ruta de error sólo llegan métricas llm_*: no inventar tokens ni costo.
        if "prompt_tokens" in uso or "completion_tokens" in uso:
            medido["tokens_entrada"] = int(uso.get("prompt_tokens") or 0)
            medido["tokens_salida"] = int(uso.get("completion_tokens") or 0)
        for clave in ("llm_reintentos", "llm_cache_hit", "llm_cache_miss"):
            if clave in uso:
                medido[clave] = int(uso.get(clave) or 0)

    return medir_uso


def _anotar_detalle(exc: Exception) -> None:
    """Conserva el detalle técnico de una declinación para diagnóstico (RF-5).

    Se registra en el log estructurado —redactado por HU-24— y nunca se muestra como
    mensaje ni se escribe en el registro consultable: el usuario no debe leer jerga.
    """
    detalle = getattr(exc, "detalle", None)
    logger.warning(
        "declinación con causa %s; detalle técnico: %s",
        getattr(exc, "causa", None),
        detalle or "sin detalle",
    )


def procesar_con_pipeline(texto: str, medicion: dict | None = None) -> dict[str, str]:
    """Genera la pieza con el pipeline CAD (HU-04) y traduce sus errores a HTTP.

    Deja en `medicion` los datos que registra el seguimiento (HU-16, AC2/AC3).
    """
    medido = medicion if medicion is not None else {}
    if not _modelo_configurado():
        return procesador_no_disponible(texto)

    # Importación diferida: el núcleo CAD (cadquery/OCP) solo se carga al usarlo.
    from m2_cad import pipeline

    medir_uso = _preparar_medicion(pipeline, medido)
    try:
        resultado = pipeline.generar_pieza(texto, medir_uso=medir_uso)
    except pipeline.PiezaDeclinada as exc:
        medido.update(
            familia="desconocida", artefactos=[exc.programa_json], causa=str(exc.causa)
        )
        _anotar_detalle(exc)
        raise DeclinacionSolicitud(exc.motivo, exc.programa_json, causa=exc.causa) from exc
    except (pipeline.ErrorGeneracion, pipeline.ErrorVerificacion) as exc:
        medido.update(familia="desconocida", causa=str(exc.causa))
        _anotar_detalle(exc)
        raise FalloHTTP(
            status.HTTP_422_UNPROCESSABLE_CONTENT, exc.mensaje, type(exc).__name__
        ) from exc
    except pipeline.ModeloNoDisponible as exc:
        medido["familia"] = "desconocida"
        raise FalloHTTP(
            status.HTTP_503_SERVICE_UNAVAILABLE, str(exc), "ModeloNoDisponible"
        ) from exc

    medido.update(
        familia=resultado.familia,
        artefactos=[resultado.programa_json, resultado.step, resultado.glb, resultado.bom_csv],
        # HU-35: el programa viaja en `medido` para registrar la versión 1 sin releer disco.
        programa=resultado.programa,
    )
    return resultado.a_respuesta()


def obtener_procesador() -> Procesador:
    """Proporciona el procesador CAD utilizado por la API."""
    return procesar_con_pipeline


def procesar_con_progreso(
    texto: str, control: ControlGeneracion, medicion: dict | None = None
) -> dict[str, str]:
    """Adaptador SSE: distingue declinaciones sin inferirlas de un código 422.

    Deja en `medicion` los mismos datos de seguimiento que la ruta JSON (HU-16).
    """
    medido = medicion if medicion is not None else {}
    if not _modelo_configurado():
        control.informar("validando")
        return procesador_no_disponible(texto)

    from m2_cad import pipeline

    medir_uso = _preparar_medicion(pipeline, medido)
    try:
        resultado = pipeline.generar_pieza(texto, control=control, medir_uso=medir_uso)
    except pipeline.PiezaDeclinada as exc:
        medido.update(
            familia="desconocida", artefactos=[exc.programa_json], causa=str(exc.causa)
        )
        _anotar_detalle(exc)
        raise SolicitudDeclinada(exc.motivo) from exc
    except (pipeline.ErrorGeneracion, pipeline.ErrorVerificacion) as exc:
        medido.update(familia="desconocida", causa=str(exc.causa))
        _anotar_detalle(exc)
        raise FalloHTTP(422, exc.mensaje, type(exc).__name__) from exc
    except pipeline.ModeloNoDisponible as exc:
        medido["familia"] = "desconocida"
        raise FalloHTTP(
            503, "El servicio de generación no está disponible.", "ModeloNoDisponible"
        ) from exc

    medido.update(
        familia=resultado.familia,
        artefactos=[resultado.programa_json, resultado.step, resultado.glb, resultado.bom_csv],
        # HU-35: el programa viaja en `medido` para registrar la versión 1 sin releer disco.
        programa=resultado.programa,
    )
    return resultado.a_respuesta()


def obtener_procesador_sse() -> ProcesadorSSE:
    return procesar_con_progreso


def obtener_gestor_trabajos() -> GestorTrabajos:
    return gestor_trabajos


def obtener_cola_trabajos() -> ColaTrabajos:
    """Cola persistente de SSE; sustituible en pruebas (HU-45)."""
    return cola_trabajos


def _trabajo(
    solicitud_id: str, gestor: GestorTrabajos, cola: ColaTrabajos
) -> Trabajo | TrabajoPersistido:
    """Trabajo encolado (HU-45) o ejecutado en proceso, con su dueño (HU-53)."""
    try:
        return cola.obtener(solicitud_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
    return gestor.obtener(solicitud_id)


def _estado_trabajo(solicitud_id: str, gestor: GestorTrabajos, cola: ColaTrabajos) -> dict:
    """Estado público de un trabajo encolado (HU-45) o ejecutado en proceso."""
    return _trabajo(solicitud_id, gestor, cola).estado()


def obtener_control_uso() -> ControlUso:
    """Control de topes, presupuesto e idempotencia (HU-32); sustituible en pruebas."""
    return control_uso


def _sesion(request: Request, usuario: str = ANONIMO) -> str:
    """Identidad para topes e idempotencia (HU-32).

    Con autenticación activa es el usuario (HU-53): la IP o ``X-Session-ID`` se
    comparten detrás de un NAT o proxy y cruzarían repeticiones entre usuarios.
    """
    if autenticacion_activa():
        return f"usuario:{usuario}"
    cabecera = (request.headers.get("X-Session-ID") or "").strip()
    if cabecera:
        return cabecera[:128]
    cliente = request.client.host if request.client else None
    return cliente or "anonimo"


def _clave_idempotencia(valor: str | None) -> str | None:
    """Normaliza la cabecera; una clave vacía equivale a no enviarla."""
    if valor is None:
        return None
    return valor.strip() or None


def _respuesta_repetida(
    registro: RegistroIdempotencia,
    gestor: GestorTrabajos,
    cola: ColaTrabajos,
    response: Response,
) -> dict[str, str] | JSONResponse:
    """Sirve la generación original sin crear otro trabajo ni sumar costo (AC2)."""
    cabeceras = {
        "Idempotent-Replay": "true",
        "X-Solicitud-ID": registro.solicitud_id,
    }
    response.headers.update(cabeceras)
    if registro.respuesta is not None:
        response.headers.update(registro.cabeceras)
        return registro.respuesta
    estado = registro.estado_final or _estado_trabajo(registro.solicitud_id, gestor, cola)
    return JSONResponse(estado, headers=cabeceras)


def obtener_configuracion_seguimiento() -> seguimiento.Configuracion:
    """Configuración de MLflow de esta solicitud (HU-16); las pruebas la sustituyen."""
    return seguimiento.Configuracion.desde_entorno()


def obtener_ruta_registro() -> Path:
    """Proporciona la ruta del CSV de registro (HU-06, AC3/AC4)."""
    return RUTA_DEFAULT


def _identificador(request: Request) -> str:
    """UUID de correlación JSON; nunca incorpora texto arbitrario en rutas."""
    try:
        return uuid.UUID(request.headers.get("X-Request-ID", "")).hex
    except ValueError:
        return uuid.uuid4().hex


def _cabeceras_registro(request: Request, identificador: str) -> dict[str, str]:
    return {
        "X-Registro-ID": identificador,
        "X-Registro-URL": str(request.url_for("consultar_registro", identificador=identificador)),
    }


def _leer_registro(identificador: str) -> dict[str, str]:
    """Devuelve la fila existente sin escribir ni duplicar el registro (HU-07 AC3)."""
    identificador = validar_uuid(identificador)
    ruta = obtener_ruta_registro()
    if ruta.exists():
        with ruta.open(encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                if fila["id"] == identificador:
                    return fila
    raise HTTPException(404, "Registro no encontrado.")


@router.get("/registros/{identificador}")
def consultar_registro(
    identificador: str,
    usuario: Annotated[str, Depends(usuario_actual)],
) -> dict[str, str]:
    """Consulta una fila propia, sin revelar la de otros usuarios (HU-53, AC2)."""
    fila = _leer_registro(identificador)
    garantizar_propietario(usuario, fila.get("usuario"), "Registro no encontrado.")
    return fila


@router.get("/registros/{identificador}/step")
def descargar_step(
    identificador: str,
    request: Request,
    usuario: Annotated[str, Depends(usuario_actual)],
) -> FileResponse:
    """Enlaza el STEP propio del registro persistente, incluso tras reiniciar."""
    exigir_token(identificador, request.headers.get("X-Download-Token"))
    fila = _leer_registro(identificador)
    garantizar_propietario(usuario, fila.get("usuario"), "Registro no encontrado.")
    try:
        resultado = ast.literal_eval(fila["resultado"])
        ruta = Path(resultado["step"]).resolve()
        if (
            not ruta.is_relative_to(obtener_directorio_salidas())
            or ruta.suffix.lower() != ".step"
            or not ruta.is_file()
        ):
            raise ValueError("STEP no disponible")
    except (ValueError, SyntaxError, KeyError, TypeError) as exc:
        raise HTTPException(404, "STEP no disponible.") from exc
    return FileResponse(
        ruta,
        filename=ruta.name,
        media_type="application/step",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.exception_handler(RequestValidationError)
async def registrar_entrada_invalida(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Registra una entrada rechazada una vez, sin arrancar pipeline ni corrida MLflow."""
    respuesta = await request_validation_exception_handler(request, exc)
    if request.method == "POST" and request.url.path == f"{PREFIJO_V1}/generar":
        usuario = usuario_de_sesion(request)
        if autenticacion_activa() and usuario == ANONIMO:
            # Un JSON mal formado falla antes de resolver la sesión: sin este corte,
            # un anónimo escribiría filas en el registro (HU-53, AC1).
            return JSONResponse(
                {"detail": "Inicia sesión para continuar."},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": 'Cookie realm="M2 CAD"'},
            )
        identificador = _identificador(request)
        with contexto_solicitud(request_id=identificador):
            logger.warning("entrada inválida rechazada en POST /generar")
        cuerpo = exc.body if isinstance(exc.body, dict) else {}
        registrar(
            texto=cuerpo.get("texto", "entrada inválida"),
            traduccion=SIN_TRADUCCION,
            resultado=None,
            latencia_ms=0,
            error="Entrada inválida",
            version=seguimiento.version_modelo(),
            ruta=obtener_ruta_registro(),
            identificador=identificador,
            usuario=usuario,
        )
        respuesta.headers.update(_cabeceras_registro(request, identificador))
    return respuesta


def _clasificar(exc: HTTPException) -> tuple[str, str | None, str | None]:
    """Estado, motivo de declinación y clase de error de la corrida (AC3)."""
    if isinstance(exc, DeclinacionSolicitud):
        return "declinada", exc.motivo, None
    return "error", None, getattr(exc, "clase", type(exc).__name__)


def _costo_medido(medido: dict, precio_entrada: float, precio_salida: float) -> float | None:
    """Costo de una medición; sin usage no hay costo (0.0 distorsionaría MLflow)."""
    tokens_entrada = medido.get("tokens_entrada")
    tokens_salida = medido.get("tokens_salida")
    if tokens_entrada is None and tokens_salida is None:
        return None
    return seguimiento.costo_usd(
        tokens_entrada,
        tokens_salida,
        precio_entrada=precio_entrada,
        precio_salida=precio_salida,
    )


def _conciliar_gasto_cola(cola: ColaTrabajos, control: ControlUso) -> None:
    """Suma una sola vez el costo de los trabajos que terminó el worker (HU-32 × HU-45).

    El worker corre en otro proceso y no ve el ``ControlUso`` de la API: su medición
    queda en la cola y se contabiliza aquí antes de reservar y al consultar ``/v1/uso``.
    """
    defecto = seguimiento.Configuracion(activo=False)
    for pendiente in cola.tomar_gastos_pendientes():
        configuracion = pendiente["configuracion"]
        costo = _costo_medido(
            pendiente["medicion"],
            configuracion.get("precio_entrada", defecto.precio_entrada),
            configuracion.get("precio_salida", defecto.precio_salida),
        )
        if costo is not None:
            control.registrar_gasto(costo, dia=pendiente["dia"])


def medir_solicitud(
    corrida: seguimiento.Corrida,
    medido: dict,
    configuracion: seguimiento.Configuracion,
    *,
    estado: str,
    latencia_ms: float,
    motivo_declinacion: str | None = None,
    error: str | None = None,
    control_uso: ControlUso | None = None,
    params_extra: dict[str, object] | None = None,
) -> None:
    """Registra params, métricas, tags y artefactos, y cierra la corrida (AC2/AC3)."""
    params: dict[str, object] = {
        "modelo": medido.get("modelo"),
        "version_modelo": medido.get("version_modelo"),
        "familia": medido.get("familia"),
        "temperatura": medido.get("temperatura"),
        "prompt": medido.get("prompt"),
        "prompt_hash": medido.get("prompt_hash"),
    }
    params.update(params_extra or {})
    corrida.registrar_params(**params)
    tokens_entrada = medido.get("tokens_entrada")
    tokens_salida = medido.get("tokens_salida")
    costo_usd = _costo_medido(medido, configuracion.precio_entrada, configuracion.precio_salida)
    if costo_usd is not None and control_uso is not None:
        control_uso.registrar_gasto(costo_usd)
    corrida.registrar_metricas(
        latencia_ms=latencia_ms,
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
        costo_usd=costo_usd,
        verificacion_ok=1 if estado == "entregada" else 0,
        llm_reintentos=medido.get("llm_reintentos"),
        llm_cache_hit=medido.get("llm_cache_hit"),
        llm_cache_miss=medido.get("llm_cache_miss"),
    )
    corrida.registrar_artefactos(*(medido.get("artefactos") or []))
    modelo = medido.get("modelo")
    version_modelo = medido.get("version_modelo")
    if corrida.id and modelo and version_modelo:
        referencia = seguimiento.registrar_version_modelo(
            nombre=f"m2-cad-{modelo}",
            version=str(version_modelo),
            corrida_id=corrida.id,
            fuente=f"runs:/{corrida.id}",
            configuracion=configuracion,
            descripcion=f"Configuración servida en /generar: {modelo}",
        )
        corrida.registrar_tags(modelo_registrado=referencia)
    corrida.finalizar(
        estado=estado,
        motivo_declinacion=motivo_declinacion,
        causa_declinacion=medido.get("causa") or declinacion.NINGUNA,
        error=error,
    )
    # RF-3/AC1: el cierre del seguimiento se registra aquí, fuera de la medición
    # de sobrecarga de `seguimiento.Corrida.finalizar` (AC6 de HU-16).
    logger.info("seguimiento: cerrando corrida (%s)", estado)


_ESTADOS_CORRIDA_SSE = {
    "verificado": "entregada",
    "declinado": "declinada",
    "cancelado": "cancelada",
}


def _usa_cola_persistente() -> bool:
    """El despliegue usa cola/worker; las pruebas heredadas pueden desactivarla."""
    valor = os.environ.get("M2_COLA_HABILITADA", "1").strip().lower()
    return valor not in {"0", "false", "no", "off"}


def _acepta_sse(request: Request) -> bool:
    tipos = [tipo.split(";")[0].strip() for tipo in request.headers.get("accept", "").split(",")]
    return "text/event-stream" in tipos


def _generar_sse(
    solicitud: SolicitudGenerar,
    request: Request,
    procesador_sse: ProcesadorSSE,
    gestor: GestorTrabajos,
    cola: ColaTrabajos,
    configuracion: seguimiento.Configuracion,
    inicio: float,
    request_id: str,
    control_uso: ControlUso,
    al_terminal: Callable[[dict], None] | None = None,
    al_crear: Callable[[str], None] | None = None,
    usuario: str = ANONIMO,
) -> RespuestaSSE:
    """Ruta SSE: registro CSV y corrida MLflow al alcanzar el estado terminal (HU-15/16).

    La corrida se abre y se cierra en el hilo del trabajo, porque MLflow guarda la
    corrida activa por hilo.
    """
    ruta_registro = obtener_ruta_registro()
    medido: dict[str, object] = {}

    def procesar(texto: str, control: ControlGeneracion) -> dict[str, str]:
        return procesador_sse(texto, control, medido)

    def registrar_terminal(terminal: dict) -> None:
        latencia_ms = (time.perf_counter() - inicio) * 1000
        registrar(
            texto=solicitud.texto,
            traduccion=SIN_TRADUCCION,
            resultado=terminal.get("resultado"),
            latencia_ms=latencia_ms,
            error=terminal.get("motivo"),
            version=seguimiento.version_modelo(),
            ruta=ruta_registro,
            identificador=terminal["solicitud_id"],
            usuario=usuario,
            causa=medido.get("causa"),
            prompt=medido.get("prompt"),
            prompt_hash=medido.get("prompt_hash"),
        )
        estado = _ESTADOS_CORRIDA_SSE.get(terminal["estado"], "error")
        solicitud_id = terminal["solicitud_id"]
        if estado == "entregada":
            # HU-35: también una entrega SSE deja su versión 1 en el histórico.
            _registrar_version_inicial(solicitud_id, usuario, medido)
        corrida = seguimiento.iniciar_corrida(
            configuracion.experimento_generacion,
            nombre=solicitud_id,
            tags={
                "solicitud_id": solicitud_id,
                "request_id": request_id_actual() or solicitud_id,
                "job_id": job_id_actual() or solicitud_id,
                "transporte": "sse",
                "usuario": usuario,
            },
            configuracion=configuracion,
        )
        medir_solicitud(
            corrida,
            medido,
            configuracion,
            estado=estado,
            latencia_ms=latencia_ms,
            motivo_declinacion=terminal.get("motivo") if estado == "declinada" else None,
            error=f"HTTP {terminal.get('codigo_http', 500)}" if estado == "error" else None,
            control_uso=control_uso,
        )
        if al_terminal is not None:
            al_terminal(terminal)
        logger.info("generación terminada en %s", estado)

    if _usa_cola_persistente() and procesador_sse is procesar_con_progreso:
        # Despliegue: la API sólo encola; el worker ejecuta y registra (HU-45, AC3).
        trabajo = cola.encolar(
            solicitud.texto,
            request_id=request_id,
            configuracion=asdict(configuracion),
            ruta_registro=obtener_ruta_registro(),
            usuario=usuario,
        )
    else:
        # Compatibilidad con la batería SSE heredada que inyecta su propio procesador.
        trabajo = gestor.crear(solicitud.texto, procesar, registrar_terminal, usuario)
    if al_crear is not None:
        al_crear(trabajo.id)
    with contexto_solicitud(job_id=trabajo.id):
        logger.info("trabajo SSE creado")
    respuesta = RespuestaSSE(trabajo, request)
    respuesta.headers.update(_cabeceras_registro(request, trabajo.id))
    respuesta.headers["X-Download-Token"] = emitir_token(trabajo.id)
    respuesta.headers["Cache-Control"] = "no-store, no-transform"
    return respuesta


def _generar_json(
    solicitud: SolicitudGenerar,
    request: Request,
    response: Response,
    procesador: Procesador,
    configuracion: seguimiento.Configuracion,
    solicitud_id: str,
    inicio: float,
    control_uso: ControlUso,
    usuario: str = ANONIMO,
) -> dict[str, str]:
    """Ruta JSON: registro y corrida MLflow con el contexto de la solicitud activo."""
    cabeceras = _cabeceras_registro(request, solicitud_id)
    medido: dict[str, object] = {}
    corrida = seguimiento.iniciar_corrida(
        configuracion.experimento_generacion,
        nombre=solicitud_id,
        tags={"solicitud_id": solicitud_id, "request_id": solicitud_id, "usuario": usuario},
        configuracion=configuracion,
    )
    try:
        respuesta = procesador(solicitud.texto, medido)
    except HTTPException as exc:
        latencia_ms = (time.perf_counter() - inicio) * 1000
        estado, motivo, error = _clasificar(exc)
        registrar(
            texto=solicitud.texto,
            traduccion=SIN_TRADUCCION,
            resultado=None,
            latencia_ms=latencia_ms,
            error=str(exc.detail),
            version=seguimiento.version_modelo(),
            ruta=obtener_ruta_registro(),
            identificador=solicitud_id,
            usuario=usuario,
            causa=medido.get("causa"),
            prompt=medido.get("prompt"),
            prompt_hash=medido.get("prompt_hash"),
        )
        medir_solicitud(
            corrida,
            medido,
            configuracion,
            estado=estado,
            latencia_ms=latencia_ms,
            motivo_declinacion=motivo,
            error=error,
            control_uso=control_uso,
        )
        logger.warning("generación terminada en %s", estado)
        exc.headers = {**(exc.headers or {}), **cabeceras}
        raise
    except BaseException as exc:
        # Un fallo no previsto también cierra la corrida (AC3): MLflow guarda la
        # corrida activa por hilo y una en RUNNING bloquearía las siguientes.
        latencia_ms = (time.perf_counter() - inicio) * 1000
        registrar(
            texto=solicitud.texto,
            traduccion=SIN_TRADUCCION,
            resultado=None,
            latencia_ms=latencia_ms,
            error=type(exc).__name__,
            version=seguimiento.version_modelo(),
            ruta=obtener_ruta_registro(),
            identificador=solicitud_id,
            usuario=usuario,
            prompt=medido.get("prompt"),
            prompt_hash=medido.get("prompt_hash"),
        )
        medir_solicitud(
            corrida,
            medido,
            configuracion,
            estado="error",
            latencia_ms=latencia_ms,
            error=type(exc).__name__,
            control_uso=control_uso,
        )
        logger.warning("generación terminada en error (%s)", type(exc).__name__)
        if isinstance(exc, Exception):
            raise HTTPException(500, "Fallo técnico del pipeline.", headers=cabeceras) from exc
        raise

    latencia_ms = (time.perf_counter() - inicio) * 1000
    # HU-35: la generación inicial deja su versión 1 en el histórico.
    _registrar_version_inicial(solicitud_id, usuario, medido)
    registrar(
        texto=solicitud.texto,
        traduccion=SIN_TRADUCCION,
        resultado=respuesta,
        latencia_ms=latencia_ms,
        version=seguimiento.version_modelo(),
        ruta=obtener_ruta_registro(),
        identificador=solicitud_id,
        usuario=usuario,
        prompt=medido.get("prompt"),
        prompt_hash=medido.get("prompt_hash"),
    )
    medir_solicitud(
        corrida,
        medido,
        configuracion,
        estado="entregada",
        latencia_ms=latencia_ms,
        control_uso=control_uso,
    )
    response.headers.update(cabeceras)
    response.headers["X-Download-Token"] = emitir_token(solicitud_id)
    response.headers["Cache-Control"] = "no-store"
    if respuesta.get("step"):
        response.headers["X-Step-URL"] = str(
            request.url_for("descargar_step", identificador=solicitud_id)
        )
    logger.info("solicitud entregada")
    return respuesta


@router.post(
    "/generar",
    response_model=dict[str, str],
    responses={
        200: {
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "x-event-data-schema": {"$ref": "#/components/schemas/EstadoTrabajo"},
                }
            }
        },
        409: {"description": "La clave de idempotencia ya se usó con otra solicitud."},
        429: {"description": "Límite por ventana excedido o presupuesto diario agotado."},
    },
)
def generar(
    solicitud: SolicitudGenerar,
    request: Request,
    response: Response,
    procesador: Annotated[Procesador, Depends(obtener_procesador)],
    procesador_sse: Annotated[ProcesadorSSE, Depends(obtener_procesador_sse)],
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    cola: Annotated[ColaTrabajos, Depends(obtener_cola_trabajos)],
    configuracion: Annotated[seguimiento.Configuracion, Depends(obtener_configuracion_seguimiento)],
    control: Annotated[ControlUso, Depends(obtener_control_uso)],
    usuario: Annotated[str, Depends(usuario_actual)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=255)] = None,
) -> dict[str, str] | StreamingResponse | JSONResponse:
    """Procesa una solicitud CAD validada, la registra (AC3/AC4) y la mide (HU-16)."""
    solicitud_id = _identificador(request)  # RF-5: reutiliza X-Request-ID válido.
    with contexto_solicitud(request_id=solicitud_id):
        inicio = time.perf_counter()
        logger.info("solicitud recibida: POST /generar")
        sesion = _sesion(request, usuario)
        transporte = "sse" if _acepta_sse(request) else "json"
        clave = _clave_idempotencia(idempotency_key)
        if clave is not None and autenticacion_activa():
            # HU-53: cada usuario tiene su propio espacio de claves; la de otro no
            # bloquea (409) ni se repite.
            clave = f"{sesion}\n{clave}"
        repetido, registro = control.reservar_idempotencia(
            clave, sesion, solicitud.texto, transporte, solicitud_id
        )
        if repetido:
            logger.info("generación repetida con la misma clave de idempotencia")
            return _respuesta_repetida(registro, gestor, cola, response)

        try:
            if _usa_cola_persistente():
                _conciliar_gasto_cola(cola, control)
            control.reservar(sesion)
        except ErrorControlUso:
            control.liberar_idempotencia(clave, registro)
            raise

        def guardar_terminal(terminal: dict) -> None:
            control.confirmar_idempotencia(clave, registro, estado_final=terminal)

        try:
            if transporte == "sse":
                return _generar_sse(
                    solicitud,
                    request,
                    procesador_sse,
                    gestor,
                    cola,
                    configuracion,
                    inicio,
                    solicitud_id,
                    control,
                    al_terminal=guardar_terminal,
                    al_crear=lambda trabajo_id: control.vincular_idempotencia(
                        clave, registro, trabajo_id
                    ),
                    usuario=usuario,
                )
            respuesta = _generar_json(
                solicitud,
                request,
                response,
                procesador,
                configuracion,
                solicitud_id,
                inicio,
                control,
                usuario=usuario,
            )
            control.confirmar_idempotencia(
                clave, registro, respuesta=respuesta, cabeceras=dict(response.headers)
            )
            return respuesta
        except BaseException:
            control.liberar_idempotencia(clave, registro)
            raise


_SIN_VERSIONES = "No hay versiones para esa solicitud."
_INDICE_ILEGIBLE = (
    "El historial de versiones de esa solicitud no está disponible: "
    "el índice guardado no se pudo leer."
)
_INDICE_SIN_GUARDAR = (
    "La edición se construyó pero no se pudo guardar como versión nueva: "
    "el historial de versiones no está disponible."
)


def _error_indice(exc: Exception) -> HTTPException:
    """Traduce un índice de versiones ilegible a un error catalogado (HU-35)."""
    logger.warning("historial de versiones ilegible: %s", exc)
    return HTTPException(status.HTTP_409_CONFLICT, _INDICE_ILEGIBLE)


def _historial_propio(solicitud_id: str, usuario: str) -> list[dict]:
    """Versiones legibles y del solicitante; si no se pueden atribuir, 404 (HU-53).

    Con autenticación activa un índice ilegible no se puede probar del solicitante,
    así que responde igual que un id desconocido: un usuario nunca puede distinguir
    el historial ajeno del inexistente (B3). En modo local no hay terceros y se
    informa el 409 con el mensaje catalogado.
    """
    try:
        guardadas = versiones.leer_versiones(solicitud_id)
    except versiones.ErrorVersiones as exc:
        if autenticacion_activa():
            logger.warning("historial de versiones ilegible: %s", exc)
            raise HTTPException(status.HTTP_404_NOT_FOUND, _SIN_VERSIONES) from exc
        raise _error_indice(exc) from exc
    if not guardadas:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _SIN_VERSIONES)
    garantizar_propietario(usuario, guardadas[0].get("usuario"), _SIN_VERSIONES)
    return guardadas


def _registrar_version_inicial(solicitud_id: str, usuario: str, medido: dict) -> None:
    """Deja la versión 1 de una generación recién entregada (HU-35, AC3).

    Como el seguimiento, el histórico es best-effort: una entrega ya construida no
    se cae porque el índice no se pueda escribir.
    """
    programa = medido.get("programa")
    if not isinstance(programa, dict) or not programa:
        return
    try:
        if versiones.ultima_version(solicitud_id) is not None:
            return
        versiones.registrar_version(
            solicitud_id,
            usuario=usuario,
            programa=programa,
            artefactos=[str(ruta) for ruta in (medido.get("artefactos") or [])],
            prompt=str(medido.get("prompt") or ""),
            prompt_hash=str(medido.get("prompt_hash") or ""),
        )
    except (versiones.ErrorVersiones, OSError) as exc:
        logger.warning("no se pudo registrar la versión inicial: %s", exc)


def _editar_json(
    solicitud_origen: str,
    previa: dict,
    cuerpo: SolicitudEdicion,
    request: Request,
    response: Response,
    configuracion: seguimiento.Configuracion,
    control: ControlUso,
    usuario: str,
) -> RespuestaEdicion:
    """Aplica una edición verificada y registra la versión nueva (HU-35, AC1/AC2).

    La versión previa llega ya resuelta y autorizada por la ruta: así un 404 por
    solicitud inexistente o ajena ocurre antes de reservar cupo de la ventana
    (HU-32, R3-reserva-ventana-404).
    """
    # Importación diferida: el núcleo CAD (cadquery/OCP) sólo se carga al usarlo.
    from m2_cad import pipeline as modulo_pipeline

    inicio = time.perf_counter()
    registro_id = _identificador(request)

    medido: dict[str, object] = {}
    medir_uso = _preparar_medicion(modulo_pipeline, medido, prompt=modulo_pipeline.PROMPT_EDICION)
    corrida = seguimiento.iniciar_corrida(
        configuracion.experimento_generacion,
        nombre=registro_id,
        tags={
            "solicitud_id": registro_id,
            "request_id": registro_id,
            "solicitud_origen": solicitud_origen,
            "operacion": "edicion",
            "usuario": usuario,
        },
        configuracion=configuracion,
    )
    estado, motivo, causa, fallo = "entregada", None, None, None
    entrada: dict | None = None
    resultado = None
    try:
        resultado = modulo_pipeline.editar_pieza(
            previa["programa"], cuerpo.instruccion, medir_uso=medir_uso
        )
    except modulo_pipeline.PiezaDeclinada as exc:
        estado, motivo, causa = "declinada", exc.motivo, str(exc.causa)
        medido.update(familia="desconocida", causa=str(exc.causa), artefactos=[exc.programa_json])
        _anotar_detalle(exc)
        fallo = DeclinacionSolicitud(exc.motivo, exc.programa_json, causa=exc.causa)
    except (modulo_pipeline.ErrorGeneracion, modulo_pipeline.ErrorVerificacion) as exc:
        estado, causa = "error", str(exc.causa)
        medido.update(familia="desconocida", causa=str(exc.causa))
        _anotar_detalle(exc)
        fallo = FalloHTTP(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.mensaje, type(exc).__name__)
    except modulo_pipeline.ModeloNoDisponible as exc:
        estado = "error"
        medido["familia"] = "desconocida"
        fallo = FalloHTTP(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc), "ModeloNoDisponible")

    respuesta: dict[str, object] | None = None
    if resultado is not None:
        medido.update(
            familia=resultado.familia,
            artefactos=[
                resultado.programa_json,
                resultado.step,
                resultado.glb,
                resultado.bom_csv,
            ],
        )
        diff = versiones.diff_programas(previa["programa"], resultado.programa)
        try:
            entrada = versiones.registrar_version(
                solicitud_origen,
                usuario=usuario,
                programa=resultado.programa,
                artefactos=[str(ruta) for ruta in (medido.get("artefactos") or [])],
                prompt=str(medido.get("prompt") or ""),
                prompt_hash=str(medido.get("prompt_hash") or ""),
                diff=diff,
            )
        except (versiones.ErrorVersiones, OSError) as exc:
            # B2: la fila del registro, el costo y el cierre de la corrida se
            # escriben igual antes de responder; el mensaje no habla de lectura.
            logger.warning("no se pudo guardar la versión nueva: %s", exc)
            estado = "error"
            fallo = HTTPException(status.HTTP_409_CONFLICT, _INDICE_SIN_GUARDAR)
            entrada = None
        if entrada is not None:
            respuesta = {
                "solicitud_id": solicitud_origen,
                "version": entrada["version"],
                "prompt": str(medido.get("prompt") or ""),
                "programa": resultado.programa,
                "diff": diff,
                **resultado.a_respuesta(),
            }

    latencia_ms = (time.perf_counter() - inicio) * 1000
    registrar(
        texto=cuerpo.instruccion,
        traduccion=SIN_TRADUCCION,
        resultado=respuesta,
        latencia_ms=latencia_ms,
        error=_texto_fallo(fallo),
        version=seguimiento.version_modelo(),
        ruta=obtener_ruta_registro(),
        identificador=registro_id,
        usuario=usuario,
        causa=causa,
        prompt=str(medido.get("prompt") or ""),
        prompt_hash=str(medido.get("prompt_hash") or ""),
    )
    medir_solicitud(
        corrida,
        medido,
        configuracion,
        estado=estado,
        latencia_ms=latencia_ms,
        motivo_declinacion=motivo,
        error=None if fallo is None else f"HTTP {fallo.status_code}",
        control_uso=control,
        params_extra={
            "operacion": "edicion",
            "solicitud_origen": solicitud_origen,
            "version_pieza": entrada["version"] if entrada else None,
        },
    )
    if fallo is not None:
        raise fallo
    cabeceras = _cabeceras_registro(request, registro_id)
    response.headers.update(cabeceras)
    response.headers["X-Download-Token"] = emitir_token(registro_id)
    response.headers["Cache-Control"] = "no-store"
    if str(respuesta.get("step") or ""):
        response.headers["X-Step-URL"] = str(
            request.url_for("descargar_step", identificador=registro_id)
        )
    logger.info("edición entregada como versión %s", entrada["version"])
    assert respuesta is not None and entrada is not None
    return RespuestaEdicion(**respuesta)


def _texto_fallo(fallo: HTTPException | None) -> str | None:
    """Detalle legible para la columna `error` del registro; `None` si no hubo fallo."""
    if fallo is None:
        return None
    detalle = getattr(fallo, "motivo", None)
    return str(detalle if detalle else fallo.detail)


@router.post(
    "/generar/{solicitud_id}/editar",
    response_model=RespuestaEdicion,
    responses={
        404: {"description": "La solicitud no existe o no es del usuario."},
        409: {
            "description": (
                "La clave de idempotencia ya se usó para esta edición, o el historial "
                "de versiones guardado no se pudo leer."
            )
        },
        422: {"description": "La edición no pasa la verificación; incluye la causa."},
        429: {"description": "Límite por ventana excedido o presupuesto diario agotado."},
    },
)
def editar_pieza(
    solicitud_id: str,
    cuerpo: SolicitudEdicion,
    request: Request,
    response: Response,
    configuracion: Annotated[seguimiento.Configuracion, Depends(obtener_configuracion_seguimiento)],
    control: Annotated[ControlUso, Depends(obtener_control_uso)],
    usuario: Annotated[str, Depends(usuario_actual)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=255)] = None,
) -> RespuestaEdicion:
    """Edita la pieza vigente de una solicitud y entrega una versión nueva (RF-1..RF-4)."""
    try:
        origen = versiones.validar_solicitud_id(solicitud_id)
    except versiones.ErrorVersiones as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _SIN_VERSIONES) from exc
    with contexto_solicitud(request_id=_identificador(request)):
        logger.info("edición recibida: POST /generar/{id}/editar")
        sesion = _sesion(request, usuario)
        clave = _clave_idempotencia(idempotency_key)
        if clave is not None and autenticacion_activa():
            clave = f"{sesion}\n{clave}"
        # La solicitud se resuelve y se autoriza ANTES de reservar cupo: un 404 no
        # consume la ventana de uso (HU-32, R3-reserva-ventana-404).
        previa = _historial_propio(origen, usuario)[-1]
        repetido, reserva = control.reservar_idempotencia(
            clave, sesion, cuerpo.instruccion, "json", origen
        )
        if repetido:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La clave de idempotencia ya se usó para esta edición.",
            )
        try:
            control.reservar(sesion)
        except ErrorControlUso:
            control.liberar_idempotencia(clave, reserva)
            raise
        try:
            respuesta = _editar_json(
                origen, previa, cuerpo, request, response, configuracion, control, usuario
            )
        except BaseException:
            control.liberar_idempotencia(clave, reserva)
            raise
        control.confirmar_idempotencia(clave, reserva)
        return respuesta


@router.get(
    "/generar/{solicitud_id}/versiones",
    response_model=RespuestaVersiones,
    responses={
        404: {"description": "La solicitud no existe o no es del usuario."},
        409: {"description": "El historial de versiones guardado no se pudo leer."},
    },
)
def historial_de_versiones(
    solicitud_id: str,
    usuario: Annotated[str, Depends(usuario_actual)],
) -> RespuestaVersiones:
    """Historial de versiones de la solicitud, en orden ascendente (RF-5, AC3)."""
    try:
        clave = versiones.validar_solicitud_id(solicitud_id)
    except versiones.ErrorVersiones as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _SIN_VERSIONES) from exc
    guardadas = _historial_propio(clave, usuario)
    return RespuestaVersiones(
        solicitud_id=clave,
        versiones=[
            VersionPieza(
                version=int(entrada["version"]),
                hora=str(entrada["hora"]),
                programa=entrada["programa"],
                artefactos=[str(ruta) for ruta in entrada.get("artefactos") or []],
                diff=entrada.get("diff") or [],
                prompt=str(entrada.get("prompt") or ""),
                prompt_hash=str(entrada.get("prompt_hash") or ""),
            )
            for entrada in guardadas
        ],
    )


# La sesión es sólo un control de acceso: el gasto es global, no por usuario.
@router.get("/uso", response_model=RespuestaUso, dependencies=[Depends(usuario_actual)])
def consultar_uso(
    control: Annotated[ControlUso, Depends(obtener_control_uso)],
    cola: Annotated[ColaTrabajos, Depends(obtener_cola_trabajos)],
) -> RespuestaUso:
    """RF-5/AC4: gasto acumulado del día, sin red ni identificadores de cliente."""
    if _usa_cola_persistente():
        _conciliar_gasto_cola(cola, control)
    return RespuestaUso(**control.gasto_acumulado())


@router.get("/generaciones/{solicitud_id}", response_model=EstadoTrabajo)
def consultar_generacion(
    solicitud_id: str,
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    cola: Annotated[ColaTrabajos, Depends(obtener_cola_trabajos)],
    usuario: Annotated[str, Depends(usuario_actual)],
) -> dict:
    """Consulta la confirmación terminal incluso después de perder la conexión SSE."""
    trabajo = _trabajo(solicitud_id, gestor, cola)
    garantizar_propietario(usuario, trabajo.usuario)
    return trabajo.estado()


@router.delete(
    "/generaciones/{solicitud_id}",
    response_model=EstadoTrabajo,
    responses={
        202: {"model": EstadoTrabajo, "description": "Cancelación solicitada, no confirmada."}
    },
)
def cancelar_generacion(
    solicitud_id: str,
    response: Response,
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    cola: Annotated[ColaTrabajos, Depends(obtener_cola_trabajos)],
    usuario: Annotated[str, Depends(usuario_actual)],
) -> dict:
    """202 pide detenerse; solo un estado terminal confirma el desenlace real."""
    trabajo = _trabajo(solicitud_id, gestor, cola)
    garantizar_propietario(usuario, trabajo.usuario)
    estado = trabajo.cancelar()
    response.status_code = 200 if estado["terminal"] else 202
    return estado


def obtener_directorio_salidas() -> Path:
    return Path("outputs").resolve()


@router.get("/generaciones/{solicitud_id}/archivos/{formato}")
@router.head("/generaciones/{solicitud_id}/archivos/{formato}", include_in_schema=False)
def descargar_archivo(
    solicitud_id: str,
    formato: str,
    request: Request,
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    cola: Annotated[ColaTrabajos, Depends(obtener_cola_trabajos)],
    salidas: Annotated[Path, Depends(obtener_directorio_salidas)],
    usuario: Annotated[str, Depends(usuario_actual)],
) -> FileResponse:
    """Entrega solo artefactos propios y verificados; el token de HU-36 sigue vigente."""
    exigir_token(solicitud_id, request.headers.get("X-Download-Token"))
    trabajo = _trabajo(solicitud_id, gestor, cola)
    garantizar_propietario(usuario, trabajo.usuario)
    estado = trabajo.estado()
    if estado["estado"] != "verificado" or formato not in {"step", "glb", "csv"}:
        raise HTTPException(404, "Archivo no disponible.")
    resultado = estado.get("resultado", {})
    nombre = (
        resultado.get("bom_csv") or resultado.get("csv")
        if formato == "csv"
        else resultado.get(formato)
    )
    if not isinstance(nombre, str) or not nombre:
        raise HTTPException(404, "Archivo no disponible.")
    ruta = Path(nombre)
    if not ruta.is_absolute():
        ruta = Path.cwd() / ruta if ruta.parts[0] == "outputs" else salidas / ruta
    ruta = ruta.resolve()
    if (
        not ruta.is_relative_to(salidas.resolve())
        or ruta.suffix.lower() != f".{formato}"
        or not ruta.is_file()
    ):
        raise HTTPException(404, "Archivo no disponible.")
    tipos = {"step": "application/step", "glb": "model/gltf-binary", "csv": "text/csv"}
    return FileResponse(
        ruta,
        media_type=tipos[formato],
        filename=f"pieza.{formato}",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


def _cabeceras_deprecacion(destino: str) -> dict[str, str]:
    """Anuncia la sustitución de una ruta plana por su equivalente `/v1` (RF-5)."""
    return {
        "Deprecation": DEPRECACION_RUTAS_PLANAS,
        "Sunset": SUNSET_RUTAS_PLANAS,
        "Link": f'<{destino}>; rel="successor-version"',
    }


async def _redirigir_a_v1(request: Request) -> RedirectResponse:
    """Conserva método, cuerpo y query al pasar una ruta plana a `/v1` (RF-2)."""
    raiz = request.scope.get("root_path", "").rstrip("/")
    ruta = request.url.path
    if raiz and ruta.startswith(raiz):
        ruta = ruta[len(raiz) :]
    destino = str(request.url.replace(path=f"{raiz}{PREFIJO_V1}{ruta}"))
    return RedirectResponse(
        destino,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers=_cabeceras_deprecacion(destino),
    )


_RUTAS_PLANAS = (
    ("/health", ("GET",)),
    ("/ready", ("GET",)),
    ("/registros/{identificador}", ("GET",)),
    ("/registros/{identificador}/step", ("GET",)),
    ("/generar", ("POST",)),
    ("/generaciones/{solicitud_id}", ("GET", "DELETE")),
    ("/generaciones/{solicitud_id}/archivos/{formato}", ("GET", "HEAD")),
)

app.include_router(router)

for _ruta, _metodos in _RUTAS_PLANAS:
    for _metodo in _metodos:
        _nombre = (
            f"legado_{_metodo.lower()}_"
            f"{_ruta.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
        )
        app.add_api_route(
            _ruta,
            _redirigir_a_v1,
            methods=[_metodo],
            name=_nombre,
            include_in_schema=False,
        )

# Rutas estáticas explícitas; las rutas API desconocidas conservan su 404 JSON.
configurar_web(app)
