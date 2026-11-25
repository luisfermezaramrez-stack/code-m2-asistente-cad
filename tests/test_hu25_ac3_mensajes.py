"""HU-25 / SPEC-026 AC3: 401 y 402 conservan mensajes y no se reintentan.

Sin red, DeepSeek, GPU ni consumo de tokens. Ejecutar con
PYTHONPATH="src:vendor/constraint-kit" y pytest + httpx.
"""

from unittest.mock import Mock

import httpx
import pytest

from m2_cad import llm_resiliente, pipeline


@pytest.mark.parametrize("codigo", [401, 402])
def test_ac3_mensaje_espanol_y_cero_reintentos(monkeypatch, codigo):
    url = "https://proveedor-simulado.invalid/chat/completions"
    solicitud = httpx.Request("POST", url)
    respuesta = httpx.Response(codigo, request=solicitud)
    error = httpx.HTTPStatusError(f"HTTP {codigo}", request=solicitud, response=respuesta)
    proveedor = Mock(side_effect=error)

    monkeypatch.setattr(pipeline.llm, "base_url", lambda rol: url)
    monkeypatch.setattr(pipeline.llm, "planner_model", lambda: "modelo-simulado")
    monkeypatch.setattr(pipeline.llm, "chat", proveedor)
    monkeypatch.setenv("LLM_MAX_RETRIES", "2")
    monkeypatch.setenv("LLM_RETRY_BASE_SECONDS", "0")
    monkeypatch.setenv("LLM_CACHE_TTL_SECONDS", "0")

    with pytest.raises(pipeline.ModeloNoDisponible) as excinfo:
        pipeline._respuesta_modelo("placa de prueba")

    assert str(excinfo.value) == pipeline.MENSAJES_HTTP[codigo]
    assert proveedor.call_count == 1
    assert llm_resiliente.metricas_actuales()["llm_reintentos"] == 0


def _simular_modelo(monkeypatch, proveedor, *, url="https://proveedor-simulado.invalid"):
    monkeypatch.setattr(pipeline.llm, "base_url", lambda rol: f"{url}/chat/completions")
    monkeypatch.setattr(pipeline.llm, "planner_model", lambda: "modelo-simulado")
    monkeypatch.setattr(pipeline.llm, "chat", proveedor)
    monkeypatch.setenv("LLM_RETRY_BASE_SECONDS", "0")


def test_respuesta_invalida_no_se_cachea(monkeypatch):
    """Revisión 2: un JSON truncado no se reutiliza desde la caché."""
    respuesta = {
        "model": "modelo-simulado",
        "choices": [{"message": {"content": "esto no es json"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }
    proveedor = Mock(return_value=respuesta)
    _simular_modelo(monkeypatch, proveedor)
    monkeypatch.setenv("LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("LLM_CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("LLM_CACHE_MAX_ITEMS", "256")

    for _ in range(2):
        with pytest.raises(pipeline.ErrorGeneracion):
            pipeline._respuesta_modelo("placa de prueba")

    assert proveedor.call_count == 2
    assert len(llm_resiliente._CACHE) == 0


def test_configuracion_invalida_se_informa_como_modelo_no_disponible(monkeypatch):
    """Revisión 4: un valor inválido no termina en un 500 opaco."""
    proveedor = Mock()
    _simular_modelo(monkeypatch, proveedor)
    monkeypatch.setenv("LLM_MAX_RETRIES", "abc")

    with pytest.raises(pipeline.ModeloNoDisponible, match="LLM_MAX_RETRIES"):
        pipeline._respuesta_modelo("placa de prueba")

    proveedor.assert_not_called()


def test_cancelacion_detiene_antes_de_llamar_al_proveedor(monkeypatch):
    """Revisión 3: el control SSE llega hasta el bucle de reintentos."""
    from m2_cad.control import ControlGeneracion, GeneracionCancelada

    proveedor = Mock()
    _simular_modelo(monkeypatch, proveedor)
    control = ControlGeneracion(lambda etapa: None)
    control.cancelacion.set()

    with pytest.raises(GeneracionCancelada):
        pipeline._respuesta_modelo("placa de prueba", control=control)

    proveedor.assert_not_called()


def test_timeout_menciona_el_plazo_total(monkeypatch):
    """Revisión 1: el mensaje refleja el plazo global, no el de un intento."""
    proveedor = Mock(side_effect=httpx.ReadTimeout("timeout"))
    _simular_modelo(monkeypatch, proveedor)
    monkeypatch.setenv("LLM_MAX_RETRIES", "0")
    monkeypatch.setattr(pipeline, "TIEMPO_ESPERA_LLM", 7.0)

    with pytest.raises(pipeline.ModeloNoDisponible, match="plazo total de 7 s"):
        pipeline._respuesta_modelo("placa de prueba")
