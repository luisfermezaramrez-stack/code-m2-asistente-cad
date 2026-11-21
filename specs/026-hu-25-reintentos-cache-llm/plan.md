# SPEC-026 — HU-25 · Plan técnico

Issue: #85 · Rama: `feature/hu-25-reintentos-cache-llm` · Destino PR: `main`.

## Alcance y diseño

- Implementar `src/m2_cad/llm_resiliente.py` alrededor de `llm.chat`; **no** modificar `vendor/constraint-kit`.
- Reintentos para HTTP 5xx y `httpx.TransportError` (conexión/timeout). Default: 2 reintentos adicionales, backoff exponencial con jitter y límite de espera. **HTTP 429 y demás 4xx sin reintento**; mantener mensajes de `MENSAJES_HTTP`.
- Caché **en memoria del proceso**, TTL predeterminado 1800 s y máximo 256 entradas; llave SHA-256 de endpoint, prompt, modelo y parámetros de generación. Sin persistencia ni API keys/cabeceras. Una respuesta recuperada de caché informa `usage={}` para no imputar costos nuevos.
- Observabilidad por solicitud: `llm_reintentos`, `llm_cache_hit`, `llm_cache_miss` añadidos a MLflow en `api.medir_solicitud`; aislamiento entre trabajos mediante `ContextVar`.
- Los errores de red agotan reintentos antes de traducirse a `ModeloNoDisponible`; 401/402/429 conservan los mensajes actuales. **Sin cambios** en SSE/JSON ni en la geometría CAD.
- No incluye deduplicación de solicitudes simultáneas ni control de presupuesto por cliente (HU-32). La caché no asegura idempotencia entre procesos o reinicios.

## Configuración

| Variable | Default | Descripción |
|---|---:|---|
| `LLM_MAX_RETRIES` | 2 | Reintentos adicionales (0–5) |
| `LLM_RETRY_BASE_SECONDS` | 0.25 | Base de espera exponencial |
| `LLM_RETRY_MAX_SECONDS` | 3 | Espera máxima de cada reintento |
| `LLM_CACHE_TTL_SECONDS` | 1800 | TTL en segundos (0 desactiva caché) |
| `LLM_CACHE_MAX_ITEMS` | 256 | Capacidad LRU (0 desactiva caché) |

## Pruebas y evidencia

- Simular proveedor: 503→200, timeout, conexión caída, 401/402/429, caché hit/miss, cambio de parámetros y TTL vencido.
- Sin red, API key ni GPU: `PYTHONPATH=src uv run --no-project --with pytest --with httpx python -m pytest tests/test_hu25_resiliencia.py -q`.
- Revisar Ruff, pruebas del backend en entorno soportado, métricas MLflow y regresión completa antes de PR; documentar evidencias reales.
