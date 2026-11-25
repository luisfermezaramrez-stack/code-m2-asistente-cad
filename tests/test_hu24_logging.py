"""HU-24: logging estructurado, correlación y redacción de secretos (SPEC-025).

Las pruebas son offline: la API usa dependencias inyectadas, el pipeline se simula
en los puntos CAD y MLflow queda desactivado. No se requieren GPU ni API keys.
"""

from __future__ import annotations

import json
import logging
import uuid
from io import StringIO
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from m2_cad import api, observabilidad, pipeline, seguimiento
from m2_cad.trabajos import GestorTrabajos

CLAVE_PRUEBA = "sk-clave-sensible-123456789"
CLAVES_JSON = {"nivel", "modulo", "mensaje", "marca_tiempo"}


@pytest.fixture(autouse=True)
def _logging_centralizado(monkeypatch):
    """Cada prueba empieza con la configuración por defecto y la restaura al salir."""
    monkeypatch.delenv("M2_LOG_LEVEL", raising=False)
    observabilidad.configurar_logging()
    yield
    observabilidad.configurar_logging()


@pytest.fixture
def salida_json():
    """Captura las líneas JSON que emitiría la consola del servicio."""
    buffer = StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(observabilidad.JsonFormatter())
    handler.addFilter(observabilidad.ContextoFilter())
    logger = logging.getLogger("m2_cad")
    logger.addHandler(handler)
    try:
        yield buffer
    finally:
        logger.removeHandler(handler)


def _lineas(buffer: StringIO) -> list[dict]:
    return [json.loads(linea) for linea in buffer.getvalue().splitlines() if linea.strip()]


@pytest.fixture
def entorno_json(monkeypatch, tmp_path):
    """API con pipeline simulado y seguimiento apagado; devuelve el id de la corrida."""
    monkeypatch.setenv("LLM_BASE_URL", "http://modelo-simulado")
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "s" * 64)  # HU-36: tokens de descarga.
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )

    def planificador(texto: str) -> dict:
        return {"parts": [{"type": "spacer", "params": {}}], "mates": []}

    def verificar(programa: dict) -> dict:
        return {"declined": False, "ok": True, "n_errors": 0, "diagnostics": []}

    def construir(programa: dict, directorio: Path) -> pipeline.ResultadoPieza:
        pipeline.verificar_programa(programa)
        return pipeline.ResultadoPieza(
            programa=programa,
            step=directorio / "pieza.step",
            glb=directorio / "pieza.glb",
            bom_csv=directorio / "pieza.csv",
            volumen_mm3=100.0,
            caja_mm=(1.0, 1.0, 1.0),
            tiempo_construccion_s=0.01,
            familia="spacer",
        )

    monkeypatch.setattr(
        pipeline, "_planificador_con_uso", lambda medir_uso, control=None: planificador
    )
    monkeypatch.setattr(pipeline.dsl, "check", verificar)
    monkeypatch.setattr(pipeline, "construir_pieza", construir)

    etiquetas: list[dict] = []
    iniciar_real = api.seguimiento.iniciar_corrida

    def capturar(experimento, **argumentos):
        etiquetas.append(dict(argumentos.get("tags") or {}))
        return iniciar_real(experimento, **argumentos)

    monkeypatch.setattr(api.seguimiento, "iniciar_corrida", capturar)
    yield etiquetas
    api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)


@pytest.fixture
def entorno_sse(monkeypatch, tmp_path):
    """API SSE aislada con un gestor propio y seguimiento desactivado."""
    gestor = GestorTrabajos()
    monkeypatch.setenv("M2_DOWNLOAD_SECRET", "s" * 64)  # HU-36: tokens de descarga.
    monkeypatch.setattr(api, "obtener_ruta_registro", lambda: tmp_path / "registro.csv")
    api.app.dependency_overrides[api.obtener_gestor_trabajos] = lambda: gestor
    api.app.dependency_overrides[api.obtener_configuracion_seguimiento] = lambda: (
        seguimiento.Configuracion(activo=False)
    )
    yield gestor
    api.app.dependency_overrides.pop(api.obtener_gestor_trabajos, None)
    api.app.dependency_overrides.pop(api.obtener_configuracion_seguimiento, None)
    api.app.dependency_overrides.pop(api.obtener_procesador_sse, None)


def test_ac2_json_valido_con_claves_obligatorias(salida_json, monkeypatch):
    """AC2 y RF-1: cada línea es JSON con nivel, módulo, mensaje y marca de tiempo."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", CLAVE_PRUEBA)
    logging.getLogger("m2_cad.prueba").info("evento %s", "simple")
    registro = _lineas(salida_json)[-1]

    assert CLAVES_JSON <= set(registro)
    assert registro["nivel"] == "INFO"
    assert registro["modulo"] == "m2_cad.prueba"
    assert registro["mensaje"] == "evento simple"
    assert registro["marca_tiempo"].endswith("+00:00")

    logging.getLogger("m2_cad.prueba").info(
        "evento estructurado",
        extra={"datos": {"etapa": "validando", "clave": CLAVE_PRUEBA}},
    )
    estructurado = _lineas(salida_json)[-1]
    assert estructurado["detalles"]["etapa"] == "validando"
    assert CLAVE_PRUEBA not in json.dumps(estructurado)


def test_ac2_el_formateador_redacta_secretos(monkeypatch):
    """AC3: la redacción se aplica también al mensaje del registro."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", CLAVE_PRUEBA)
    registro = logging.LogRecord(
        "m2_cad.prueba",
        logging.ERROR,
        __file__,
        1,
        "Authorization: Bearer %s",
        (CLAVE_PRUEBA,),
        None,
    )
    lineas = observabilidad.JsonFormatter().format(registro)

    assert CLAVE_PRUEBA not in lineas
    assert "Bearer" not in lineas
    assert "[REDACTADO]" in lineas


