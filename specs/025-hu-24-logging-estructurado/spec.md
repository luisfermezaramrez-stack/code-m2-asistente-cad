# SPEC-025 · HU-24 — Logging estructurado y trazas correlacionadas

- **ID**: SPEC-025
- **Historia**: issue por crear · Ola 0 · Tamaño S · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: —
- **Rama**: `feature/hu-24-logging-estructurado`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3

## Problema y contexto

El backend registra eventos con `logging.getLogger` suelto, sin configuración central:

1. `src/m2_cad/trabajos.py:22` crea el logger del módulo y sólo lo usa en
   `trabajos.py:97` y `trabajos.py:106` (`logger.exception` ante fallos de generación y
   de registro SSE).
2. `src/m2_cad/seguimiento.py:23` crea otro logger, usado en `seguimiento.py:260` y
   `seguimiento.py:331` para advertencias del cliente MLflow.
3. No hay `dictConfig` ni formato JSON en el paquete; cada línea depende del formato por
   defecto de uvicorn o de Python.
4. Existe un identificador de correlación parcial: la ruta JSON acepta `X-Request-ID` y lo
   usa como id del registro (`src/m2_cad/api.py:207-210`), y la ruta SSE usa
   `solicitud_id` como etiqueta de MLflow (`src/m2_cad/api.py:371-378`). Ninguno de los dos
   aparece en los logs, así que una solicitud no puede reconstruirse desde ellos.

## Historia de usuario

**Como** operador del servicio, **quiero** logs estructurados en JSON con un identificador
de solicitud propagado de punta a punta, **para** reconstruir qué pasó con una solicitud
concreta filtrando por un único id.

## Requisitos

### Funcionales

- **RF-1**: una configuración central con `logging.config.dictConfig` que emite cada
  registro en JSON (una línea por evento) con nivel, módulo, mensaje y marca de tiempo.
- **RF-2**: cada registro asociado a una solicitud incluye `request_id` y, en la ruta SSE,
  `job_id`.
- **RF-3**: el id se propaga API → trabajo SSE → pipeline → seguimiento MLflow; la corrida
  de MLflow guarda el mismo id como etiqueta.
- **RF-4**: el motivo de error se registra sin secretos: ninguna API key, cabecera
  `Authorization` ni variable sensible aparece en los logs.
- **RF-5**: un `X-Request-ID` válido recibido se reutiliza como `request_id`; si falta o no
  es válido, se genera uno nuevo (comportamiento actual de `_identificador`).

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: el modelo se simula.
- **RNF-2**: no cambia el contrato HTTP ni el formato de eventos SSE existentes.
- **RNF-3**: el nivel de log es configurable por variable de entorno.

> **Supuesto**: `request_id` y `job_id` pueden coincidir en la ruta SSE si el diseño lo
> simplifica; la decisión se fija en `plan.md`.

## Criterios de aceptación

### AC1 — Reconstrucción por un único id

- **Dado** una solicitud completa procesada por la API (JSON o SSE)
- **Cuando** se filtran los logs por su `request_id`
- **Entonces** aparecen, en orden, los eventos de entrada, etapas del pipeline, resultado
  (construida, declinada o error) y cierre del seguimiento, y la corrida de MLflow lleva el
  mismo id como etiqueta.

### AC2 — Formato JSON

- **Dado** el servicio arrancado con la configuración por defecto
- **Cuando** se emite cualquier registro del paquete `m2_cad`
- **Entonces** la línea es JSON válido con, al menos, `nivel`, `modulo`, `mensaje`,
  `marca_tiempo` y, si corresponde, `request_id`.

### AC3 — Sin secretos

- **Dado** una solicitud que falla con la API key configurada
- **Cuando** se registra el motivo del error
- **Entonces** ni el valor de la API key ni la cabecera `Authorization` aparecen en los logs.

## Fuera de alcance

- Agregadores o backends de logs externos (Loki, ELK, CloudWatch).
- Trazas distribuidas OpenTelemetry.
- Panel de métricas ([SPEC-052](../052-hu-51-panorama-metricas/spec.md)).

## Métricas de éxito

- Porcentaje de líneas de log del paquete con `request_id` en solicitudes: 100 %.
- Secretos detectados en logs de prueba: 0.
