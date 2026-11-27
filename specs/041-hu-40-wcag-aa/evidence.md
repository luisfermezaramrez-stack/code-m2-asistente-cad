# HU-40 — Evidencias de implementación

**Fecha:** 27 de noviembre de 2026
**Issue:** #100
**Especificación:** SPEC-041 (dependencias: SPEC-035 y SPEC-039)
**Rama:** `feature/hu-40-wcag-aa`
**PR:** [#149](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/149)

## 1. Implementación

- `frontend/src/App.vue`: se eliminó el manejador propio de `keydown` que capturaba `Tab`
  y `Enter` dentro de `nav` y provocaba una trampa de teclado en los extremos. La
  navegación vuelve a usar `Tab`/`Enter` nativos de `RouterLink`, y `<main id="contenido">`
  gana `tabindex="-1"` para que «Saltar al contenido» mueva el foco de forma explícita.
- `frontend/src/views/NewRequestView.vue`: `ol.steps` ya no se crea con `v-if`; existe
  desde el inicio como región viva `aria-live="polite"`,
  `aria-relevant="additions text"`. El primer evento SSE y los siguientes se anuncian
  sin mover el foco. El estado conserva su propia región viva. `Generar pieza` deja de
  usar `disabled` mientras `busy`: sigue enfocable y expone `aria-disabled="true"`,
  porque deshabilitar el botón enfocado hace que Chromium mueva el foco a `body` de
  forma intermitente. La guarda `start()` evita envíos duplicados.
- `frontend/src/style.css`: `.steps--vacio` anula el sangrado de la lista sin etapas y
  `button[aria-disabled='true']` comparte el aspecto de `button:disabled`; no se añaden
  tokens ni colores nuevos.
- `frontend/e2e/support/auditoriaA11y.ts`: inyecta `axe-core/axe.min.js` en el navegador,
  corre `wcag2a`, `wcag2aa`, `wcag21a` y `wcag21aa`, muestra el detalle legible de cada
  violación y falla por impacto crítico/serio o por `color-contrast`.
- `frontend/e2e/accesibilidad.spec.ts`: audita nueva solicitud, resultado, historial y
  ajustes en tema claro y oscuro, con el backend simulado de SPEC-042.
- `frontend/e2e/teclado.spec.ts`: completa el flujo con `Tab`, `Enter` y entrada de
  texto por teclado; comprueba el enlace de salto, el foco visible de 3 px, el cambio de
  tema, el progreso, la estabilidad del foco desde el envío hasta el terminal y la
  descarga del STEP.
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
| AC2 — Flujo completo sin mouse | `e2e/teclado.spec.ts`: salto al contenido, cambio de tema, descripción, envío, progreso y descarga del STEP con `Tab`/`Enter`; foco visible de 3 px y botón de envío enfocado durante toda la espera. | Cumple en Chromium con build real. |
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
| Vitest | `npm --prefix frontend test` | **85 aprobadas**, 9 archivos. |
| Tipado | `npm --prefix frontend run typecheck` | Sin errores (`src`, `tests` y `e2e`). |
| Build | `npm --prefix frontend run build` | Correcto; chunk diferido del visor sin cambios. |
| E2E | `make e2e` | **6 aprobadas** en 8,3 s: axe claro/oscuro, declinación, flujo feliz, error del modelo y teclado. |
| Estabilidad del foco | `npm --prefix frontend run e2e -- e2e/teclado.spec.ts --repeat-each=10` | **10/10 aprobadas** en 16,6 s tras el ajuste de `aria-disabled`. |
| Verificación completa | `make check` | Ruff, prompts, contrato OpenAPI, tipos OpenAPI, Vitest, TypeScript y build en verde; pytest **690/696** con cobertura **92,06 %** (umbral 70 %). Fallan 6 pruebas Windows preexistentes, detalle abajo. |
| Comparación contra la base | mismos 6 node IDs en `origin/main` | 5 fallan igual; el sexto (`msvcrt.locking` con duplicados concurrentes) es intermitente de la misma familia y pasó en esa repetición. |
| Estándar `jan-project-standard` | `new_project.py --path . --audit` | **0 FALTA**, 4 OK, 21 DIFIERE (personalizaciones legítimas ya presentes antes de esta HU). |
| CI del PR #149 | jobs de GitHub Actions y espejo | `e2e`, `test`, `dependencias` y `espejo` en verde; `secretos` en rojo por cuatro hallazgos preexistentes, detalle abajo. |

En PR #149, `e2e` pasó en 40 s, `test` en 1 m 42 s, `dependencias` en 19 s y `espejo`
en 6 s. `secretos` falló con `generic-api-key` en
`tests/test_metricas.py:575,576,598,599`, todos del commit
`09cca944d81801f376b45bc447cf0e3138d78dc2`, anterior a esta HU y ya detectado en HU-39.
No se tocó ese archivo, no se reescribió el historial y no se añadió una excepción: la
correctiva pertenece a HU-28. El job `e2e` de CI ejecutó la auditoría axe y el flujo
sin mouse del build del PR.

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
| Al reejecutar E2E tras la interrupción de acceso, `teclado.spec.ts` falló una vez con el foco en `body`: `Generar pieza` se deshabilitaba al iniciar. | El botón conserva el foco con `aria-disabled="true"` y mantiene la guarda de `start()`; se añadió un aserto E2E inmediato y una prueba Vitest de no duplicidad. | 85/85 Vitest; 6/6 E2E; 10/10 repeticiones del flujo de teclado. |

## 6. Limitaciones

- Chromium es el único navegador de la suite, según el supuesto de SPEC-042.
- Las reglas axe se ejecutan sobre el DOM posterior a la carga; no sustituyen una
  revisión con lector de pantalla real (fuera de alcance de SPEC-041).
- Las vistas de historial y ajustes siguen siendo estados presentacionales: la auditoría
  cubre su accesibilidad, no un contenido aún no implementado por otras HU.
- `make check` no queda verde en este equipo Windows por fallos preexistentes; en CI
  `e2e` y `test` quedaron en verde y `secretos` reprodujo el hallazgo preexistente de
  HU-28. El merge queda al equipo.

## 7. Conclusión

HU-40 elimina la trampa de teclado del shell, mantiene el foco en el botón de envío
durante la espera, anuncia cada etapa del SSE sin mover el foco y convierte la revisión
manual de accesibilidad en una auditoría axe de CI sobre cuatro vistas y dos temas. La
regresión de contraste introducida a propósito fue detectada, y la suite final quedó en
verde con 85 pruebas Vitest y 6 E2E.

## 8. Verificación tras la interrupción de acceso

- `git fsck --connectivity-only --no-reflogs` en el worktree y en el checkout principal:
  sin objetos perdidos ni corruptos. Los objetos `dangling` listados son restos normales
  de worktrees y ramas antiguas.
- `git stash list`: los cinco stashes siguen intactos, incluido `stash@{0}` de HU-28.
- `HEAD` local y `origin/feature/hu-40-wcag-aa` coincidían al reconectar; PR #149 sigue
  abierto y vincula `#100`.
- `git diff --check` limpio; `frontend/package.json` y `frontend/package-lock.json` sin
  cambios desde el commit; `npm ls --depth=0` muestra `axe-core@4.14.1`.
- Rerun tras la reconexión: 85/85 Vitest, typecheck limpio, 6/6 E2E, 10/10 repeticiones
  del flujo de teclado y auditoría de estándar con 0 `FALTA`.
