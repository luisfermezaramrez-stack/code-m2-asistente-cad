# HU-24 — Evidencias de implementación

**Fecha:** 24 de noviembre de 2026  
**Issue:** #84  
**Especificación:** SPEC-025  
**Rama:** `feature/hu-24-logging-estructurado`

## 1. Implementación

Se centralizó la observabilidad del paquete `m2_cad` sin alterar el contrato HTTP ni el
formato SSE:

- `observabilidad.py`: `dictConfig`, formateador JSON, filtro de contexto, redacción y
  nivel desde `M2_LOG_LEVEL`.
- `api.py`: `request_id` desde `X-Request-ID` válido (o UUID nuevo), eventos de entrada y
  resultado, etiquetas MLflow y cierre del seguimiento correlacionado.
- `trabajos.py`: `copy_context()` al hilo del trabajo SSE y `job_id` en cada registro del
  pipeline en segundo plano.
- `pipeline.py`: eventos de etapas y registro redactado del cuerpo de errores del proveedor.
- Documentación: `README.md`, `.env.example`, `CONSTITUTION.md` y `specs/README.md`.

## 2. Resultados de las pruebas

| Validación | Resultado |
|---|---|
| Pytest (suite completa, sin red/GPU/API key) | 384 aprobadas |
| Pytest `tests/test_hu24_logging.py` | 10 aprobadas |
| Cobertura `src/m2_cad` | 94 % total; `observabilidad.py` 100 % |
| Ruff: análisis estático (`E, F, I, B`) | Sin errores |
| Ruff: formato | 37 archivos correctamente formateados |
| Suite con cobertura, 4 ejecuciones consecutivas | 384 aprobadas en todas |

Los 26 warnings de la suite son `DeprecationWarning` de SWIG/build123d, ajenos a HU-24.

## 3. Criterios de aceptación

- **AC1:** `test_ac1_reconstruccion_por_request_id` filtra todos los registros por un mismo
  `request_id` y verifica, en orden, entrada HTTP, etapas del pipeline, resultado entregado y
  cierre del seguimiento; comprueba además que la corrida lleva el mismo id en las etiquetas
  `request_id` y `solicitud_id`.
- **AC2:** `test_ac2_json_valido_con_claves_obligatorias` valida JSON parseable con `nivel`,
  `modulo`, `mensaje` y `marca_tiempo` (UTC ISO 8601), más `detalles` opcionales.
- **AC3:** `test_ac3_error_del_proveedor_no_filtra_la_clave` y
  `test_ac2_el_formateador_redacta_secretos` comprueban que un cuerpo con
  `Authorization: Bearer <clave>` queda como `Authorization: [REDACTADO]` y que la clave de
  prueba no aparece en ningún registro.

## 4. Requisitos funcionales verificados

- **RF-1/RF-2:** formato central y `request_id`/`job_id` presentes en JSON de API y del hilo
  SSE (`test_rf2_hilo_sse_conserva_request_id_y_job_id`).
- **RF-5:** `X-Request-ID` UUID válido se reutiliza; ausente, vacío o inválido se genera uno
  nuevo (`test_rf5_*`).
- **RNF-1/RNF-2:** sin red, API key ni GPU en pruebas; respuesta HTTP y eventos SSE
  intactos.
- **RNF-3:** `M2_LOG_LEVEL=debug` cambia el nivel y un valor desconocido cae a `INFO`.

## 5. Notas técnicas

- El evento de cierre del seguimiento se emite en `medir_solicitud()` y no dentro de
  `Corrida.finalizar()`. Así se preserva la medición de sobrecarga ≤ 50 ms p95 de HU-16
  (AC6), que había mostrado inestabilidad cuando `finalizar()` escribía en el log.
- `configurar_logging()` no se repite en el ciclo de vida de la app: `dictConfig` sustituye
  handlers y borraría los que añaden las herramientas de diagnóstico.
- En este host macOS x86_64 `make check` no puede completar la sincronización porque
  `nlopt==2.11.0` no publica wheel para esa plataforma (limitación conocida del repo). Los
  pasos equivalentes se ejecutaron con `uv run --no-sync`: Ruff, Pytest y cobertura.

## 6. Limitaciones

- No se incorpora un agregador externo ni OpenTelemetry: la spec pide líneas JSON y
  correlación, no un colector.
- El texto de la solicitud no se escribe en el log; la redacción complementa la política de
  privacidad ya aplicada al registro CSV.
- `M2_LOG_LEVEL` se lee al importar `api.py`; cambiarlo en caliente requiere reiniciar el
  proceso o llamar explícitamente a `configurar_logging()`.
