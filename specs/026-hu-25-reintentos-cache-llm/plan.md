# SPEC-026 — HU-25 · Plan técnico

Issue: #85 · Rama: `feature/hu-25-reintentos-cache-llm` · Destino PR: `main`.

## Alcance y diseño

- Implementar `src/m2_cad/llm_resiliente.py` alrededor de `llm.chat`; **no** modificar `vendor/constraint-kit`.
- Reintentos sólo para **HTTP 500, 502, 503 y 504** y `httpx.TransportError`
  (conexión/timeout). Default: 2 reintentos adicionales, backoff exponencial con jitter y
  límite de espera. **Todos los 4xx y los 5xx permanentes (501, 505) sin reintento**;
  mantener mensajes de `MENSAJES_HTTP`.
- El `timeout` de `consultar` es un **plazo total** para todos los intentos: cada intento
  recibe el tiempo restante y el backoff se recorta al mismo plazo. El mensaje de
  `ModeloNoDisponible` informa ese plazo global, no uno por intento.
- Caché **en memoria del proceso**, TTL predeterminado 1800 s y máximo 256 entradas;
  llave SHA-256 de endpoint, prompt, modelo, parámetros de generación y **huella no
  reversible de la credencial activa**. Sin persistencia ni API keys/cabeceras. Una
  respuesta recuperada de caché informa `usage={}` para no imputar costos nuevos.
- La caché sólo se escribe después de que `_programa_de` extrae el programa. Una salida
  truncada o inválida no se almacena y no se reutiliza durante el TTL.
- Cancelación cooperativa: `generar_pieza` pasa `ControlGeneracion.comprobar_cancelacion`
  a `consultar`; se comprueba antes de cada intento y en tramos de 50 ms durante el
  backoff. Un trabajo SSE cancelado no inicia otra llamada paga.
- Configuración inválida: `ConfiguracionInvalida` (subclase de `ValueError`) se traduce en
  `pipeline._respuesta_modelo` a `ModeloNoDisponible` (503) con el nombre de la variable.
- Observabilidad por solicitud: `llm_reintentos`, `llm_cache_hit`, `llm_cache_miss`
  añadidos a MLflow en `api.medir_solicitud`; aislamiento entre trabajos mediante
  `ContextVar`. En la ruta de error sólo se registran esas claves: no se escriben tokens
  ni `costo_usd` en 0, para no distorsionar los promedios.
- Los errores de red agotan reintentos o plazo antes de traducirse a
  `ModeloNoDisponible`; 401/402/429 conservan los mensajes actuales. La ruta SSE mantiene
  su mensaje 503 genérico para no filtrar URLs ni credenciales del proveedor.
- No incluye deduplicación de solicitudes simultáneas ni control de presupuesto por
  cliente (HU-32). La caché no asegura idempotencia entre procesos o reinicios.

## Configuración

| Variable | Default | Descripción |
|---|---:|---|
| `LLM_MAX_RETRIES` | 2 | Reintentos adicionales (0–5) |
| `LLM_RETRY_BASE_SECONDS` | 0.25 | Base de espera exponencial (0–30) |
| `LLM_RETRY_MAX_SECONDS` | 3 | Espera máxima de cada reintento (0–120) |
| `LLM_CACHE_TTL_SECONDS` | 1800 | TTL en segundos (0 desactiva caché) |
| `LLM_CACHE_MAX_ITEMS` | 256 | Capacidad LRU (0 desactiva caché) |

El plazo total no es configurable por entorno: `pipeline.TIEMPO_ESPERA_LLM = 120.0` s se
reparte entre todos los intentos.

## Pruebas y evidencia

- Simular proveedor: 503→200, 500/502/504, 501/505 sin reintento, timeout, conexión caída,
  401/402/429, caché hit/miss, cambio de parámetros, TTL vencido, credencial rotada,
  validador que rechaza la respuesta y cancelación antes/durante el backoff.
- Sin red, API key ni GPU: `uv run --no-sync pytest tests/test_hu25_resiliencia.py tests/test_hu25_ac3_mensajes.py -q`.
- Verificar el mensaje de plazo total, la traducción de configuración inválida a 503 y que
  un fallo del LLM no registra tokens/costo en MLflow
  (`tests/test_api_seguimiento.py::test_fallo_del_llm_no_registra_tokens_ni_costo_en_cero`).
- Revisar Ruff, regresión completa y cobertura antes de PR; documentar evidencias reales en
  `evidence.md`.
