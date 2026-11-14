"""Seguimiento de experimentos con MLflow (HU-16 · specs/009-hu-16-mlflow).

Observabilidad best-effort: si MLflow no está disponible o el seguimiento está
desactivado con ``MLFLOW_TRACKING_ENABLED=0``, la generación concluye igual y el
fallo se emite como advertencia en el log (AC6). Nada de lo registrado aquí es
fuente de verdad de la pieza.
"""

from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from constraint_kit import llm

from m2_cad.registro import _sanitizar

logger = logging.getLogger(__name__)

EXPERIMENTO_GENERACION = "m2-cad-generacion"
EXPERIMENTO_BANCO = "m2-cad-banco"
URI_PREDETERMINADA = "file:./mlruns"

# La sobrecarga del seguimiento debe ser ≤ 50 ms p95 con backend local (AC6):
# sin reintentos del cliente HTTP y con timeout corto para un servidor caído.
_TIMEOUT_HTTP_S = "2"
_REINTENTOS_HTTP = "0"
_LARGO_MAXIMO_TEXTO = 5000
_VALORES_INACTIVOS = {"0", "false", "no", "off"}
_PATRON_NOMBRE_INVALIDO = re.compile(r"[^A-Za-z0-9._-]+")
# Versiones ya registradas por (uri, nombre de modelo, versión): evita buscar en
# cada solicitud y mantiene la sobrecarga local por debajo del AC6.
_versiones_registradas: dict[tuple[str, str, str], str] = {}


def _texto(valor: Any) -> str:
    """Sanitiza el texto antes de registrarlo (AC5) y acota su largo."""
    return _sanitizar(str(valor))[:_LARGO_MAXIMO_TEXTO]


def _es_escalar(valor: Any) -> bool:
    return isinstance(valor, (str, int, float, bool)) and not isinstance(valor, complex)


def _metrica(valor: Any) -> float | None:
    """Convierte a float descartando None, no numéricos y no finitos."""
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def version_modelo() -> str:
    """Identificador de la configuración servida (AC7).

    ``LLM_MODEL_VERSION`` cuando el proveedor publica una versión concreta (por
    ejemplo el digest del GGUF de la línea base); si no, el id del modelo servido.
    Nunca devuelve ``desconocida``.
    """
    return os.environ.get("LLM_MODEL_VERSION") or llm.planner_model()


def costo_usd(
    tokens_entrada: int | float | None,
    tokens_salida: int | float | None,
    *,
    precio_entrada: float = 0.0,
    precio_salida: float = 0.0,
) -> float:
    """Costo en USD con precios por millón de tokens."""
    entrada = float(tokens_entrada or 0)
    salida = float(tokens_salida or 0)
    return (entrada * precio_entrada + salida * precio_salida) / 1_000_000


@dataclass(frozen=True)
class Configuracion:
    """Configuración efectiva del seguimiento, leída del entorno."""

    uri: str = URI_PREDETERMINADA
    activo: bool = True
    precio_entrada: float = 0.0
    precio_salida: float = 0.0
    experimento_generacion: str = EXPERIMENTO_GENERACION
    experimento_banco: str = EXPERIMENTO_BANCO

    @property
    def es_archivo(self) -> bool:
        return self.uri.startswith("file:")

    @classmethod
    def desde_entorno(cls, entorno: Mapping[str, str] | None = None) -> Configuracion:
        env = os.environ if entorno is None else entorno
        activo = env.get("MLFLOW_TRACKING_ENABLED", "1").strip().lower()
        return cls(
            uri=(env.get("MLFLOW_TRACKING_URI") or URI_PREDETERMINADA).strip(),
            activo=activo not in _VALORES_INACTIVOS,
            precio_entrada=float(env.get("MLFLOW_PRECIO_ENTRADA") or 0.0),
            precio_salida=float(env.get("MLFLOW_PRECIO_SALIDA") or 0.0),
            experimento_generacion=(
                env.get("MLFLOW_EXPERIMENT_NAME") or EXPERIMENTO_GENERACION
            ).strip(),
            experimento_banco=(env.get("MLFLOW_EXPERIMENT_BANCO") or EXPERIMENTO_BANCO).strip(),
        )


