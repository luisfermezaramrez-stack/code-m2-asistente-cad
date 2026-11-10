"""API REST para la generación preliminar de componentes CAD (HU-06)."""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from m2_cad.registro import RUTA_DEFAULT, registrar

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
    """Informa que el pipeline CAD todavía no está integrado."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="El pipeline CAD aún no está disponible.",
    )


def obtener_procesador() -> Callable[[str], dict[str, str]]:
    """Proporciona el procesador CAD utilizado por la API."""
    return procesador_no_disponible


def obtener_ruta_registro() -> Path:
    """Proporciona la ruta del CSV de registro (HU-06, AC3/AC4)."""
    return RUTA_DEFAULT


@app.post("/generar")
def generar(
    solicitud: SolicitudGenerar,
    procesador: Annotated[
        Callable[[str], dict[str, str]],
        Depends(obtener_procesador),
    ],
) -> dict[str, str]:
    """Procesa una solicitud CAD validada y la registra (AC3 y AC4)."""
    inicio = time.perf_counter()
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
