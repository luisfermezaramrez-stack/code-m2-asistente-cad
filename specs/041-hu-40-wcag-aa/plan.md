# Plan de implementación · HU-40 (SPEC-041)

## Decisión de arquitectura

No se reescribe la UI. Se conservan el foco visible de 3 px, los `aria-describedby`, el
`role="alert"`, los tokens con contraste verificado y el visor con controles de teclado.
Se corrigen tres brechas con evidencia en el código y se automatiza lo que hoy sólo era
manual:

1. **Trampa de teclado en el shell.** `frontend/src/App.vue` intercepta `Tab` entre los
   enlaces de navegación y `preventDefault()` en los extremos, así que el foco no puede
   salir de la barra hacia el formulario. Se elimina el manejador propio: `Tab` y `Enter`
   nativos de `<a>` y `<button>` ya cumplen AC2. El enlace «Saltar al contenido» pasa a
   apuntar a un `<main tabindex="-1">` para que la compensación de foco sea explícita.
2. **Etapas no anunciadas.** `ol.steps` se crea fuera de la región viva del estado. Se
   mantiene el `<div class="state" aria-live="polite">` para el estado y se convierte la
   lista en una región viva persistente (`aria-live="polite"`,
   `aria-relevant="additions text"`) que siempre existe en el DOM; así el primer `<li>`
   también se anuncia. No se mueve el foco.
3. **Auditoría axe ausente en CI.** `axe-core` se añade como dependencia de desarrollo y
   se inyecta en la página desde un helper de Playwright. Un nuevo espec
   `e2e/accesibilidad.spec.ts` audita las cuatro vistas (nueva solicitud, resultado,
   historial y ajustes) en tema claro y oscuro, sobre el build real y con el backend
   simulado de SPEC-042. Como `make e2e` ya corre en GitHub Actions y en el espejo, una
   violación crítica o seria hace fallar CI sin abrir una segunda puerta.
4. **Contraste AA.** La prueba `frontend/tests/tokens.test.ts` ya calcula la luminancia
   WCAG desde el CSS; se amplía para evaluar también el bloque explícito
   `:root[data-theme='dark']`, además del sistema. La auditoría axe comprueba además el
   contraste renderizado en ambos temas.

### Componentes

- `frontend/src/App.vue`: quitar `useRouter`, `nav`, `manejarTeclado` y `@keydown`;
  añadir `tabindex="-1"` a `<main id="contenido">`.
- `frontend/src/views/NewRequestView.vue`: `ol.steps` siempre renderizado con `aria-live`
  y oculto cuando está vacío por CSS; el estado conserva su región viva.
- `frontend/src/style.css`: regla `:empty` para la lista sin etapas; sin tokens nuevos.
- `frontend/e2e/support/auditoriaA11y.ts`: inyecta `axe-core/axe.min.js`, ejecuta las
  reglas `wcag2a`, `wcag2aa`, `wcag21a` y `wcag21aa`, y falla con el detalle de las
  violaciones críticas/serias y de `color-contrast`.
- `frontend/e2e/accesibilidad.spec.ts`: 4 vistas × 2 temas; la vista de resultado usa el
  backend simulado con un `verificado` y descargas disponibles.
- `frontend/e2e/teclado.spec.ts`: recorre el flujo completo con `Tab`, `Enter` y
  `keyboard.type`, comprueba foco visible, uso del enlace de salto y que la llegada de
  eventos SSE no cambia `document.activeElement`.
- `frontend/package.json` / `package-lock.json`: `axe-core@4.14.1` exacto, como el resto
  de las dependencias fijadas; `npm test` sigue siendo Vitest.
- `frontend/tests/tokens.test.ts`: contraste AA sobre claro, oscuro del sistema y oscuro
  explícito.

### Configuración

| Elemento | Valor | Uso |
| --- | --- | --- |
| `axe-core` | `4.14.1` (exacta) | Motor de auditoría inyectado en el navegador real. |
| Reglas axe | `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` | Alcance WCAG 2.1 AA de la HU. |
| Vistas | nueva solicitud, resultado, historial, ajustes | AC1. |
| Temas | `light`, `dark` vía `localStorage('m2-cad-theme')` | AC4. |
| Navegador | Chromium, `workers: 1` | Configuración existente de SPEC-042. |

### Compatibilidad y seguridad

- No se modifica Python, el contrato OpenAPI ni el pipeline CAD.
- No se añade red externa, API key ni GPU: axe se lee del paquete instalado y el backend
  sigue simulado con `page.route('**/v1/**')`.
- No se certifica con lectores de pantalla reales: SPEC-041 lo declara fuera de alcance.
  La evidencia distingue claramente auditoría automated de validación manual.
- Se documenta el resultado en `specs/041-hu-40-wcag-aa/evidence.md`, `specs/README.md`,
  `frontend/README.md` y `CONSTITUTION.md`.

## Verificación

1. `npm --prefix frontend test` (Vitest, incluido contraste de tokens).
2. `npm --prefix frontend run typecheck` y `npm --prefix frontend run build`.
3. `make e2e`: auditoría axe, flujo por teclado y los tres escenarios de SPEC-042.
4. Comprobación manual en Chromium: saltar al contenido, Tab desde la barra hasta el
   formulario, generar, descargar y alternar tema sin mouse.
5. `make check` completo antes de abrir el PR.
6. El PR cierra `#100` y pide revisión a `luisfermezaramrez-stack`; no se fusiona.
