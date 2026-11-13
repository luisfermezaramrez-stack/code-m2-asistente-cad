"""API REST para la generación preliminar de componentes CAD (HU-06)."""

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from m2_cad.registro import RUTA_DEFAULT, registrar
from m2_cad.seguimiento import ControlGeneracion, SolicitudDeclinada
from m2_cad.trabajos import GestorTrabajos, Procesador, RespuestaSSE
from m2_cad.web import configurar_web

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
    """Informa que el pipeline CAD todavía no está integrado."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="El pipeline CAD aún no está disponible.",
    )


def procesar_con_pipeline(texto: str) -> dict[str, str]:
    """Genera la pieza con el pipeline CAD (HU-04) y traduce sus errores a HTTP."""
    if not os.environ.get("LLM_BASE_URL"):
        return procesador_no_disponible(texto)

    # Importación diferida: el núcleo CAD (cadquery/OCP) solo se carga al usarlo.
    from m2_cad import pipeline
    from m2_cad.traduccion import ErrorTraduccion

    try:
        return pipeline.generar_pieza(texto).a_respuesta()
    except pipeline.PiezaDeclinada as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Pieza declinada: {exc.motivo}",
        ) from exc
    except (pipeline.ErrorGeneracion, pipeline.ErrorVerificacion) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except (pipeline.ModeloNoDisponible, ErrorTraduccion) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


def obtener_procesador() -> Callable[[str], dict[str, str]]:
    """Proporciona el procesador CAD utilizado por la API."""
    return procesar_con_pipeline


def procesar_con_progreso(texto: str, control: ControlGeneracion) -> dict[str, str]:
    """Adaptador SSE: distingue declinaciones sin inferirlas de un código 422."""
    if not os.environ.get("LLM_BASE_URL"):
        control.informar("validando")
        return procesador_no_disponible(texto)

    from m2_cad import pipeline
    from m2_cad.traduccion import ErrorTraduccion

    try:
        return pipeline.generar_pieza(texto, control=control).a_respuesta()
    except pipeline.PiezaDeclinada as exc:
        raise SolicitudDeclinada(exc.motivo) from exc
    except (pipeline.ErrorGeneracion, pipeline.ErrorVerificacion) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (pipeline.ModeloNoDisponible, ErrorTraduccion) as exc:
        raise HTTPException(503, "El servicio de generación no está disponible.") from exc


def obtener_procesador_sse() -> Procesador:
    return procesar_con_progreso


def obtener_gestor_trabajos() -> GestorTrabajos:
    return gestor_trabajos


def obtener_ruta_registro() -> Path:
    """Proporciona la ruta del CSV de registro (HU-06, AC3/AC4)."""
    return RUTA_DEFAULT


@app.post(
    "/generar",
    response_model=dict[str, str],
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
def generar(
    solicitud: SolicitudGenerar,
    request: Request,
    procesador: Annotated[
        Callable[[str], dict[str, str]],
        Depends(obtener_procesador),
    ],
    procesador_sse: Annotated[Procesador, Depends(obtener_procesador_sse)],
    gestor: Annotated[GestorTrabajos, Depends(obtener_gestor_trabajos)],
) -> dict[str, str] | StreamingResponse:
    """Procesa una solicitud CAD validada y la registra (AC3 y AC4)."""
    inicio = time.perf_counter()
    tipos = [tipo.split(";")[0].strip() for tipo in request.headers.get("accept", "").split(",")]
    if "text/event-stream" in tipos:
        ruta_registro = obtener_ruta_registro()

        def registrar_terminal(terminal: dict) -> None:
            resultado = terminal.get("resultado")
            registrar(
                texto=solicitud.texto,
                traduccion=resultado.get("traduccion", "") if resultado else "",
                resultado=resultado,
                latencia_ms=(time.perf_counter() - inicio) * 1000,
                error=terminal.get("motivo"),
                version="desconocida",
                ruta=ruta_registro,
            )

        trabajo = gestor.crear(solicitud.texto, procesador_sse, registrar_terminal)
        return RespuestaSSE(trabajo, request)
    try:
        respuesta = procesador(solicitud.texto)
    except HTTPException as exc:
        registrar(
            texto=solicitud.texto,
            traduccion="",
            resultado=None,
            latencia_ms=(time.perf_counter() - inicio) * 1000,
            error=str(exc.detail),
            version="desconocida",
            ruta=obtener_ruta_registro(),
        )
        raise

    registrar(
        texto=solicitud.texto,
        traduccion="",
        resultado=respuesta,
        latencia_ms=(time.perf_counter() - inicio) * 1000,
        version="desconocida",
        ruta=obtener_ruta_registro(),
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
