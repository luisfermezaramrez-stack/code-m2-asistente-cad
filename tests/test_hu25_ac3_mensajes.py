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
