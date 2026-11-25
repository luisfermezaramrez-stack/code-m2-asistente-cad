"""Contratos HTTP/SSE compartidos; SPEC-028 (HU-27), AC1 y AC3."""

from typing import Literal

from typing_extensions import NotRequired, TypedDict

EtapaTrabajo = Literal[
    "iniciando", "validando", "generando", "verificado", "declinado", "error", "cancelado"
]


class EstadoTrabajo(TypedDict):
    """JSON de consulta, cancelación y data SSE; opcional significa campo ausente."""

    solicitud_id: str
    estado: EtapaTrabajo
    terminal: bool
    cancelacion_solicitada: bool
    secuencia: NotRequired[int]
    resultado: NotRequired[dict[str, str]]
    motivo: NotRequired[str]
    codigo_http: NotRequired[int]
    pipeline_detenido: NotRequired[bool]
    cancelacion_remota_confirmada: NotRequired[bool]
