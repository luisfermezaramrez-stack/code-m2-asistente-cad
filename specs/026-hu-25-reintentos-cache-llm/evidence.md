# HU-25 — Evidencias de implementación

**Fecha:** 24 de noviembre de 2026

**Issue:** #85

**Especificación:** SPEC-026

**Rama:** `feature/hu-25-reintentos-cache-llm`

**PR:** #126

## 1. Implementación

Se incorporaron mecanismos de resiliencia para las llamadas al modelo LLM:

- Reintentos sólo ante errores transitorios: HTTP 500, 502, 503 y 504, timeout y fallo de
  conexión.
- Espera progresiva entre intentos (*exponential backoff* con jitter) acotada por un
  **plazo total** compartido.
- Caché de respuestas con TTL y capacidad configurables.
- Todos los 4xx (401, 402, 429, …) y los 5xx permanentes (501, 505) sin reintento.
- Registro de métricas de reintentos, aciertos y fallos de caché.
- Consumo facturable cero cuando se reutiliza una respuesta almacenada.

## 2. Correcciones de la revisión del PR #126

| Punto | Corrección | Prueba que lo cubre |
|---|---|---|
| 1. Timeout multiplicado | `consultar` usa un plazo total; cada intento recibe el tiempo restante y el backoff se recorta al plazo. El mensaje dice «plazo total». | `test_plazo_total_limita_los_reintentos`, `test_timeout_menciona_el_plazo_total`, `test_timeout_reintenta_y_termina_con_error` |
| 2. Caché con respuestas inválidas | `consultar` recibe `validador=_programa_de`; sólo cachea si la extracción tiene éxito. | `test_cache_no_guarda_respuesta_rechazada_por_validador`, `test_respuesta_invalida_no_se_cachea` |
| 3. Cancelación ignorada | `ControlGeneracion.comprobar_cancelacion` llega a `consultar`; se comprueba antes de cada intento y cada 50 ms durante el backoff. | `test_cancelacion_detiene_los_reintentos`, `test_cancelacion_antes_del_primer_intento_no_llama_proveedor`, `test_cancelacion_detiene_antes_de_llamar_al_proveedor` |
| 4. Configuración inválida → 500 | `ConfiguracionInvalida` se traduce a `ModeloNoDisponible` (503) con la variable afectada. | `test_configuracion_invalida_falla_sin_llamar_proveedor`, `test_configuracion_invalida_se_informa_como_modelo_no_disponible` |
| 5. Tokens en 0 en corridas fallidas | En error sólo se registran `llm_*`; no se escriben tokens ni `costo_usd` cuando no hay `usage`. | `test_fallo_del_llm_no_registra_tokens_ni_costo_en_cero` |
| 6. 5xx permanentes reintentados | Lista explícita `{500, 502, 503, 504}`; 501 y 505 no se reintentan. | `test_errores_no_transitorios_no_se_reintentan[501/505]`, `test_5xx_transitorios_se_reintentan` |
| 7. Clave de caché sin credencial | La clave incluye una huella SHA-256 de la credencial activa; la clave en claro nunca se almacena. | `test_cache_distingue_credencial_sin_guardarla`, `test_cache_no_almacena_api_key_ni_headers` |
| 8. Documentación inconsistente | `spec.md`, `plan.md`, `tasks.md` y este `evidence.md` describen el comportamiento real: todos los 4xx y 501/505 sin reintento; regresión y métricas verificadas. | Revisión de los cuatro documentos |

## 3. Validaciones realizadas

Entorno local: macOS x86_64, Python 3.12.13, `uv` 0.13.2. Las dependencias se instalaron
con `uv sync --locked --dev --no-install-package nlopt --no-install-package
llama-cpp-python`; como `nlopt==2.11.0` no publica wheel para macOS x86_64, se instaló
localmente `nlopt==2.9.1` con `uv pip`. La CI usa el lock completo (`nlopt==2.11.0`) en
Linux, que es la referencia reproducible.

| Validación | Comando | Resultado |
|---|---|---|
| Ruff lint | `uv run --no-sync ruff check src tests` | Sin errores |
| Ruff format | `uv run --no-sync ruff format --check src tests` | 46 archivos ya formateados |
| Pruebas HU-25 | `uv run --no-sync pytest tests/test_hu25_resiliencia.py tests/test_hu25_ac3_mensajes.py -q` | **29 aprobadas** |
| Seguimiento MLflow | `uv run --no-sync pytest tests/test_api_seguimiento.py -q` | **10 aprobadas** |
| Regresión completa | `uv run --no-sync pytest -q` | **404 aprobadas**, 0 fallidas |
| Cobertura | `uv run --no-sync pytest --cov=src/m2_cad --cov-report=term-missing -q` | **94,00 %** total; **92 %** en `llm_resiliente.py` |
| `git diff --check` | `git diff --check` | Sin errores |

La regresión se repitió tras integrar `main` (HU-27, HU-30 y HU-36) en la rama. Para
ejecutarla localmente hace falta `M2_DOWNLOAD_SECRET` (HU-36) y las dependencias de
`frontend/` para los tests de tipos OpenAPI (HU-27); la CI las prepara en sus pasos
previos. La CI de GitHub Actions quedó en verde sobre el commit de integración
`5bdb7f0`.

## 4. Integración con MLflow

Se verificó con el file store temporal de `tests/test_api_seguimiento.py` que:

- una solicitud entregada registra `tokens_entrada`, `tokens_salida`, `costo_usd` y las
  métricas `llm_*`;
- una solicitud fallida registra `llm_reintentos`, `llm_cache_hit` y `llm_cache_miss`,
  pero **no** inventa tokens ni costo en 0;
- la corrida se cierra siempre (sin corridas en `RUNNING`).

No se utilizó un servidor MLflow real durante estas comprobaciones.

## 5. Limitaciones y verificaciones pendientes

- Validar la ejecución integral en Docker (`make up` + generación real).
- Verificar las métricas en una ejecución real con servidor MLflow (no sólo file store).
- La ejecución local en macOS x86_64 requirió el ajuste de `nlopt` descrito arriba; la CI
  de GitHub Actions es la referencia reproducible.

## 6. Conclusión

Las correcciones cubren los ocho puntos de la revisión: el plazo total evita esperas
multiplicadas, la caché sólo reutiliza respuestas válidas, la cancelación detiene los
reintentos, la configuración inválida se informa como 503, las métricas de error no
distorsionan MLflow, los 5xx permanentes no se reintentan y la documentación refleja el
comportamiento real. Ruff, la suite completa (404 pruebas) y la cobertura (94,00 %) están
en verde.
