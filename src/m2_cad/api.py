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
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from m2_cad import seguimiento
from m2_cad.cola_trabajos import ColaTrabajos
from m2_cad.contratos import EstadoTrabajo
from m2_cad.control import ControlGeneracion, SolicitudDeclinada
from m2_cad.observabilidad import (
    configurar_logging,
    contexto_solicitud,
    job_id_actual,
    request_id_actual,
)
from m2_cad.registro import RUTA_DEFAULT, SIN_TRADUCCION, registrar
from m2_cad.retencion_salidas import depurar_outputs, leer_politica
from m2_cad.seguridad_descargas import emitir_token, exigir_token, validar_uuid
from m2_cad.trabajos import GestorTrabajos, RespuestaSSE
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
    """Abre la cola al arrancar y detiene la retención al cerrar (HU-45, RF-4)."""
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

app = FastAPI(
    title="M2 CAD Assistant API",
    lifespan=_ciclo_aplicacion,
    version="0.1.0",
    description="Servicio de generación preliminar de componentes CAD.",
)
gestor_trabajos = GestorTrabajos()
cola_trabajos = ColaTrabajos()


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


@app.get("/health")
def health() -> dict[str, str]:
    """Comprueba que el proceso de la API está disponible."""
    return {"status": "ok"}


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
    """Declinación con motivo y programa, sin cambiar el 422 de HU-05."""

    def __init__(self, motivo: str, programa_json: Path | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Pieza declinada: {motivo}",
            headers={"X-Resultado-Tipo": "declinacion_explicita"},
        )
        self.motivo = motivo
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


@app.get("/ready")
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


def _preparar_medicion(pipeline, medido: dict) -> Callable[[dict], None]:
    """Anota modelo y versión, y devuelve el receptor del `usage` (HU-16, AC2)."""
    medido.update(
        modelo=pipeline.llm.planner_model(),
        version_modelo=seguimiento.version_modelo(),
        temperatura=pipeline.TEMPERATURA_LLM,
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
        medido.update(familia="desconocida", artefactos=[exc.programa_json])
        raise DeclinacionSolicitud(exc.motivo, exc.programa_json) from exc
    except (pipeline.ErrorGeneracion, pipeline.ErrorVerificacion) as exc:
        medido["familia"] = "desconocida"
        raise FalloHTTP(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc), type(exc).__name__
        ) from exc
    except pipeline.ModeloNoDisponible as exc:
        medido["familia"] = "desconocida"
        raise FalloHTTP(
            status.HTTP_503_SERVICE_UNAVAILABLE, str(exc), "ModeloNoDisponible"
        ) from exc

    medido.update(
        familia=resultado.familia,
        artefactos=[resultado.programa_json, resultado.step, resultado.glb, resultado.bom_csv],
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
        medido.update(familia="desconocida", artefactos=[exc.programa_json])
        raise SolicitudDeclinada(exc.motivo) from exc
    except (pipeline.ErrorGeneracion, pipeline.ErrorVerificacion) as exc:
        medido["familia"] = "desconocida"
        raise FalloHTTP(422, str(exc), type(exc).__name__) from exc
    except pipeline.ModeloNoDisponible as exc:
        medido["familia"] = "desconocida"
        raise FalloHTTP(
            503, "El servicio de generación no está disponible.", "ModeloNoDisponible"
        ) from exc

    medido.update(
        familia=resultado.familia,
        artefactos=[resultado.programa_json, resultado.step, resultado.glb, resultado.bom_csv],
    )
    return resultado.a_respuesta()


def obtener_procesador_sse() -> ProcesadorSSE:
    return procesar_con_progreso


def obtener_gestor_trabajos() -> GestorTrabajos:
    return gestor_trabajos


def obtener_cola_trabajos() -> ColaTrabajos:
    """Cola persistente de SSE; sustituible en pruebas (HU-45)."""
    return cola_trabajos


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


@app.get("/registros/{identificador}")
def consultar_registro(identificador: str) -> dict[str, str]:
    """Consulta una fila existente, sin escribir ni duplicar el registro (HU-07 AC3)."""
    identificador = validar_uuid(identificador)
    ruta = obtener_ruta_registro()
    if ruta.exists():
        with ruta.open(encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                if fila["id"] == identificador:
                    return fila
    raise HTTPException(404, "Registro no encontrado.")


@app.get("/registros/{identificador}/step")
def descargar_step(identificador: str, request: Request) -> FileResponse:
    """Enlaza el STEP del registro persistente, incluso tras reiniciar los trabajos."""
    exigir_token(identificador, request.headers.get("X-Download-Token"))
    fila = consultar_registro(identificador)
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
    if request.method == "POST" and request.url.path == "/generar":
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
        )
        respuesta.headers.update(_cabeceras_registro(request, identificador))
    return respuesta


def _clasificar(exc: HTTPException) -> tuple[str, str | None, str | None]:
    """Estado, motivo de declinación y clase de error de la corrida (AC3)."""
    if isinstance(exc, DeclinacionSolicitud):
        return "declinada", exc.motivo, None
    return "error", None, getattr(exc, "clase", type(exc).__name__)


def medir_solicitud(
    corrida: seguimiento.Corrida,
    medido: dict,
    configuracion: seguimiento.Configuracion,
    *,
    estado: str,
    latencia_ms: float,
    motivo_declinacion: str | None = None,
    error: str | None = None,
) -> None:
    """Registra params, métricas, tags y artefactos, y cierra la corrida (AC2/AC3)."""
    corrida.registrar_params(
        modelo=medido.get("modelo"),
        version_modelo=medido.get("version_modelo"),
        familia=medido.get("familia"),
        temperatura=medido.get("temperatura"),
    )
    tokens_entrada = medido.get("tokens_entrada")
    tokens_salida = medido.get("tokens_salida")
    # Sin usage no se registra costo 0.0: distorsionaría los promedios de MLflow.
    costo_usd = (
        None
        if tokens_entrada is None and tokens_salida is None
        else seguimiento.costo_usd(
            tokens_entrada,
            tokens_salida,
            precio_entrada=configuracion.precio_entrada,
            precio_salida=configuracion.precio_salida,
        )
    )
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
    corrida.finalizar(estado=estado, motivo_declinacion=motivo_declinacion, error=error)
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
        )
        estado = _ESTADOS_CORRIDA_SSE.get(terminal["estado"], "error")
        solicitud_id = terminal["solicitud_id"]
        corrida = seguimiento.iniciar_corrida(
            configuracion.experimento_generacion,
            nombre=solicitud_id,
            tags={
                "solicitud_id": solicitud_id,
                "request_id": request_id_actual() or solicitud_id,
                "job_id": job_id_actual() or solicitud_id,
                "transporte": "sse",
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
        )
        logger.info("generación terminada en %s", estado)

    if _usa_cola_persistente() and procesador_sse is procesar_con_progreso:
        # Despliegue: la API sólo encola; el worker ejecuta y registra (HU-45, AC3).
        trabajo = cola.encolar(
            solicitud.texto,
            request_id=request_id,
            configuracion=asdict(configuracion),
            ruta_registro=obtener_ruta_registro(),
        )
    else:
        # Compatibilidad con la batería SSE heredada que inyecta su propio procesador.
        trabajo = gestor.crear(solicitud.texto, procesar, registrar_terminal)
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
) -> dict[str, str]:
    """Ruta JSON: registro y corrida MLflow con el contexto de la solicitud activo."""
    cabeceras = _cabeceras_registro(request, solicitud_id)
    medido: dict[str, object] = {}
    corrida = seguimiento.iniciar_corrida(
        configuracion.experimento_generacion,
        nombre=solicitud_id,
        tags={"solicitud_id": solicitud_id, "request_id": solicitud_id},
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
        )
        medir_solicitud(
            corrida,
            medido,
            configuracion,
            estado=estado,
            latencia_ms=latencia_ms,
            motivo_declinacion=motivo,
            error=error,
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
        )
        medir_solicitud(
            corrida,
            medido,
            configuracion,
            estado="error",
            latencia_ms=latencia_ms,
            error=type(exc).__name__,
        )
        logger.warning("generación terminada en error (%s)", type(exc).__name__)
        if isinstance(exc, Exception):
            raise HTTPException(500, "Fallo técnico del pipeline.", headers=cabeceras) from exc
        raise

    latencia_ms = (time.perf_counter() - inicio) * 1000
    registrar(
        texto=solicitud.texto,
        traduccion=SIN_TRADUCCION,
        resultado=respuesta,
        latencia_ms=latencia_ms,
        version=seguimiento.version_modelo(),
        ruta=obtener_ruta_registro(),
        identificador=solicitud_id,
    )
    medir_solicitud(corrida, medido, configuracion, estado="entregada", latencia_ms=latencia_ms)
    response.headers.update(cabeceras)
    response.headers["X-Download-Token"] = emitir_token(solicitud_id)
    response.headers["Cache-Control"] = "no-store"
    if respuesta.get("step"):
        response.headers["X-Step-URL"] = str(
            request.url_for("descargar_step", identificador=solicitud_id)
        )
    logger.info("solicitud entregada")
    return respuesta