def _preparar_entorno(configuracion: Configuracion) -> None:
    """Fija los defaults del cliente antes de importar mlflow."""
    if configuracion.es_archivo:
        # MLflow 3.x bloquea el file store salvo opt-out explícito.
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", _TIMEOUT_HTTP_S)
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", _REINTENTOS_HTTP)
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    logging.getLogger("mlflow").setLevel(logging.WARNING)


class Corrida:
    """Una corrida de MLflow; se vuelve no-op si algo falla."""

    def __init__(
        self,
        experimento: str,
        *,
        nombre: str | None = None,
        tags: Mapping[str, Any] | None = None,
        anidada: bool = False,
        configuracion: Configuracion | None = None,
    ) -> None:
        self.configuracion = configuracion or Configuracion.desde_entorno()
        self.experimento = experimento
        self.nombre = nombre
        self.anidada = anidada
        self.tags_iniciales = dict(tags or {})
        self.id: str | None = None
        self.activa = False
        self.fallos = 0
        self._mlflow: Any = None
        self._cliente: Any = None

    # -- ciclo de vida ---------------------------------------------------
    def abrir(self) -> Corrida:
        if not self.configuracion.activo:
            return self
        try:
            _preparar_entorno(self.configuracion)
            import mlflow
            from mlflow.tracking import MlflowClient

            self._mlflow = mlflow
            mlflow.set_tracking_uri(self.configuracion.uri)
            self._cliente = MlflowClient(tracking_uri=self.configuracion.uri)
            experimento = mlflow.set_experiment(self.experimento)
            corrida = mlflow.start_run(
                experiment_id=experimento.experiment_id,
                run_name=_texto(self.nombre) if self.nombre else None,
                nested=self.anidada,
                tags={clave: _texto(valor) for clave, valor in self.tags_iniciales.items()},
            )
            self.id = corrida.info.run_id
            self.activa = True
        except Exception as exc:  # noqa: BLE001 - el seguimiento nunca rompe la respuesta
            self._fallo("no se pudo abrir la corrida", exc)
        return self

    def finalizar(
        self,
        *,
        estado: str | None = None,
        motivo_declinacion: str | None = None,
        error: str | None = None,
    ) -> None:
        """Cierra la corrida; nunca queda en RUNNING (AC3)."""
        if not self.activa:
            return
        try:
            self.registrar_tags(
                estado=estado,
                motivo_declinacion=motivo_declinacion,
                error=error,
            )
            self._cerrar("FINISHED")
        except Exception as exc:  # noqa: BLE001
            self._fallo("no se pudo cerrar la corrida", exc)
            self._cerrar("FAILED", silencioso=True)

    def _cerrar(self, status: str, *, silencioso: bool = False) -> None:
        try:
            self._mlflow.end_run(status=status)
        except Exception as exc:  # noqa: BLE001
            if not silencioso:
                self._fallo("no se pudo terminar la corrida", exc)
            try:
                self._cliente.set_terminated(self.id, status=status)
            except Exception as exc2:  # noqa: BLE001
                self._fallo("la corrida quedó sin terminar", exc2)
        finally:
            self.activa = False

    # -- registro -------------------------------------------------------
    def registrar_params(self, **params: Any) -> None:
        escalares = {
            clave: (_texto(valor) if isinstance(valor, str) else valor)
            for clave, valor in params.items()
            if valor is not None and _es_escalar(valor)
        }
        self._operacion(
            "no se pudieron registrar los params",
            lambda: [self._mlflow.log_param(clave, valor) for clave, valor in escalares.items()],
        )

    def registrar_metricas(self, **metricas: Any) -> None:
        numericas = {
            clave: numero
            for clave, valor in metricas.items()
            if (numero := _metrica(valor)) is not None
        }
        self._operacion(
            "no se pudieron registrar las métricas",
            lambda: [self._mlflow.log_metric(clave, numero) for clave, numero in numericas.items()],
        )

    def registrar_tags(self, **tags: Any) -> None:
        limpios = {clave: _texto(valor) for clave, valor in tags.items() if valor is not None}
        if not limpios:
            return
        self._operacion(
            "no se pudieron registrar los tags",
            lambda: [self._mlflow.set_tag(clave, valor) for clave, valor in limpios.items()],
        )

    def registrar_artefactos(self, *rutas: Path | str | None) -> None:
        existentes = [Path(ruta) for ruta in rutas if ruta and Path(ruta).is_file()]
        if not existentes:
            return
        self._operacion(
            "no se pudieron registrar los artefactos",
            lambda: [self._mlflow.log_artifact(str(ruta)) for ruta in existentes],
        )

    # -- internos -------------------------------------------------------
    def _operacion(self, descripcion: str, accion) -> None:
        if not self.activa or self.fallos:
            return
        try:
            accion()
        except Exception as exc:  # noqa: BLE001
            self._fallo(descripcion, exc)

    def _fallo(self, descripcion: str, exc: Exception) -> None:
        self.fallos += 1
        logger.warning("seguimiento: %s (%s: %s)", descripcion, type(exc).__name__, exc)


