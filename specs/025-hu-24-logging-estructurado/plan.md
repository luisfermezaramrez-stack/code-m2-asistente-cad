# HU-24 — Plan técnico de logging estructurado y trazas correlacionadas

## 1. Objetivo

Centralizar la configuración de logging del paquete `m2_cad` para emitir una línea JSON por
evento, con un `request_id` correlacionado de punta a punta (API → trabajo SSE → pipeline →
MLflow) y sin secretos en los mensajes, sin cambiar el contrato HTTP ni el formato de los
eventos SSE.

## 2. Arquitectura propuesta

1. Un módulo `observabilidad.py` concentra `dictConfig`, el formateador JSON, el filtro de
   contexto y la redacción de secretos.
2. `api.py` fija el `request_id` al entrar en `POST /generar` (reutilizando un
   `X-Request-ID` válido o generando uno) y lo propaga al trabajo SSE y a la corrida de
   MLflow.
3. `trabajos.py` copia el contexto de la solicitud al hilo del trabajo y añade el `job_id`,
   de modo que los registros del pipeline ejecutado en segundo plano conserven ambos ids.
4. `pipeline.py`, `trabajos.py` y `api.py` emiten eventos en las etapas ya existentes:
   entrada, validación, generación, verificación, construcción, terminal y cierre del
   seguimiento. El evento de cierre se registra en `medir_solicitud()` y no dentro de
   `Corrida.finalizar()` para no alterar la medición de sobrecarga de HU-16 (AC6).
5. El formateador aplica redacción antes de serializar: cabeceras `Authorization`, claves de
   API, tokens Bearer, valores de variables sensibles y PII (correos y nombres declarados).

El `request_id` y el `job_id` pueden coincidir en la ruta SSE por decisión de diseño: el id
del trabajo es el `solicitud_id` que ya expone la API.

## 3. Componentes

| Archivo | Responsabilidad |
|---|---|
| `src/m2_cad/observabilidad.py` | Configuración central, formato JSON, contexto y redacción |
| `src/m2_cad/api.py` | Establece `request_id`, registra eventos HTTP, etiqueta MLflow y el cierre del seguimiento |
| `src/m2_cad/trabajos.py` | Propaga el contexto al hilo del trabajo y añade `job_id` |
| `src/m2_cad/pipeline.py` | Eventos de etapas y redacción del motivo de error del proveedor |
| `tests/test_hu24_logging.py` | Pruebas de AC1–AC3, RF-5 y RNF-3 |

## 4. Formato de registro

Cada línea es un objeto JSON con, al menos:

| Clave | Contenido |
|---|---|
| `nivel` | `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL` |
| `modulo` | Nombre del logger (`m2_cad.api`, `m2_cad.pipeline`, …) |
| `mensaje` | Mensaje formateado y redactado |
| `marca_tiempo` | ISO 8601 en UTC |
| `request_id` | Id de correlación de la solicitud, cuando aplica |
| `job_id` | Id del trabajo SSE, cuando aplica |
| `excepcion` | Traza redactada, sólo en `logger.exception` |

Los ids se inyectan con un `logging.Filter` basado en `contextvars`, por lo que no hace falta
añadirlos a cada llamada de logging.

## 5. Configuración

- `M2_LOG_LEVEL`: nivel del logger `m2_cad` (por defecto `INFO`; valores no reconocidos
  caen a `INFO`). La configuración se aplica al importar la API, que es el punto en el que
  el servicio lee su entorno.
- `configurar_logging()` se aplica al importar la API y se puede volver a invocar para
  releer el entorno (por ejemplo, en pruebas); `dictConfig` sustituye los handlers del
  paquete, así que no se repite en el ciclo de vida de la aplicación para no borrar
  handlers añadidos por herramientas de diagnóstico.
- Se conserva `propagate=True` para no romper la captura de `caplog` en las pruebas
  existentes de `m2_cad.seguimiento`.

## 6. Correlación con MLflow

Las corridas de `POST /generar` y del flujo SSE llevan las etiquetas `request_id` y
`solicitud_id`; en SSE también `job_id`. Los valores pasan por la sanitización existente de
`seguimiento`, que ya limita su longitud. No se registran claves, tokens ni URLs con
credenciales.

## 7. Estrategia de pruebas

Pytest con `TestClient`, dependencias inyectadas y modelo simulado; sin red, GPU ni API key.
Se comprueban:

- AC1: al filtrar por `request_id` aparecen entrada, etapas, resultado y cierre, y la
  corrida lleva el mismo id como etiqueta.
- AC2: cada línea es JSON válido con las claves obligatorias.
- AC3: un error del proveedor cuyo cuerpo incluye `Authorization: Bearer <clave>` no filtra
  la clave ni la cabecera.
- RF-5: `X-Request-ID` válido se reutiliza; ausente o inválido se genera uno nuevo.
- RF-2: los registros del hilo SSE conservan `request_id` y `job_id`.
- RNF-3: el nivel se lee de `M2_LOG_LEVEL`.

Se ejecutan además Ruff, la suite completa y la comprobación de cobertura (≥ 70 %).

## 8. Alcance y restricciones

- No cambiar el contrato HTTP ni los eventos SSE (RNF-2).
- No introducir agregadores externos, OpenTelemetry ni paneles (fuera de alcance de la spec).
- No registrar el texto de la solicitud en los logs: la redacción complementa, pero no
  sustituye, la política de privacidad del registro CSV.
- No modificar la lógica de generación CAD ni la de reintentos del LLM.

## 9. Cierre

La historia se considera terminada cuando AC1–AC3 estén cubiertos por pruebas, Ruff y Pytest
pasen, `evidence.md` documente los resultados y el PR sea aprobado.
