# SPEC-055 · HU-54 — Sitio de documentación publicado

- **ID**: SPEC-055
- **Historia**: issue por crear · Ola 3 (opcional) · Tamaño M · Épica: Entrega
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-030](../030-hu-29-runbook-operativo/spec.md)
- **Rama**: `feature/hu-54-sitio-documentacion`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

La documentación vive como Markdown suelto en el repositorio: `README.md`,
`CONSTITUTION.md`, `docs/` y `specs/` con su índice (`specs/README.md`). `docs/` contiene
`docs/README.md`, `informe-final.md`, `model-card.md`, `backlog-v2.md`,
`auditoria-specs-024-056.md`, los documentos de HU-15 (`hu15-despliegue.md`,
`hu15-docker-validation.md`, `hu15-integracion-hu14.md`, `hu15-sse.md`), la prueba de
usuarios (`prueba-usuarios.md` y `prueba-usuarios/`), las corridas del banco de HU-07
(`docs/hu07/`) y el diagrama de arquitectura (`arquitectura.html` con sus JSON). No hay
configuración de generador (no existe `mkdocs.yml` en la raíz). Supuesto: no hay un sitio
navegable publicado; no es verificable desde el repositorio.

El ítem 48 del borrador ("MkDocs") se bajó a la ola 3: la necesidad operativa se cubre
primero con el runbook de SPEC-030; el sitio es presentación, no operación
(`docs/backlog-v2.md` §6 y §7).

## Historia de usuario

**Como** evaluador o nuevo integrante, **quiero** consultar la documentación del proyecto
en un sitio navegable, **para** entender uso, arquitectura y operación sin recorrer el
repositorio.

## Requisitos

### Funcionales

- **RF-1**: sitio estático generado desde el Markdown existente, sin duplicar contenido.
  Supuesto: MkDocs (ítem 48 del borrador) con un tema estándar.
- **RF-2**: navegación por secciones: uso, arquitectura, operación (runbook de SPEC-030),
  especificaciones y decisiones (`CONSTITUTION.md`).
- **RF-3**: publicación automática al fusionar en la rama de integración o principal.
  Supuesto: GitHub Pages desde un workflow de GitHub Actions.
- **RF-4**: el build del sitio falla ante enlaces internos rotos.

### No funcionales

- **RNF-1**: las dependencias del generador se gestionan con `uv` (regla de
  `CONSTITUTION.md`; prohibido `pip` y `requirements.txt`).
- **RNF-2**: el build del sitio no requiere red de terceros más allá de las dependencias,
  ni API key ni GPU.
- **RNF-3**: el contenido sigue en español, como el resto de la documentación.

## Criterios de aceptación

### AC1 — Build local

- **Dado** un checkout limpio con dependencias instaladas
- **Cuando** se ejecuta el comando documentado de build del sitio
- **Entonces** se genera el sitio sin errores ni advertencias de enlaces rotos.

### AC2 — Publicación

- **Dado** una PR fusionada que cambia documentación
- **Cuando** termina el workflow de publicación
- **Entonces** el sitio publicado refleja el cambio.

### AC3 — Runbook accesible

- **Dado** el sitio publicado
- **Cuando** se navega a la sección de operación
- **Entonces** se encuentra el runbook de SPEC-030 sin duplicar su texto.

## Fuera de alcance

- Redactar el runbook (SPEC-030) o reescribir la documentación existente.
- Documentación de API generada (cubierta por OpenAPI, SPEC-032).
- Traducción a otros idiomas.

## Métricas de éxito

- 0 enlaces internos rotos en el build.
- Sitio publicado actualizado tras cada fusión de documentación.