@app.post(
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
        }
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
) -> dict[str, str] | StreamingResponse:
    """Procesa una solicitud CAD validada, la registra (AC3/AC4) y la mide (HU-16)."""
    solicitud_id = _identificador(request)  # RF-5: reutiliza X-Request-ID válido.
    with contexto_solicitud(request_id=solicitud_id):
        inicio = time.perf_counter()
        logger.info("solicitud recibida: POST /generar")
        if _acepta_sse(request):
            return _generar_sse(
                solicitud,
                request,
                procesador_sse,
                gestor,
                cola,
                configuracion,
                inicio,
                solicitud_id,
            )
        return _generar_json(
            solicitud, request, response, procesador, configuracion, solicitud_id, inicio
        )


@app.get("/generaciones/{solicitud_id}", response_model=EstadoTrabajo)
def consultar_generacion(
    solicitud_id: str,
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    cola: Annotated[ColaTrabajos, Depends(obtener_cola_trabajos)],
) -> dict:
    """Consulta la confirmación terminal incluso después de perder la conexión SSE."""
    try:
        return cola.estado(solicitud_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
    return gestor.obtener(solicitud_id).estado()


@app.delete(
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
) -> dict:
    """202 pide detenerse; solo un estado terminal confirma el desenlace real."""
    try:
        estado = cola.cancelar(solicitud_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
        estado = gestor.obtener(solicitud_id).cancelar()
    response.status_code = 200 if estado["terminal"] else 202
    return estado


def obtener_directorio_salidas() -> Path:
    return Path("outputs").resolve()


@app.get("/generaciones/{solicitud_id}/archivos/{formato}")
@app.head("/generaciones/{solicitud_id}/archivos/{formato}", include_in_schema=False)
def descargar_archivo(
    solicitud_id: str,
    formato: str,
    request: Request,
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    salidas: Annotated[Path, Depends(obtener_directorio_salidas)],
) -> FileResponse:
    """Entrega solo artefactos existentes del resultado verificado de este trabajo."""
    exigir_token(solicitud_id, request.headers.get("X-Download-Token"))
    estado = gestor.obtener(solicitud_id).estado()
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


# Rutas estáticas explícitas; las rutas API desconocidas conservan su 404 JSON.
configurar_web(app)
