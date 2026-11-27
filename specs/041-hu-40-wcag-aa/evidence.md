# HU-40 — Evidencias de implementación

**Fecha:** 27 de noviembre de 2026
**Issue:** #100
**Especificación:** SPEC-041 (dependencias: SPEC-035 y SPEC-039)
**Rama:** `feature/hu-40-wcag-aa`
**PR:** pendiente de apertura

## 1. Implementación

- `frontend/src/App.vue`: se eliminó el manejador propio de `keydown` que capturaba `Tab`
  y `Enter` dentro de `nav` y provocaba una trampa de teclado en los extremos. La
  navegación vuelve a usar `Tab`/`Enter` nativos de `RouterLink`, y `<main id="contenido">`
  gana `tabindex="-1"` para que «Saltar al contenido» mueva el foco de forma explícita.
- `frontend/src/views/NewRequestView.vue`: `ol.steps` ya no se crea con `v-if`; existe
  desde el inicio como región viva `aria-live="polite"`,
  `aria-relevant="additions text"`. El primer evento SSE y los siguientes se anuncian
  sin mover el foco. El estado conserva su propia región viva.
- `frontend/src/style.css`: `.steps--vacio` anula el sangrado de la lista sin etapas;
  no se añaden tokens ni colores nuevos.
- `frontend/e2e/support/auditoriaA11y.ts`: inyecta `axe-core/axe.min.js` en el navegador,
  corre `wcag2a`, `wcag2aa`, `wcag21a` y `wcag21aa`, muestra el detalle legible de cada
  violación y falla por impacto crítico/serio o por `color-contrast`.
- `frontend/e2e/accesibilidad.spec.ts`: audita nueva solicitud, resultado, historial y
  ajustes en tema claro y oscuro, con el backend simulado de SPEC-042.
- `frontend/e2e/teclado.spec.ts`: completa el flujo con `Tab`, `Enter` y entrada de
  texto por teclado; comprueba el enlace de salto, el foco visible de 3 px, el cambio de
  tema, el progreso, la estabilidad del foco y la descarga del STEP.
- `frontend/package.json` y `package-lock.json`: `axe-core@4.14.1` exacto, como
  dependencia de desarrollo. `npm test` sigue siendo Vitest.
- `frontend/tests/router.test.ts`: las dos pruebas que exigían el manejador eliminado
  ahora verifican que `Tab` no se captura y que el enlace enfocado navega con su
  activación nativa, además del `tabindex` del destino del salto.
- `frontend/tests/App.test.ts` y `frontend/tests/tokens.test.ts`: nuevos asertos de
  región viva/foco y contraste sobre claro, oscuro del sistema y oscuro explícito.

No se modificaron `src/m2_cad/**`, los contratos OpenAPI ni el pipeline CAD.

## 2. Criterios de aceptación

| AC | Verificación | Resultado |
|---|---|---|
| AC1 — axe sin violaciones críticas ni serias | `make e2e`: `accesibilidad.spec.ts` audita 4 vistas × 2 temas sobre el build real; 0 violaciones críticas, serias y 0 de `color-contrast`. | Cumple. |
| AC2 — Flujo completo sin mouse | `e2e/teclado.spec.ts`: salto al contenido, cambio de tema, descripción, envío, progreso y descarga del STEP con `Tab`/`Enter`; foco visible de 3 px. | Cumple en Chromium con build real. |
| AC3 — Anuncios de estado | `ol.steps` es región viva persistente; Vitest comprueba que al añadir `Validando solicitud` el foco no cambia; E2E lo comprueba hasta el terminal. | Cumple. |
| AC4 — Contraste en ambos temas | `tokens.test.ts` recalcula 17 pares para claro, oscuro del sistema y oscuro explícito (≥4.5 texto, ≥3 no texto); axe verifica el contraste renderizado en ambos temas. | Cumple; valores vigentes en `docs/diseno-v2.md`. |

### Mutación que demuestra AC1

Se cambió temporalmente `--color-muted` del tema claro a `#ffffff` en
`frontend/src/design/tokens.css`, se reconstruyó el bundle y se ejecutó sólo la auditoría
de tema claro: axe falló con `color-contrast`-impacto `serious`, ratios `1.12:1` y
`1.07:1` en `.brand`, `.muted` y `.viewport > .muted`, con captura y traza. El cambio se
revirtió con `git checkout -- frontend/src/design/tokens.css` y no se commiteó; la
corrida final de `make e2e` quedó en verde.

