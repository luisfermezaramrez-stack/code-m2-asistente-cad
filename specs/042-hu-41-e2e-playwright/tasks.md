# Tareas · HU-41 (SPEC-042)

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [x] T0 · Leer SPEC-042, `CONSTITUTION.md`, `AGENTS.md`, el frontend (shell, SSE,
  descargas) y los dos pipelines; auditoría no destructiva en un worktree propio.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Crear `frontend/playwright.config.ts` con un solo Chromium, `trace:
  retain-on-failure`, `screenshot: only-on-failure` y `vite preview` del build real.
- [x] T3 · Escribir `frontend/e2e/support/fakeCadService.ts` con la forma de eventos SSE
  del doble de Vitest sobre las rutas reales `/v1` (RF-4, RNF-1).
- [x] T4 · Escribir los tres escenarios: `happy-path.spec.ts` (RF-1), `declination.spec.ts`
  (RF-2) y `model-error.spec.ts` (RF-3), sin esperas fijas (RNF-2).
- [x] T5 · Añadir `make e2e` y `make e2e-install`, el script `e2e` de `package.json`, la
  dependencia exacta `@playwright/test@1.65.1`, `e2e/**` en `tsconfig.json` y los
  artefactos de Playwright a `.gitignore`.
- [x] T6 · Añadir el job `e2e` a `.github/workflows/ci.yml` (solo Chromium) con captura y
  traza como artefactos en `if: failure()` (RF-5, AC2).
- [x] T7 · Añadir el job `e2e` al espejo `.gitlab-ci.yml` y la guarda de paridad en
  `tests/test_ci_parity.py`; actualizar el recuento de jobs en `CONSTITUTION.md`.
- [x] T8 · AC1: romper la descarga del STEP, comprobar que Vitest sigue en verde y el E2E
  falla, y revertir sin commitear.
- [x] T9 · Documentar `README.md`, `frontend/README.md`, `specs/README.md`,
  `CONSTITUTION.md` y esta carpeta; `make check` y `make e2e`; PR con `Closes #101`.