def test_ac1_reconstruccion_por_request_id(entorno_json, caplog, salida_json):
    """AC1: entrada, etapas, resultado y cierre comparten id y etiquetan MLflow."""
    identificador = uuid.uuid4().hex
    with caplog.at_level(logging.INFO, logger="m2_cad"):
        with TestClient(api.app) as client:
            respuesta = client.post(
                "/generar",
                json={"texto": "Espaciador de 14 mm"},
                headers={"X-Request-ID": identificador},
            )

    assert respuesta.status_code == 200
    mensajes = [
        registro.getMessage()
        for registro in caplog.records
        if getattr(registro, "request_id", None) == identificador
    ]
    assert any(mensaje == "solicitud recibida: POST /generar" for mensaje in mensajes)
    for etapa in (
        "pipeline: validando solicitud",
        "pipeline: generando programa",
        "pipeline: programa generado",
        "pipeline: catálogo validado",
        "pipeline: programa verificado",
        "pipeline: pieza construida (spacer)",
        "seguimiento: cerrando corrida (entregada)",
        "solicitud entregada",
    ):
        assert etapa in mensajes
    assert mensajes.index("solicitud recibida: POST /generar") < mensajes.index(etapa)
    assert entorno_json[0]["request_id"] == identificador
    assert entorno_json[0]["solicitud_id"] == identificador
    assert all(linea["request_id"] == identificador for linea in _lineas(salida_json))


def test_ac3_error_del_proveedor_no_filtra_la_clave(monkeypatch, caplog):
    """AC3: el cuerpo del error con Authorization se registra redactado."""
    monkeypatch.setenv("LLM_BASE_URL", "http://modelo-simulado")
    monkeypatch.setenv("DEEPSEEK_API_KEY", CLAVE_PRUEBA)
    respuesta_http = httpx.Response(
        401,
        text=f'{{"error": "Authorization: Bearer {CLAVE_PRUEBA}"}}',
        request=httpx.Request("POST", "http://modelo-simulado"),
    )

    def chat_falso(*argumentos, **kwargs):
        raise httpx.HTTPStatusError("401", request=respuesta_http.request, response=respuesta_http)

    monkeypatch.setattr(pipeline.llm, "chat", chat_falso)
    with caplog.at_level(logging.WARNING, logger="m2_cad"):
        with pytest.raises(pipeline.ModeloNoDisponible):
            pipeline._respuesta_modelo("Espaciador de 14 mm")

    texto = "\n".join(registro.getMessage() for registro in caplog.records)
    assert CLAVE_PRUEBA not in texto
    assert "Authorization: Bearer" not in texto
    assert "[REDACTADO]" in texto


def test_rf5_request_id_valido_se_reutiliza(entorno_json, salida_json):
    """RF-5: un X-Request-ID UUID válido se usa como request_id y en la respuesta."""
    identificador = uuid.uuid4().hex
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar",
            json={"texto": "Espaciador de 14 mm"},
            headers={"X-Request-ID": identificador},
        )

    assert respuesta.headers["X-Registro-ID"] == identificador
    assert all(linea["request_id"] == identificador for linea in _lineas(salida_json))


@pytest.mark.parametrize("cabecera", [None, "no-es-un-uuid", ""])
def test_rf5_request_id_invalido_o_ausente_se_genera(entorno_json, salida_json, cabecera):
    """RF-5: sin cabecera válida se genera un UUID nuevo por solicitud."""
    cabeceras = {} if cabecera is None else {"X-Request-ID": cabecera}
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar", json={"texto": "Espaciador de 14 mm"}, headers=cabeceras
        )

    generado = respuesta.headers["X-Registro-ID"]
    assert uuid.UUID(generado).hex == generado
    assert all(linea["request_id"] == generado for linea in _lineas(salida_json))


def test_rf2_hilo_sse_conserva_request_id_y_job_id(entorno_sse, salida_json):
    """RF-2: los registros del trabajo SSE llevan ambos ids de correlación."""
    identificador = uuid.uuid4().hex

    def generar(texto, control):
        control.informar("validando")
        control.informar("generando")
        logging.getLogger("m2_cad.pipeline").info("pipeline: fase SSE")
        return {"resultado": "generada"}

    api.app.dependency_overrides[api.obtener_procesador_sse] = lambda: (
        lambda texto, control, medicion=None: generar(texto, control)
    )
    with TestClient(api.app) as client:
        respuesta = client.post(
            "/generar",
            json={"texto": "Pieza de prueba"},
            headers={"Accept": "text/event-stream", "X-Request-ID": identificador},
        )

    trabajo_id = respuesta.headers["X-Solicitud-ID"]
    lineas = [linea for linea in _lineas(salida_json) if linea.get("request_id") == identificador]
    assert lineas
    assert any(
        linea.get("job_id") == trabajo_id and "trabajo SSE creado" in linea["mensaje"]
        for linea in lineas
    )
    assert any(
        linea.get("job_id") == trabajo_id and "fase SSE" in linea["mensaje"] for linea in lineas
    )


def test_rnf3_nivel_configurable_por_variable(monkeypatch):
    """RNF-3: M2_LOG_LEVEL fija el nivel; un valor inválido cae a INFO."""
    monkeypatch.setenv("M2_LOG_LEVEL", "debug")
    observabilidad.configurar_logging()
    assert logging.getLogger("m2_cad").level == logging.DEBUG

    monkeypatch.setenv("M2_LOG_LEVEL", "ruido")
    observabilidad.configurar_logging()
    assert logging.getLogger("m2_cad").level == logging.INFO
