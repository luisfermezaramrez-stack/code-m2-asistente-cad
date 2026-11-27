"""Panorama de métricas sobre MLflow (HU-51 · specs/052-hu-51-panorama-metricas/spec.md).

Lee las corridas que ya registra `m2_cad.seguimiento` y las agrega en una ventana
de tiempo (S1, S2): totales, piezas entregadas, declinaciones por causa, latencia y
costo. No se crea almacén propio ni caché: la fuente única es MLflow.

`resumir_corridas` es pura; `leer_corridas` y `panorama` son las únicas funciones
que tocan el backend. Todo fallo de MLflow se convierte en
`SeguimientoNoDisponible` — o, en `panorama`, en un estado degradado explícito con
`disponible: False` y un `motivo` en español (S6/AC2, nunca 500).

RNF-3 (S7): el resultado no incluye textos de solicitud, nombres de usuario ni ids
de corrida; sólo contadores, media de latencia, costo acumulado y el enlace a la UI
de MLflow. Importable sin el kernel CAD (stdlib + `m2_cad.seguimiento`).
"""

from __future__ import annotations

import math
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

from m2_cad import seguimiento

__all__ = [
    "HORAS_MAXIMAS",
    "HORAS_POR_DEFECTO",
    "SeguimientoNoDisponible",
    "UI_POR_DEFECTO",
    "VARIABLE_UI",
    "leer_corridas",
    "lectura",
    "panorama",
    "resumir_corridas",
]

VARIABLE_UI = "MLFLOW_UI_URL"
UI_POR_DEFECTO = "http://127.0.0.1:5000"
HORAS_POR_DEFECTO = 24
HORAS_MAXIMAS = 720

# Una declinación sin causa utilizable se agrega bajo esta clave, para que el
# desglose (SPEC-027) nunca mezcle «sin dato» con una causa real del catálogo.
SIN_CAUSA = "sin_causa"
_CAUSAS_VACIAS = {"", "ninguna"}

_MENSAJE_DESACTIVADO = (
    "El seguimiento está desactivado: activa MLFLOW y vuelve a intentarlo."
)
_LARGO_MAXIMO_ERROR = 300
# El mensaje de error nunca puede arrastrar las credenciales del URI del usuario.
_PATRON_CREDENCIALES = re.compile(r"(?P<esquema>[A-Za-z][A-Za-z0-9+.\-]*://)[^/\s@]+@")


class SeguimientoNoDisponible(RuntimeError):
    """El backend de seguimiento está desactivado o no se pudo consultar."""


def _texto(valor: Any) -> str | None:
    """Texto no vacío o ``None``: nunca se inventan valores ausentes."""
    if valor is None:
        return None
    limpio = str(valor).strip()
    return limpio or None


def _medida(valor: Any) -> float | None:
    """Número finito o ``None`` (descarta ausentes y no numéricos)."""
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def _en_ms(momento: datetime) -> float:
    return momento.timestamp() * 1000.0


def _en_ventana(inicio_ms: Any, desde_ms: float, hasta_ms: float) -> bool:
    """``True`` si la corrida cae en ``[desde, hasta]`` (ambos extremos incluidos).

    Una fila sin ``start_time`` se conserva: MLflow siempre publica la marca y
    descartarla ocultaría corridas, cosa que la comparación con MLflow prohíbe.
    """
    momento = _medida(inicio_ms)
    if momento is None:
        return True
    return desde_ms <= momento <= hasta_ms


def _sin_credenciales(error: Exception) -> str:
    """Texto del error sin el userinfo del URI (usuario:contraseña@host)."""
    texto = _PATRON_CREDENCIALES.sub(r"\g<esquema>", str(error))
    return texto[:_LARGO_MAXIMO_ERROR] or type(error).__name__


def lectura(corrida: Any) -> dict:
    """Normaliza una corrida de MLflow (``Run`` de ``search_runs``) a una fila plana.

    Sólo se copian los campos que el panorama necesita para agregar por causa,
    familia y prompt; los ausentes quedan en ``None``. No se propaga el id de la
    corrida ni ningún texto de la solicitud (RNF-3).
    """
    datos = getattr(corrida, "data", None)
    info = getattr(corrida, "info", None)
    etiquetas = getattr(datos, "tags", None) or {}
    medidas = getattr(datos, "metrics", None) or {}
    parametros = getattr(datos, "params", None) or {}
    return {
        "estado": _texto(etiquetas.get("estado")),
        "causa": _texto(etiquetas.get("causa_declinacion")),
        "latencia_ms": _medida(medidas.get("latencia_ms")),
        "costo_usd": _medida(medidas.get("costo_usd")),
        "familia": _texto(parametros.get("familia")),
        "prompt": _texto(parametros.get("prompt")),
        "inicio_ms": _medida(getattr(info, "start_time", None)),
    }


