"""HU-25: tests unitarios sin red, DeepSeek, GPU ni constraint-kit."""

import time

import httpx
import pytest

from m2_cad import llm_resiliente as servicio


@pytest.fixture(autouse=True)
def limpiar(monkeypatch):
    servicio._CACHE.clear()
    servicio.reiniciar_metricas()
    monkeypatch.setenv("LLM_MAX_RETRIES", "2")
    monkeypatch.setenv("LLM_RETRY_BASE_SECONDS", "0")
    monkeypatch.setenv("LLM_CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("LLM_CACHE_MAX_ITEMS", "256")


def respuesta_modelo():
    return {
        "model": "deepseek-chat",
        "choices": [{"message": {"content": '{"parts":[],"mates":[]}'}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }


def error_http(codigo):
    solicitud = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    respuesta = httpx.Response(codigo, request=solicitud)
    return httpx.HTTPStatusError("error del proveedor", request=solicitud, response=respuesta)


def consultar(proveedor, *, texto="Placa de acero", temperatura=0.1):
    return servicio.consultar(
        {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": texto}],
            "temperature": temperatura,
        },
        url="https://api.deepseek.com/chat/completions",
        timeout=1.0,
        proveedor=proveedor,
    )


def test_ac1_503_luego_200_reintenta_una_vez():
    llamadas = []

    def proveedor(*args, **kwargs):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise error_http(503)
        return respuesta_modelo()

    assert consultar(proveedor)["model"] == "deepseek-chat"
    assert len(llamadas) == 2
    assert servicio.metricas_actuales() == {
        "llm_reintentos": 1,
        "llm_cache_hit": 0,
        "llm_cache_miss": 1,
    }


def test_ac2_cache_evitar_segunda_llamada_y_usage_cero():
    llamadas = []

    def proveedor(*args, **kwargs):
        llamadas.append(1)
        return respuesta_modelo()

    assert consultar(proveedor)["usage"]["prompt_tokens"] == 100
    segunda = consultar(proveedor)
    assert len(llamadas) == 1
    assert segunda["usage"] == {}
    assert segunda["model"] == "deepseek-chat"
    assert servicio.metricas_actuales()["llm_cache_hit"] == 1


@pytest.mark.parametrize("codigo", [400, 401, 402, 404, 429])
def test_ac3_errores_4xx_no_se_reintentan(codigo):
    llamadas = []

    def proveedor(*args, **kwargs):
        llamadas.append(1)
        raise error_http(codigo)

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        consultar(proveedor)
    assert excinfo.value.response.status_code == codigo
    assert len(llamadas) == 1
    assert servicio.metricas_actuales()["llm_reintentos"] == 0


def test_timeout_reintenta_y_termina_con_error():
    llamadas = []

    def proveedor(*args, **kwargs):
        llamadas.append(1)
        raise httpx.ReadTimeout("Timeout")

    with pytest.raises(httpx.ReadTimeout):
        consultar(proveedor)
    assert len(llamadas) == 3
    assert servicio.metricas_actuales()["llm_reintentos"] == 2


def test_fallo_conexion_reintenta_y_recupera():
    llamadas = []

    def proveedor(*args, **kwargs):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise httpx.ConnectError("Desconectado")
        return respuesta_modelo()

    consultar(proveedor)
    assert len(llamadas) == 2


def test_cambio_parametros_o_modelo_no_reutiliza_cache():
    llamadas = []

    def proveedor(*args, **kwargs):
        llamadas.append(1)
        return respuesta_modelo()

    consultar(proveedor, temperatura=0.1)
    consultar(proveedor, temperatura=0.8)
    consultar(proveedor, texto="Otra solicitud")
    assert len(llamadas) == 3


def test_ttl_vencido_obliga_nueva_llamada(monkeypatch):
    llamadas = []
    clock = [time.monotonic()]
    monkeypatch.setattr(servicio.time, "monotonic", lambda: clock[0])

    def proveedor(*args, **kwargs):
        llamadas.append(1)
        return respuesta_modelo()

    consultar(proveedor)
    clock[0] += 61
    consultar(proveedor)
    assert len(llamadas) == 2


def test_cache_no_almacena_api_key_ni_headers():
    def proveedor(*args, **kwargs):
        datos = respuesta_modelo()
        datos["api_key"] = "clave-privada"
        datos["headers"] = {"Authorization": "Bearer privado"}
        return datos

    consultar(proveedor)
    assert len(servicio._CACHE) == 1
    contenido = next(iter(servicio._CACHE.values()))[1]
    assert "api_key" not in contenido
    assert "headers" not in contenido
    assert "Authorization" not in repr(contenido)


def test_configuracion_invalida_falla_sin_llamar_proveedor(monkeypatch):
    monkeypatch.setenv("LLM_MAX_RETRIES", "999")
    with pytest.raises(ValueError, match="LLM_MAX_RETRIES"):
        consultar(lambda *args, **kwargs: respuesta_modelo())
