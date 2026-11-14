"""API REST para la generación preliminar de componentes CAD (HU-06)."""

import ast
import csv
import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from m2_cad import seguimiento
from m2_cad.control import ControlGeneracion, SolicitudDeclinada
from m2_cad.registro import RUTA_DEFAULT, SIN_TRADUCCION, registrar
from m2_cad.trabajos import GestorTrabajos, RespuestaSSE
from m2_cad.web import configurar_web

Procesador = Callable[[str, dict | None], dict[str, str]]
ProcesadorSSE = Callable[[str, ControlGeneracion, dict | None], dict[str, str]]

app = FastAPI(
    title="M2 CAD Assistant API",
    version="0.1.0",
    description="Servicio de generación preliminar de componentes CAD.",
)
gestor_trabajos = GestorTrabajos()


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


def _preparar_medicion(pipeline, medido: dict) -> Callable[[dict], None]:
    """Anota modelo y versión, y devuelve el receptor del `usage` (HU-16, AC2)."""
    medido.update(
        modelo=pipeline.llm.planner_model(),
        version_modelo=seguimiento.version_modelo(),
        temperatura=pipeline.TEMPERATURA_LLM,
    )

    def medir_uso(uso: dict) -> None:
        medido["tokens_entrada"] = int(uso.get("prompt_tokens") or 0)
        medido["tokens_salida"] = int(uso.get("completion_tokens") or 0)

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
    ruta = obtener_ruta_registro()
    if ruta.exists():
        with ruta.open(encoding="utf-8", newline="") as archivo:
            for fila in csv.DictReader(archivo):
                if fila["id"] == identificador:
                    return fila
    raise HTTPException(404, "Registro no encontrado.")


@app.get("/registros/{identificador}/step")
def descargar_step(identificador: str) -> FileResponse:
    """Enlaza el STEP del registro persistente, incluso tras reiniciar los trabajos."""
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
    corrida.registrar_metricas(
        latencia_ms=latencia_ms,
        tokens_entrada=medido.get("tokens_entrada"),
        tokens_salida=medido.get("tokens_salida"),
        costo_usd=seguimiento.costo_usd(
            medido.get("tokens_entrada"),
            medido.get("tokens_salida"),
            precio_entrada=configuracion.precio_entrada,
            precio_salida=configuracion.precio_salida,
        ),
        verificacion_ok=1 if estado == "entregada" else 0,
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


_ESTADOS_CORRIDA_SSE = {
    "verificado": "entregada",
    "declinado": "declinada",
    "cancelado": "cancelada",
}


def _acepta_sse(request: Request) -> bool:
    tipos = [tipo.split(";")[0].strip() for tipo in request.headers.get("accept", "").split(",")]
    return "text/event-stream" in tipos


def _generar_sse(
    solicitud: SolicitudGenerar,
    request: Request,
    procesador_sse: ProcesadorSSE,
    gestor: GestorTrabajos,
    configuracion: seguimiento.Configuracion,
    inicio: float,
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
            tags={"solicitud_id": solicitud_id, "transporte": "sse"},
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

    trabajo = gestor.crear(solicitud.texto, procesar, registrar_terminal)
    respuesta = RespuestaSSE(trabajo, request)
    respuesta.headers.update(_cabeceras_registro(request, trabajo.id))
    return respuesta


@app.post(
    "/generar",
    response_model=dict[str, str],
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
def generar(
    solicitud: SolicitudGenerar,
    request: Request,
    response: Response,
    procesador: Annotated[Procesador, Depends(obtener_procesador)],
    procesador_sse: Annotated[ProcesadorSSE, Depends(obtener_procesador_sse)],
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    configuracion: Annotated[seguimiento.Configuracion, Depends(obtener_configuracion_seguimiento)],
) -> dict[str, str] | StreamingResponse:
    """Procesa una solicitud CAD validada, la registra (AC3/AC4) y la mide (HU-16)."""
    inicio = time.perf_counter()
    if _acepta_sse(request):
        return _generar_sse(solicitud, request, procesador_sse, gestor, configuracion, inicio)
    solicitud_id = _identificador(request)
    cabeceras = _cabeceras_registro(request, solicitud_id)
    medido: dict[str, object] = {}
    corrida = seguimiento.iniciar_corrida(
        configuracion.experimento_generacion,
        nombre=solicitud_id,
        tags={"solicitud_id": solicitud_id},
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
    if respuesta.get("step"):
        response.headers["X-Step-URL"] = str(
            request.url_for("descargar_step", identificador=solicitud_id)
        )
    return respuesta


@app.get("/generaciones/{solicitud_id}")
def consultar_generacion(
    solicitud_id: str,
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
) -> dict:
    """Consulta la confirmación terminal incluso después de perder la conexión SSE."""
    return gestor.obtener(solicitud_id).estado()


@app.delete("/generaciones/{solicitud_id}")
def cancelar_generacion(
    solicitud_id: str,
    response: Response,
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
) -> dict:
    """202 pide detenerse; solo un estado terminal confirma el desenlace real."""
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
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
    salidas: Annotated[Path, Depends(obtener_directorio_salidas)],
) -> FileResponse:
    """Entrega solo artefactos existentes del resultado verificado de este trabajo."""
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