def leer_corridas(
    configuracion: seguimiento.Configuracion,
    *,
    desde: datetime,
    hasta: datetime,
) -> list[dict]:
    """Corridas del experimento de generación dentro de ``[desde, hasta]``.

    Cualquier fallo de MLflow (desactivado, experimento inexistente, servidor
    caído) se reporta como `SeguimientoNoDisponible` con un mensaje en español que
    no incluye credenciales ni el userinfo del URI. ``desde`` y ``hasta`` deben ser
    fechas con zona horaria (el panorama usa siempre UTC).
    """
    if not configuracion.activo:
        raise SeguimientoNoDisponible(_MENSAJE_DESACTIVADO)
    desde_ms = _en_ms(desde)
    hasta_ms = _en_ms(hasta)
    try:
        seguimiento._preparar_entorno(configuracion)
        from mlflow.tracking import MlflowClient

        cliente = MlflowClient(tracking_uri=configuracion.uri)
        experimento = cliente.get_experiment_by_name(configuracion.experimento_generacion)
        if experimento is None:
            raise SeguimientoNoDisponible(
                "No se encontró el experimento «"
                f"{configuracion.experimento_generacion}» en MLflow: revisa "
                "MLFLOW_EXPERIMENT_NAME y el URI del seguimiento."
            )
        corridas = cliente.search_runs([experimento.experiment_id])
    except SeguimientoNoDisponible:
        raise
    except Exception as exc:  # noqa: BLE001 - toda falla del backend degrada (S6)
        raise SeguimientoNoDisponible(
            "No se pudo leer el seguimiento de MLflow "
            f"({type(exc).__name__}): {_sin_credenciales(exc)}"
        ) from exc
    return [
        lectura(corrida)
        for corrida in corridas
        if _en_ventana(
            getattr(getattr(corrida, "info", None), "start_time", None), desde_ms, hasta_ms
        )
    ]


def _agregar_causas(filas: Iterable[dict], estados: Iterable[str]) -> dict[str, int]:
    """Declinaciones por causa del catálogo (SPEC-027), ordenadas por clave."""
    por_causa: dict[str, int] = {}
    for fila, estado in zip(filas, estados, strict=True):
        if estado != "declinada":
            continue
        causa = _texto(fila.get("causa"))
        clave = SIN_CAUSA if causa is None or causa.lower() in _CAUSAS_VACIAS else causa
        por_causa[clave] = por_causa.get(clave, 0) + 1
    return dict(sorted(por_causa.items()))


def resumir_corridas(
    corridas: list[dict],
    *,
    desde: datetime,
    hasta: datetime,
    motivo: str | None = None,
) -> dict:
    """Agrega filas normalizadas en la ventana ``[desde, hasta]`` (función pura).

    Con ``motivo`` el panorama se declara degradado: ``disponible`` es ``False`` y
    los agregados quedan vacíos, para que la UI muestre el motivo sin romperse.
    Nunca incluye textos, usuarios ni ids de corrida (RNF-3). ``desde`` y ``hasta``
    deben ser fechas con zona horaria (el panorama usa siempre UTC).
    """
    disponible = motivo is None
    desde_ms = _en_ms(desde)
    hasta_ms = _en_ms(hasta)
    filas = (
        [fila for fila in corridas if _en_ventana(fila.get("inicio_ms"), desde_ms, hasta_ms)]
        if disponible
        else []
    )
    estados = [(_texto(fila.get("estado")) or "").lower() for fila in filas]
    latencias = [
        numero for fila in filas if (numero := _medida(fila.get("latencia_ms"))) is not None
    ]
    costos = [numero for fila in filas if (numero := _medida(fila.get("costo_usd"))) is not None]
    return {
        "disponible": disponible,
        "motivo": motivo,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "solicitudes": len(filas),
        "entregadas": sum(1 for estado in estados if estado == "entregada"),
        "declinadas": sum(1 for estado in estados if estado == "declinada"),
        "errores": sum(1 for estado in estados if estado == "error"),
        "declinaciones_por_causa": _agregar_causas(filas, estados),
        "latencia_media_ms": round(sum(latencias) / len(latencias), 1) if latencias else None,
        "costo_usd": round(float(sum(costos)), 6),
        "mlflow_ui": (os.environ.get(VARIABLE_UI) or "").strip() or UI_POR_DEFECTO,
        "generado_en": datetime.now(UTC).isoformat(),
    }


def panorama(
    configuracion: seguimiento.Configuracion,
    *,
    horas: int = HORAS_POR_DEFECTO,
) -> dict:
    """Panorama de las últimas ``horas`` (1..`HORAS_MAXIMAS`); nunca lanza por el backend.

    Un ``horas`` fuera de rango es un error del llamador y se reporta con
    `ValueError`; en cambio, si el seguimiento está desactivado o MLflow falla se
    devuelve el panorama degradado (S6/AC2).
    """
    if (
        not isinstance(horas, int)
        or isinstance(horas, bool)
        or not 1 <= horas <= HORAS_MAXIMAS
    ):
        raise ValueError(
            f"«horas» debe ser un entero entre 1 y {HORAS_MAXIMAS}; se recibió {horas!r}."
        )
    hasta = datetime.now(UTC)
    desde = hasta - timedelta(hours=horas)
    try:
        corridas = leer_corridas(configuracion, desde=desde, hasta=hasta)
    except SeguimientoNoDisponible as exc:
        motivo = str(exc) or "el seguimiento no está disponible"
    except Exception as exc:  # noqa: BLE001 - el panorama nunca rompe la respuesta (S6)
        motivo = f"No se pudo consultar el seguimiento de MLflow ({type(exc).__name__})."
    else:
        return resumir_corridas(corridas, desde=desde, hasta=hasta)
    return resumir_corridas([], desde=desde, hasta=hasta, motivo=motivo)
