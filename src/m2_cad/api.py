"""API REST para la generación preliminar de componentes CAD (HU-06)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

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


@app.post("/generar")
def generar(
    solicitud: SolicitudGenerar,
    procesador: Annotated[
        Callable[[str], dict[str, str]],
        Depends(obtener_procesador),
    ],
) -> dict[str, str]:
    """Procesa una solicitud CAD validada."""
    return procesador(solicitud.texto)
