# HU-41 — Evidencias de implementación

**Fecha:** 27 de noviembre de 2026
**Issue:** #101
**Especificación:** SPEC-042 (dependencia: SPEC-039)
**Rama:** `feature/hu-41-e2e-playwright`
**PR:** [#144](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/144)

## 1. Implementación

Los E2E prueban el **build real** de la SPA y un **backend simulado dentro del test**:

- `frontend/playwright.config.ts`: `testDir: ./e2e`, un solo proyecto `chromium`,
  `workers: 1`, `retries: 0`, `trace: retain-on-failure`, `screenshot: only-on-failure`,
  `video: off`, reporte `list` + HTML y `webServer` que levanta `vite preview` en
  `127.0.0.1:4173` con `--strictPort` sobre `frontend/dist`.
- `frontend/e2e/support/fakeCadService.ts`: backend simulado con `page.route('**/v1/**')`.
  Reutiliza la forma de eventos de `frontend/tests/fakeCadService.ts` (`event()`:
  `solicitud_id`, `estado`, `secuencia`, `terminal`, `cancelacion_solicitada`, más los
  extras `motivo` y `resultado`) y responde `/v1/auth/me`, `POST /v1/generar` (SSE con
  `X-Solicitud-ID` y `X-Download-Token`), `GET|DELETE /v1/generaciones/job1` y los
  `HEAD|GET` de `/v1/generaciones/job1/archivos/{step,glb,csv}`. Registra cada petición,
  así que la prueba puede afirmar qué se descargó y con qué token. Una ruta no prevista
  responde 404 con su nombre: un escenario falla en su aserción, nunca pasa en silencio.
- `frontend/e2e/support/acciones.ts`: navegación al shell (`/` redirige a
  `/nueva-solicitud`) y envío de la descripción, compartido por los tres escenarios.
- Escenarios: `happy-path.spec.ts` (RF-1), `declination.spec.ts` (RF-2) y
  `model-error.spec.ts` (RF-3).
- `Makefile`: `make e2e-install` (solo Chromium) y `make e2e`, que depende de
  `frontend-build` para no probar nunca un build viejo.
- CI: job `e2e` en `.github/workflows/ci.yml` (Node 24, `make frontend-install`,
  `npx playwright install --with-deps chromium`, `make e2e` y
  `actions/upload-artifact@v4` con `if: failure()`) y job `e2e` en `.gitlab-ci.yml`
  (`node:24-bookworm`, misma suite, artefactos con `on_failure`).
  `tests/test_ci_parity.py` gana una guarda que exige la suite, el navegador y los
  artefactos en las dos puertas, y que `make e2e` dependa de `frontend-build`.
- `frontend/package.json`: `@playwright/test` `1.65.1` (exacta) y script
  `e2e: playwright test`. `npm test` sigue siendo `vitest run` (RNF-3).
  `frontend/tsconfig.json` incluye `e2e/**/*.ts` y `playwright.config.ts`, así que
  `make check` tipa también los escenarios. `.gitignore` excluye
  `frontend/test-results/`, `frontend/playwright-report/`, `frontend/blob-report/` y
  `frontend/.playwright/`.

No se modificaron `frontend/src/**`, `src/m2_cad/**` ni los contratos OpenAPI.

## 2. Criterios de aceptación

| AC | Verificación | Resultado |
|---|---|---|
| AC1 — Regresión detectada | Se quitó a propósito `@click="flow.download(file)"` del botón de descarga en `frontend/src/views/NewRequestView.vue`. `npm --prefix frontend test` (Vitest) quedó en **82/82 en verde** y `make e2e` **falló** en `e2e/happy-path.spec.ts` esperando el evento `download` del STEP. Revertido con `git checkout`, sin commitear (`git status` limpio para `frontend/src`). | Cumple: la regresión de integración que Vitest no ve la detecta el E2E. |
| AC2 — Evidencia en el fallo | `trace: retain-on-failure` + `screenshot: only-on-failure`; en cada corrida roja local aparecieron `test-results/<caso>/test-failed-1.png`, `error-context.md` y `trace.zip`, y `playwright-report/`. En CI el job publica `frontend/test-results/` y `frontend/playwright-report/` con `if: failure()`. | Cumple (observado en local; el job quedó en verde, así que el paso de artefactos no llegó a ejecutarse en CI). |
| AC3 — Cobertura de los tres flujos | `make e2e`: flujo feliz, declinación y error del modelo. | Cumple: **3 aprobadas** en 4,7 s en Chromium. |

## 3. Validaciones realizadas

| Validación | Comando | Resultado |
|---|---|---|
| Verificación completa | `make check` | **Verde**: Ruff, `prompts-check`, contrato OpenAPI, tipos OpenAPI, Vitest (**82 aprobadas**, 9 archivos), `vue-tsc`, build y pytest (**696 aprobadas**, 33 advertencias, 66,88 s) con cobertura **92,06 %** (umbral 70 %). |
| Suite E2E | `make e2e` | **Verde**: 3 escenarios aprobados en 4,7 s sobre el build real. |
| Paridad de pipelines | `uv run --locked pytest -q tests/test_ci_parity.py` | **16 aprobadas**. |
| Tipo de los E2E | `npm --prefix frontend run typecheck` | Sin errores (`e2e/**` y `playwright.config.ts` incluidos). |
| CI del PR | Job `e2e` de [CI #45946739885](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/45946739885) y de la corrida del último commit, [CI #45947220661](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/45947220661/job/140334575383) | **Verde** en 35 s y 39 s respectivamente; el resto de jobs del PR (`test`, `secretos`, `dependencias`, `espejo`) también en verde. |
| Hooks | `make precommit` | **No verde en el estado base**: ver sección 5; los hooks sobre los archivos de esta HU pasaron en cada commit. |

## 4. Compatibilidad y seguridad

- Vitest sigue siendo la suite de componentes: `npm test` no cambia y los E2E viven en
  `npm run e2e` / `make e2e`, fuera de `make check` y de `make frontend-check`.
- Sin red externa, API key ni GPU (RNF-1): el token de descarga del backend simulado es
  el literal `token-simulado-hu41` y no hay ninguna URL del modelo en el bundle.
- El escenario de error afirma que el DOM no expone claves, URLs ni trazas, que es el
  contrato de `publicMessage` en `frontend/src/api.ts`.
- Determinismo (RNF-2): `workers: 1`, `retries: 0` y ninguna espera fija; todo espera por
  locator o por estado (`div.state`, `ol.steps li`, `[data-download-filename]`).
- El pipeline del espejo no abre una segunda puerta de integración: el job `e2e` corre en
  la misma etapa `test` y solo sobre la rama por defecto del espejo.

## 5. Integración y correcciones

| Hallazgo | Corrección | Prueba |
|---|---|---|
| Primera corrida del flujo feliz en rojo: `expect(backend.descargas).toEqual(['step'])` fallaba porque el visor 3D también pide el GLB con el mismo token (`['glb','step']`). | La aserción comprueba ambos artefactos y verifica el token en **todas** las peticiones de archivos. | `make e2e` en verde. |
| `make precommit` falla y **modifica archivos ajenos** a la HU: el hook `ruff-format` fijado en `v0.6.9` reformatea 6 archivos de `src/m2_cad` y `tests/`, y `trailing-whitespace`/`end-of-file-fixer` tocan specs de HU-24 y HU-36. | Se revirtieron esos cambios con `git checkout --` y no se commitea nada de ellos; es un desfase preexistente entre la versión del hook y la del Ruff del proyecto. | Los hooks sobre los archivos de esta rama pasaron en los tres commits. |
| Una corrida de `make check` falló en `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms` (umbral de 50 ms bajo carga de la máquina). | Sin cambios: no toca Python. Se repitió tres veces en aislamiento (3/3 verde) y la corrida completa siguiente quedó en 696 aprobadas. | Corrida completa en verde; prueba inestable por umbral de tiempo, ajena a esta HU. |

## 6. Limitaciones

- Solo Chromium (Supuesto de SPEC-042): la matriz de navegadores queda fuera de alcance.
- El cuerpo SSE de una respuesta interceptada llega completo, así que el progreso se
  verifica por la lista de etapas realmente recibidas y por el estado terminal, no
  fotograma a fotograma; el parseo de bytes fragmentados ya lo cubre `sse.test.ts` de
  Vitest, no los E2E.
- No hay E2E de las vistas de historial (HU-37) ni de ajustes: el alcance son los tres
  flujos de SPEC-042.
- El job `e2e` del espejo GitLab no se observó ejecutado: el pipeline solo corre sobre la
  rama por defecto del espejo, después de fusionar. Su paridad queda garantizada por
  `tests/test_ci_parity.py`, no por una corrida vista.
- El paso de artefactos de CI no se ejercitó en el PR (el job quedó en verde); su
  comportamiento se observó en local con la corrida roja de AC1.

## 7. Conclusión

Los tres flujos principales de la SPA se ejecutan en un navegador real contra el build que
se entrega, sin red externa, API key ni GPU, y CI falla si la integración se rompe: se
demostró rompiendo la descarga del STEP, que Vitest no detecta y el E2E sí. La suite de
componentes queda intacta y el espejo GitLab corre la misma verificación.
