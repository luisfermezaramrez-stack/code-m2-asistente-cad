# SPEC-030 · HU-29 — Runbook operativo

- **ID**: SPEC-030
- **Historia**: issue por crear · Ola 0 · Tamaño S · Épica: Entrega
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: —
- **Rama**: `feature/hu-29-runbook-operativo`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3

## Problema y contexto

La documentación actual explica cómo levantar el sistema, no cómo operarlo cuando falla:

1. `README.md:144` (*Instalación y uso*), `README.md:218` (*Despliegue local con Docker
   Compose*) y `docs/hu15-despliegue.md` describen la puesta en marcha.
2. Los fallos del proveedor tienen mensajes en español (`MENSAJES_HTTP`,
   `src/m2_cad/pipeline.py:96-100`: 401 clave rechazada, 402 sin saldo, 429 límite), pero
   ningún documento dice qué hacer ante cada uno.
3. El modelo se elige con `LLM_MODEL` (`docker-compose.yml:34`) y la clave con
   `DEEPSEEK_API_KEY` (`docker-compose.yml:33`); no hay procedimiento de rotación ni de
   vuelta atrás.
4. El registro vive en `data/registro.csv` (`src/m2_cad/registro.py:29`) y las piezas en
   `outputs/`; no hay procedimiento de restauración.

## Historia de usuario

**Como** operador del servicio, **quiero** un runbook con los incidentes previsibles y su
respuesta, **para** diagnosticar y resolver una caída sin depender de quien escribió el
código.

## Requisitos

### Funcionales

- **RF-1**: un runbook en `docs/` que cubre, como mínimo:
  - modelo caído o sin respuesta;
  - cuenta sin crédito;
  - respuesta inválida del modelo;
  - rotación de la clave DeepSeek;
  - rollback de la versión de modelo;
  - rollback de la imagen del servicio;
  - restauración de `data/registro.csv`;
  - restauración de `outputs/`.
- **RF-2**: cada escenario tiene tres partes: síntoma, diagnóstico y acción.
- **RF-3**: cada diagnóstico y cada acción incluyen el comando exacto a ejecutar.
- **RF-4**: el runbook se enlaza desde el README.

### No funcionales

- **RNF-1**: los comandos usan las herramientas del proyecto (`make`, `uv`, `docker
  compose`) y no exponen secretos en pantalla ni en el historial.
- **RNF-2**: cada comando se valida en el entorno local antes de fusionar.

> **Supuesto**: la restauración se documenta sobre el almacenamiento actual (CSV y
> carpeta); cuando exista la persistencia de
> [SPEC-031](../031-hu-30-persistencia-registro/spec.md), el runbook se actualiza en esa
> spec.

## Criterios de aceptación

### AC1 — Estructura por escenario

- **Dado** el runbook publicado
- **Cuando** se revisa cada escenario de RF-1
- **Entonces** cada uno tiene síntoma, diagnóstico y acción, y cada paso de diagnóstico y
  de acción trae su comando exacto.

### AC2 — Comandos ejecutables

- **Dado** el entorno local levantado con `make up`
- **Cuando** se ejecutan los comandos de diagnóstico del runbook
- **Entonces** corren sin modificaciones y sin mostrar la API key.

### AC3 — Descubrible

- **Dado** el README del repositorio
- **Cuando** se busca cómo operar el sistema ante una falla
- **Entonces** hay un enlace directo al runbook.

## Fuera de alcance

- Sitio de documentación publicado ([SPEC-055](../055-hu-54-sitio-documentacion/spec.md)).
- Alertas automáticas ([SPEC-047](../047-hu-46-alertas-regresion/spec.md)).
- Despliegue en la nube ([SPEC-048](../048-hu-47-despliegue-nube/spec.md)).

## Métricas de éxito

- Escenarios de RF-1 cubiertos con síntoma, diagnóstico y acción: 8 de 8.
- Comandos del runbook que fallan al ejecutarse: 0.