def iniciar_corrida(
    experimento: str,
    *,
    nombre: str | None = None,
    tags: Mapping[str, Any] | None = None,
    anidada: bool = False,
    configuracion: Configuracion | None = None,
) -> Corrida:
    """Abre una corrida; sin MLflow disponible devuelve una corrida inactiva."""
    return Corrida(
        experimento,
        nombre=nombre,
        tags=tags,
        anidada=anidada,
        configuracion=configuracion,
    ).abrir()


def nombre_modelo_registrado(nombre: str) -> str:
    """Nombre válido para el registro de modelos de MLflow (sin «/» ni rutas)."""
    return _PATRON_NOMBRE_INVALIDO.sub("_", _texto(nombre))


def registrar_version_modelo(
    *,
    nombre: str,
    version: str,
    corrida_id: str | None,
    fuente: str,
    configuracion: Configuracion | None = None,
    descripcion: str = "",
) -> str | None:
    """Registra (una sola vez) la versión de modelo servida y liga la corrida (AC7).

    Devuelve ``nombre/vN`` cuando se pudo registrar; nunca propaga fallos.
    """
    configuracion = configuracion or Configuracion.desde_entorno()
    if not configuracion.activo or not corrida_id:
        return None
    registro = nombre_modelo_registrado(nombre)
    clave = (configuracion.uri, registro, _texto(version))
    if clave in _versiones_registradas:
        return _versiones_registradas[clave]
    try:
        _preparar_entorno(configuracion)
        from mlflow.tracking import MlflowClient

        cliente = MlflowClient(tracking_uri=configuracion.uri)
        for modelo in cliente.search_model_versions(f"name='{registro}'"):
            if (modelo.tags or {}).get("version_modelo") == _texto(version):
                referencia = f"{nombre}/v{modelo.version}"
                _versiones_registradas[clave] = referencia
                return referencia
        try:
            cliente.create_registered_model(registro)
        except Exception:  # noqa: BLE001 - ya existe: continuar
            pass
        nueva = cliente.create_model_version(
            name=registro,
            source=fuente,
            run_id=corrida_id,
            description=_texto(descripcion),
            tags={"version_modelo": _texto(version)},
        )
        referencia = f"{nombre}/v{nueva.version}"
        _versiones_registradas[clave] = referencia
        return referencia
    except Exception as exc:  # noqa: BLE001 - degradación segura (AC6)
        logger.warning(
            "seguimiento: no se registró la versión de modelo (%s: %s)",
            type(exc).__name__,
            exc,
        )
        return None


def configuracion_en(uri: str, **cambios: Any) -> Configuracion:
    """Configuración derivada de ``uri`` y ajustada con ``cambios``."""
    return replace(Configuracion(uri=uri), **cambios)
