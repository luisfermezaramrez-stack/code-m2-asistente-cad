# Plan de implementación · HU-41 (SPEC-042)

## Decisión de arquitectura

Se prueba el **build real** de la SPA (`npm run build` → `frontend/dist`) servido por
`vite preview`, y el backend se simula **dentro del test** con `page.route('**/v1/**')`.
La SPA consume rutas relativas (`/v1/generar`, `/v1/generaciones/{id}`,
`/v1/generaciones/{id}/archivos/{formato}`) y el bundle no lleva ninguna URL del backend
(SPEC-037), así que interceptar `/v1` en el navegador basta: no hace falta un segundo
proceso, ni el proxy de Vite, ni que alguien escuche en `127.0.0.1:8000`. Eso es lo que
hace posible RNF-1: sin red externa, sin API key y sin GPU.

No se levanta un stub de FastAPI. La regresión que SPEC-042 teme es de integración
UI↔contrato SSE↔descargas; el doble `frontend/tests/fakeCadService.ts` ya documenta la
forma del contrato y aquí se reutiliza esa misma forma sobre un navegador real. Un
proceso aparte añadiría superficie (puerto, ciclo de vida, proxy) sin cubrir más código.

**Progreso sin esperas fijas.** Una respuesta interceptada entrega el cuerpo SSE
completo, con los frames `validando(1) → generando(2) → verificado(3)`; los escenarios de
declinación y de error terminan en `declinado(2)` y `error(2)`. El progreso visible se
comprueba sobre la lista `ol.steps[aria-label="Etapas informadas"]`, que la UI construye
con cada etapa realmente recibida, y sobre el estado terminal (`div.state.verificado`).
Todas las aserciones usan locators con autoespera de Playwright: no hay
`page.waitForTimeout` ni esperas dependientes de tiempo (RNF-2).

### Componentes

- `frontend/playwright.config.ts`: `testDir: ./e2e`, un solo proyecto `chromium`
  (Supuesto de SPEC-042), `workers: 1`, `trace: retain-on-failure`,
  `screenshot: only-on-failure`, `video: off`, reporte `list` + HTML y `webServer` que
  levanta `vite preview` en `127.0.0.1:4173` (`--strictPort`).
- `frontend/e2e/support/fakeCadService.ts`: backend simulado. Reproduce la forma de
  eventos de `frontend/tests/fakeCadService.ts` (`event()` con `solicitud_id`, `estado`,
  `secuencia`, `terminal`, `cancelacion_solicitada` y extras `motivo`/`resultado`) y
  responde `/v1/auth/me`, `POST /v1/generar` (SSE con `X-Solicitud-ID` y
  `X-Download-Token`), `GET|DELETE /v1/generaciones/job1` y los `HEAD|GET` de
  `/archivos/{step,glb,csv}`. Registra las peticiones recibidas para poder afirmar que
  la descarga viaja con el token. Una ruta no prevista responde 404 con su nombre, de
  modo que un escenario falla en su aserción en vez de pasar en silencio.
- `frontend/e2e/happy-path.spec.ts` (RF-1), `declination.spec.ts` (RF-2) y
  `model-error.spec.ts` (RF-3): los tres escenarios de AC3.
- `frontend/e2e/support/acciones.ts`: navegación al shell (`/` redirige a
  `/nueva-solicitud`) y envío de la descripción; evita duplicar los pasos en cada spec.
- `Makefile`: `make e2e-install` (solo Chromium) y `make e2e`, que depende de
  `frontend-build` para no probar nunca un build viejo.
- `.github/workflows/ci.yml`, job `e2e`: instala Node 24, el frontend desde el lockfile,
  **solo Chromium** y corre `make e2e`; con `if: failure()` publica
  `frontend/test-results/` (captura y traza) y `frontend/playwright-report/`.
- `.gitlab-ci.yml`, job `e2e`: la misma suite sobre `node:24-bookworm`, con los mismos
  artefactos en `on_failure`. No abre una segunda puerta de integración.
- `tests/test_ci_parity.py`: guarda nueva que exige la suite y sus artefactos en las dos
  puertas, y que `make e2e` dependa de `frontend-build`.
- `frontend/tsconfig.json`: `e2e/**/*.ts` y `playwright.config.ts` entran en
  `vue-tsc --noEmit`, así que `make check` tipa también los escenarios.
- `.gitignore`: `frontend/test-results/`, `frontend/playwright-report/`,
  `frontend/blob-report/` y `frontend/.playwright/`.

### Configuración

| Elemento | Valor | Uso |
| --- | --- | --- |
| `@playwright/test` | `1.65.1` (exacta, como el resto del repo) | Runner y navegador de los E2E. |
| Navegador | `chromium` solamente | Supuesto de SPEC-042: una matriz completa queda fuera de alcance. |
| `baseURL` / `webServer` | `http://127.0.0.1:4173`, `--strictPort` | `vite preview` del build real; si el puerto está ocupado, falla en vez de usar otro servidor. |
| `trace` / `screenshot` | `retain-on-failure` / `only-on-failure` | AC2: evidencia ante fallo, sin ruido cuando todo pasa. |
| `workers` / `retries` | `1` / `0` | Determinismo: el orden no depende de la concurrencia y un fallo no se reintenta a ciegas. |
| `outputDir` / reporte | `frontend/test-results/`, `frontend/playwright-report/` | Rutas que publica CI y que `.gitignore` excluye. |

### Compatibilidad y seguridad

- **Vitest sigue siendo la suite de componentes** (RNF-3): `npm test` es `vitest run`;
  los E2E viven en `npm run e2e` y en `make e2e`, fuera de `make check` y de
  `make frontend-check` (necesitan navegador y no bloquean el ciclo corto).
- No se modifican `frontend/src/**`, `src/m2_cad/**` ni los contratos OpenAPI. El único
  cambio en `frontend/package.json` y `package-lock.json` es la dependencia de desarrollo
  de Playwright y su script.
- El token de descarga del backend simulado es un literal de prueba
  (`token-simulado-hu41`); no hay claves, ni URLs del modelo, ni red externa.
- El escenario de error afirma que el DOM no expone claves, URLs ni trazas, que es el
  contrato de `publicMessage` en `frontend/src/api.ts`.

### Fuera de alcance

Modelo real, núcleo geométrico real, matriz completa de navegadores, auditoría de
accesibilidad (SPEC-041) y pruebas E2E de las vistas de historial (HU-37) y ajustes.

## Verificación

1. `make check` (Ruff, contratos, tipos OpenAPI, Vitest, TypeScript, build y
   pytest/cobertura, incluida la guarda nueva de paridad).
2. `make e2e` con los tres escenarios en verde sobre el build real.
3. AC1 reproducido en local: se rompe a propósito la descarga del STEP en
   `frontend/src/views/NewRequestView.vue`, Vitest sigue en verde y el E2E falla con
   captura y traza; se revierte sin commitear.
4. Evidencia en [`evidence.md`](./evidence.md) al cerrar la historia.
