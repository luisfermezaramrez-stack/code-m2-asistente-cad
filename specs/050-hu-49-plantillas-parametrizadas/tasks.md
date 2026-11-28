# Tareas · HU-49 (SPEC-050)

Orden de ejecución; la evidencia final vivirá en `evidence.md`. Plan aprobado por el humano
antes de empezar la fase 2.

- [ ] T0 · Plan y decisiones abiertas aprobados (este commit).
- [ ] T1 · `data/plantillas.toml` + `src/m2_cad/plantillas.py` (`cargar`, `verificar`,
  `instanciar`, `derivar_parametros`) + `scripts/verify_plantillas.py` +
  `make plantillas-check` dentro de `make check` y del `job lint` del espejo, con su guarda
  en `tests/test_ci_parity.py`; pruebas en RED de `tests/test_plantillas.py`.
- [ ] T2 · Instanciación sin LLM: validación de rangos antes de construir (AC2), reutilizo
  de `_construir_programa` y prueba de que `generar_pieza` no se invoca (AC1, RNF-1).
- [ ] T3 · Persistencia de plantillas guardadas con propietario (`data/plantillas.json`,
  atómica) y derivación de parámetros ±50 % desde el programa (RF-3).
- [ ] T4 · Endpoints `GET /v1/plantillas`, `POST /v1/plantillas`,
  `POST /v1/plantillas/{id}/instanciar` con `usuario_actual` y `garantizar_propietario`;
  regenerar `contracts/openapi-v1.json` y `frontend/src/generated/api.ts`.
- [ ] T5 · Pruebas de AC1, AC2, AC3 (firma geométrica) y aislamiento entre usuarios en
  `tests/test_hu49_plantillas.py`, más no regresión del flujo por texto, del CSV del BOM y
  de los endpoints tocados.
- [ ] T6 · UI: `frontend/src/views/TemplatesView.vue`, ruta y nav, llamadas en
  `frontend/src/api.ts`, pruebas Vitest y un escenario E2E en `frontend/e2e/`.
- [ ] T7 · Documentación: `specs/README.md` (filas 036 y 050), `plan.md`, `tasks.md`,
  `README.md`, `CONSTITUTION.md` (§4, §6, §9 si cambia la arquitectura) y `evidence.md`.
- [ ] T8 · `make corpus-dorado` y `make check` en verde con `M2_DOWNLOAD_SECRET`; commits
  por unidad; sin push ni PR.
