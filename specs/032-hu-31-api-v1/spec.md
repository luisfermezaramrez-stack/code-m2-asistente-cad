# SPEC-032 · HU-31 — API `/v1` versionada con contrato congelado

- **ID**: SPEC-032
- **Historia**: issue por crear · Ola 1 · Tamaño M · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-028](../028-hu-27-tipos-openapi/spec.md)
- **Rama**: `feature/hu-31-api-v1`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §4
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

La API de HU-06 ([SPEC-013](../013-hu-06-api-fastapi/spec.md)) no tiene versión pública:

1. La aplicación declara `version="0.1.0"` (`src/m2_cad/api.py:27-31`) y expone rutas
   planas: `/health` (`api.py:54`), `/registros/{identificador}` (`api.py:222`),
   `/generar` (`api.py:397`) y `/generaciones/{solicitud_id}` (`api.py:495-522`).
2. `/docs` y `/openapi.json` quedan abiertos con los valores por defecto de FastAPI.
3. No hay contrato congelado: un cambio en un modelo de respuesta llega al cliente sin
   que ninguna prueba lo detecte.
4. El frontend llama a las rutas planas (`frontend/src/useGeneration.ts:136`,
   `frontend/src/api.ts:37`).

SPEC-028 genera los tipos del frontend desde el OpenAPI; esta spec fija ese OpenAPI por
versión para que el contrato sea estable.

## Historia de usuario

**Como** integrador de un cliente de la API, **quiero** rutas versionadas bajo `/v1` con
un contrato congelado y una política de deprecación, **para** actualizar el servidor sin
que mi cliente se rompa sin aviso.

## Requisitos

### Funcionales

- **RF-1**: todas las rutas de la API se publican con el prefijo `/v1`.
- **RF-2**: las rutas planas actuales redirigen a su equivalente `/v1` durante una versión.
- **RF-3**: el contrato OpenAPI de cada versión se congela en un archivo versionado en el
  repositorio.
- **RF-4**: un test de contrato compara el OpenAPI generado con el congelado y falla ante
  un cambio incompatible sin subir la versión.
- **RF-5**: la política de deprecación (plazo de las rutas viejas, cómo se anuncia un
  cambio de versión) queda documentada.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU.
- **RNF-2**: las rutas estáticas de la SPA y el 404 JSON de rutas API desconocidas se
  conservan. Ese comportamiento surge de `configurar_web` (`src/m2_cad/web.py:40-70`), que
  sólo añade `/` y `/assets` sin fallback; `api.py:560` es el comentario y `api.py:561` la
  llamada a `configurar_web`.
- **Supuesto**: el frontend pasa a consumir `/v1` en la misma HU, usando los tipos de
  SPEC-028.

## Criterios de aceptación

### AC1 — El cliente viejo sigue funcionando (AC de no regresión)

- **Dado** un cliente que llama a las rutas planas actuales: `/health` (`api.py:54`),
  `/registros/{identificador}` (`api.py:222`), `/generar` (`api.py:397`) y
  `/generaciones/{solicitud_id}` (`api.py:495`)
- **Cuando** ejecuta una generación completa (`/generar`, consulta y descarga) antes y
  después de introducir `/v1`
- **Entonces** obtiene el mismo resultado en ambos casos; tras el cambio, servido por las
  rutas `/v1`.

> Hoy este AC pasa sin código porque `/v1` no existe: se mantiene como prueba explícita de
> no regresión de las rutas planas, escrita antes del cambio.

### AC2 — Quitar un campo rompe el test de contrato

- **Dado** el contrato `/v1` congelado
- **Cuando** se quita un campo de una respuesta sin subir la versión
- **Entonces** el test de contrato falla en CI.

### AC3 — Prefijo `/v1`

- **Dado** el servicio en ejecución
- **Cuando** se consulta el OpenAPI publicado
- **Entonces** todas las rutas de la API aparecen bajo `/v1`.

### AC4 — Política documentada

- **Dado** el repositorio
- **Cuando** se busca la política de deprecación
- **Entonces** está documentada con el plazo de convivencia de las rutas viejas.

## Fuera de alcance

- Autenticación de la API ([SPEC-054](../054-hu-53-autenticacion/spec.md)).
- Un `/v2` o cambios funcionales de los endpoints.
- Generación de tipos del frontend (SPEC-028).

## Métricas de éxito

- 100 % de las rutas API bajo `/v1`.
- 0 cambios incompatibles fusionados sin subir versión.