## 3. Validaciones realizadas

| Validación | Comando | Resultado |
|---|---|---|
| Vitest | `npm --prefix frontend test` | **84 aprobadas**, 9 archivos. |
| Tipado | `npm --prefix frontend run typecheck` | Sin errores (`src`, `tests` y `e2e`). |
| Build | `npm --prefix frontend run build` | Correcto; chunk diferido del visor sin cambios. |
| E2E | `make e2e` | **6 aprobadas** en 9,0 s: axe claro/oscuro, declinación, flujo feliz, error del modelo y teclado. |
| Verificación completa | `make check` | Ruff, prompts, contrato OpenAPI, tipos OpenAPI, Vitest, TypeScript y build en verde; pytest **690/696** con cobertura **92,06 %** (umbral 70 %). Fallan 6 pruebas Windows preexistentes, detalle abajo. |
| Comparación contra la base | mismos 6 node IDs en `origin/main` | 5 fallan igual; el sexto (`msvcrt.locking` con duplicados concurrentes) es intermitente de la misma familia y pasó en esa repetición. |
| Estándar `jan-project-standard` | `new_project.py --path . --audit` | **0 FALTA**, 4 OK, 21 DIFIERE (personalizaciones legítimas ya presentes antes de esta HU). |
| CI del PR | jobs del PR | Pendiente de la apertura del PR; `make e2e` ya está cableado en GitHub Actions y en el espejo desde SPEC-042. |

Las seis fallas locales de `make check` son ajenas a este cambio: cinco huellas STEP del
corpus dorado, bloqueo `msvcrt.locking`/enlaces simbólicos sin privilegio en Windows y el
umbral p95 de MLflow. No se tocó Python ni esas pruebas.

## 4. Compatibilidad y seguridad

- Sin red externa, API key ni GPU: axe se lee del paquete instalado y las peticiones
  `/v1` siguen interceptadas por `page.route` (RNF-1).
- Se conservan la base accesible de SPEC-035/SPEC-039, el foco de 3 px, los
  `aria-describedby` y el `role="alert"` (RNF-2). No se rediseña la UI.
- La comprobación axe en CI no abre una segunda puerta: se suma al job `e2e` existente.
- No se afirma certificación con lectores de pantalla ni matriz de navegadores: SPEC-041
  lo deja fuera de alcance. La evidencia es auditoría automatizada en Chromium.

## 5. Integración y correcciones

| Hallazgo | Corrección | Prueba |
|---|---|---|
| Las pruebas antiguas de `router.test.ts` exigían el manejador que capturaba `Tab`. | Se reescribieron para verificar la ausencia de trampa y la navegación nativa del enlace enfocado. | Vitest 84/84. |
| La primera corrida de mutación usó `npm --prefix frontend exec -- ...` desde la raíz y no encontró `baseURL`. | Se ejecutó desde `frontend/` con `npm run e2e` y se reconstruyó el bundle antes de auditar. | Mutación detectada y revertida; `make e2e` final en verde. |
| El worktree nuevo no tenía `vendor/` ni las dependencias Python. | Se copió el `vendor/` preparado del checkout principal y se apuntó `UV_PROJECT_ENVIRONMENT` al entorno existente; no se cambió el lockfile. | Ruff y comprobaciones de contrato/tipos en verde. |

## 6. Limitaciones

- Chromium es el único navegador de la suite, según el supuesto de SPEC-042.
- Las reglas axe se ejecutan sobre el DOM posterior a la carga; no sustituyen una
  revisión con lector de pantalla real (fuera de alcance de SPEC-041).
- Las vistas de historial y ajustes siguen siendo estados presentacionales: la auditoría
  cubre su accesibilidad, no un contenido aún no implementado por otras HU.
- `make check` no queda verde en este equipo Windows por fallos preexistentes; las
  puertas de CI sobre Linux y la suite E2E completa sí quedaron verificadas en local.

## 7. Conclusión

HU-40 elimina la trampa de teclado del shell, anuncia cada etapa del SSE sin mover el
foco y convierte la revisión manual de accesibilidad en una auditoría axe de CI sobre
cuatro vistas y dos temas. La regresión de contraste introducida a propósito fue
detectada, y la suite final quedó en verde con 84 pruebas Vitest y 6 E2E.
