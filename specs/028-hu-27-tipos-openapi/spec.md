# SPEC-028 · HU-27 — Tipos del frontend generados desde OpenAPI

- **ID**: SPEC-028
- **Historia**: #87 (HU-27) · 2 SP · Etiquetas: Frontend, Backend · Hito: M4
- **Planificación**: Ola 0 · Tamaño S · Épica: Frontend/API
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: —
- **Rama**: `feature/hu-27-tipos-openapi`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

1. Los tipos del cliente están escritos a mano en `frontend/src/api.ts:1-15` (`Stage`,
   `Job`, `Format`, `Artifact`) y se validan con `parseJob` (`frontend/src/api.ts:19`).
2. Hay una prueba que congela parte del contrato del backend
   (`tests/test_sse.py:116-119`, respuesta de `POST /generar` en OpenAPI), pero nada
   compara el TypeScript con ese contrato: un campo renombrado en FastAPI sólo se descubre
   en ejecución.
3. Varias rutas no declaran `response_model` (por ejemplo `GET /generaciones/{solicitud_id}`,
   `src/m2_cad/api.py:495`), así que en `/openapi.json` aparecen como un objeto genérico
   sin campos (`"type": "object"` sin `properties`), igual que la respuesta JSON de
   `POST /generar` (`tests/test_sse.py:117-119`).

Esta spec es requisito de la API versionada
([SPEC-032](../032-hu-31-api-v1/spec.md)).

## Historia de usuario

**Como** desarrollador del frontend, **quiero** que los tipos TypeScript del cliente se
generen desde el OpenAPI del backend y que CI verifique que están al día, **para** que un
cambio de contrato rompa la integración continua y no la aplicación en producción.

## Requisitos

### Funcionales

- **RF-1**: un objetivo de `make` genera los tipos TypeScript desde `/openapi.json`.
- **RF-2**: CI regenera los tipos y falla si el resultado no coincide con lo versionado.
- **RF-3**: `frontend/src/api.ts` consume los tipos generados en lugar de declararlos a
  mano.
- **RF-4**: el mensaje de fallo en CI indica el comando exacto para regenerar.

### No funcionales

- **RNF-1**: la generación no requiere levantar el servidor ni usar red, API key ni GPU:
  el esquema se obtiene de `app.openapi()`.
- **RNF-2**: la generación es determinista (mismo esquema → mismo archivo).
- **RNF-3**: no cambia el contrato HTTP ni los eventos SSE existentes.

> **Supuesto**: para que el estado de un trabajo (`Job`) quede en el esquema, las rutas que
> lo devuelven declaran un modelo de respuesta; los eventos SSE se documentan con el mismo
> modelo. El alcance exacto se fija en `plan.md`.

> **Supuesto**: la validación en tiempo de ejecución de `parseJob` se conserva; los tipos
> generados no la reemplazan.

## Criterios de aceptación

### AC1 — Campo cambiado sin regenerar rompe CI

- **Dado** los tipos generados y versionados
- **Cuando** una PR cambia un campo de una respuesta del API sin regenerar los tipos
- **Entonces** el job de CI falla e indica el comando para regenerarlos.

### AC2 — Generación por `make`

- **Dado** un checkout limpio con dependencias instaladas
- **Cuando** se ejecuta el objetivo de generación
- **Entonces** el archivo de tipos queda actualizado sin levantar el servidor.

### AC3 — Cliente tipado

- **Dado** los tipos generados
- **Cuando** se ejecuta `make check`
- **Entonces** `api.ts` compila contra ellos y Vitest y `vue-tsc` pasan.

## Fuera de alcance

- Versionar la API bajo `/v1` ([SPEC-032](../032-hu-31-api-v1/spec.md)).
- Generar un cliente HTTP completo.
- Cambiar campos del contrato actual.

## Métricas de éxito

- Divergencias contrato ↔ TypeScript que llegan a `develop`: 0.
- Tipos de respuesta del API escritos a mano en `api.ts`: 0.
