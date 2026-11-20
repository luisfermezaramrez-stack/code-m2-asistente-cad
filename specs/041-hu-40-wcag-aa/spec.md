# SPEC-041 · HU-40 — Cierre de brechas WCAG 2.1 AA

- **ID**: SPEC-041
- **Historia**: #100 (HU-40) · 2 SP · Etiquetas: Frontend, accessibility · Hito: M4
- **Planificación**: Ola 2 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-035](../035-hu-34-sistema-diseno-v2/spec.md),
  [SPEC-039](../039-hu-38-app-shell/spec.md)
- **Rama**: `feature/hu-40-wcag-aa`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

Esta spec reformula el borrador 28: la base de accesibilidad ya existe y no se audita
desde cero.

1. Foco visible de 3 px (`frontend/src/style.css:4`), `aria-describedby` en los campos
   (`frontend/src/App.vue:49`, `frontend/src/App.vue:54`) y `role="alert"` en el error
   de entrada (`frontend/src/App.vue:51`).
2. Contraste de texto ≥ 6.31:1 documentado en `frontend/README.md:112` y
   `design/README.md:76`.
3. La verificación fue sólo manual y en Chrome (`frontend/README.md:109-112`): no hay
   auditoría automática en CI ni validación de lectores de pantalla.
4. El flujo ya es operable sin mouse: las acciones son `<button>` y `<a>`
   (`frontend/src/App.vue:57-65`, `frontend/src/App.vue:94`) y el visor atiende
   `@keydown` (`frontend/src/GlbViewer.vue:120-127`). La brecha concreta con evidencia
   hoy es la lista de etapas `ol.steps` (`frontend/src/App.vue:75`), que está fuera de la
   región viva del estado (`App.vue:70`) y no anuncia las etapas nuevas.

Con el shell de SPEC-039 y el modo oscuro de SPEC-035 aparecen vistas y un tema nuevos
que la base actual no cubre.

## Historia de usuario

**Como** usuario que navega con teclado o lector de pantalla, **quiero** que todo el flujo
cumpla WCAG 2.1 AA, **para** solicitar y revisar una pieza sin depender del mouse ni de la
vista.

## Requisitos

### Funcionales

- **RF-1**: auditoría axe automática en CI sobre las vistas principales.
- **RF-2**: corrección de las brechas reales detectadas por axe o con evidencia en el
  código, sin reescritura de la UI.
- **RF-3**: navegación completa por teclado en todas las vistas.
- **RF-4**: anuncios de estado accesibles para los eventos SSE del trabajo.
- **RF-5**: contraste AA verificado en ambos temas (claro y oscuro).

### No funcionales

- **RNF-1**: la auditoría corre sin red, API key ni GPU: el backend se simula.
- **RNF-2**: se conserva la base existente (foco, `aria-*`, contraste documentado).

## Criterios de aceptación

### AC1 — axe sin violaciones críticas ni serias

- **Dado** las vistas principales (nueva solicitud, historial, ajustes, resultado)
- **Cuando** CI ejecuta la auditoría axe
- **Entonces** no hay violaciones de impacto crítico o serio y una nueva hace fallar CI.

### AC2 — Flujo completo sin mouse (AC de no regresión)

Este criterio ya se cumple hoy en la vista única; se conserva como no regresión sobre las
vistas del shell. Las brechas de teclado nuevas se exigen sólo si axe las reporta (AC1).

- **Dado** la aplicación sin uso del mouse
- **Cuando** se escribe una solicitud, se envía, se sigue el progreso y se descarga el
  resultado
- **Entonces** todo el flujo se completa sólo con teclado y con foco visible.

### AC3 — Anuncios de estado

- **Dado** un trabajo en curso
- **Cuando** llegan eventos SSE de cambio de etapa o estado terminal
- **Entonces** se anuncian en una región viva sin mover el foco, incluidas las etapas que
  hoy se agregan a `ol.steps` (`App.vue:75`) fuera de toda región viva.

### AC4 — Contraste en ambos temas

- **Dado** los temas claro y oscuro
- **Cuando** se verifica el contraste de los tokens
- **Entonces** todos los pares texto/fondo cumplen AA.

## Fuera de alcance

- Rediseño visual o nuevos tokens (SPEC-035).
- Certificación formal con usuarios de tecnologías de apoyo.
- Nivel AAA.

## Métricas de éxito

- Cero violaciones axe críticas o serias en CI.
- Flujo completo operable sin mouse en ambos temas.
