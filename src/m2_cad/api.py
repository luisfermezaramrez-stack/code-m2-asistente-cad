"""API REST para la generación preliminar de componentes CAD (HU-06)."""

import os
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from m2_cad import seguimiento
from m2_cad.registro import RUTA_DEFAULT, SIN_TRADUCCION, registrar

Procesador = Callable[[str, dict | None], dict[str, str]]

app = FastAPI(
    title="M2 CAD Assistant API",
    version="0.1.0",
    description="Servicio de generación preliminar de componentes CAD.",
)


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
        )
        self.motivo = motivo
        self.programa_json = programa_json


def _modelo_configurado() -> bool:
    """Hay modelo: DeepSeek con key (HU-14) o un servidor propio en LLM_BASE_URL."""
    return any(
        os.environ.get(variable) for variable in ("LLM_BASE_URL", "LLM_API_KEY", "DEEPSEEK_API_KEY")
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

    medido.update(
        modelo=pipeline.llm.planner_model(),
        version_modelo=seguimiento.version_modelo(),
        temperatura=pipeline.TEMPERATURA_LLM,
    )

    def medir_uso(uso: dict) -> None:
        medido["tokens_entrada"] = int(uso.get("prompt_tokens") or 0)
        medido["tokens_salida"] = int(uso.get("completion_tokens") or 0)

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


def obtener_configuracion_seguimiento() -> seguimiento.Configuracion:
    """Configuración de MLflow de esta solicitud (HU-16); las pruebas la sustituyen."""
    return seguimiento.Configuracion.desde_entorno()


def obtener_ruta_registro() -> Path:
    """Proporciona la ruta del CSV de registro (HU-06, AC3/AC4)."""
    return RUTA_DEFAULT


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


@app.post("/generar")
def generar(
    solicitud: SolicitudGenerar,
    procesador: Annotated[Procesador, Depends(obtener_procesador)],
    configuracion: Annotated[seguimiento.Configuracion, Depends(obtener_configuracion_seguimiento)],
) -> dict[str, str]:
    """Procesa una solicitud CAD validada, la registra (AC3/AC4) y la mide (HU-16)."""
    inicio = time.perf_counter()
    solicitud_id = uuid.uuid4().hex
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
        raise
    except BaseException as exc:
        # Un fallo no previsto también cierra la corrida (AC3): MLflow guarda la
        # corrida activa por hilo y una en RUNNING bloquearía las siguientes.
        medir_solicitud(
            corrida,
            medido,
            configuracion,
            estado="error",
            latencia_ms=(time.perf_counter() - inicio) * 1000,
            error=type(exc).__name__,
        )
        raise

    latencia_ms = (time.perf_counter() - inicio) * 1000
    registrar(
        texto=solicitud.texto,
        traduccion=SIN_TRADUCCION,
        resultado=respuesta,
        latencia_ms=latencia_ms,
        version=seguimiento.version_modelo(),
        ruta=obtener_ruta_registro(),
    )
    medir_solicitud(corrida, medido, configuracion, estado="entregada", latencia_ms=latencia_ms)
    return respuesta
