# Tareas · HU-49 (SPEC-050)

Orden de ejecución; la evidencia final vivirá en `evidence.md`. Plan aprobado por el humano
antes de empezar la fase 2.

- [x] T0 · Plan y decisiones abiertas aprobados (este commit).
- [x] T1 · `data/plantillas.toml` + `src/m2_cad/plantillas.py` (`cargar`, `verificar`,
  `instanciar`, `derivar_parametros`) + `scripts/verify_plantillas.py` +
  `make plantillas-check` dentro de `make check` y del `job lint` del espejo, con su guarda
  en `tests/test_ci_parity.py`; pruebas en RED de `tests/test_plantillas.py`.
- [x] T2 · Instanciación sin LLM: validación de rangos antes de construir (AC2), reutilizo
  de `_construir_programa` y prueba de que `generar_pieza` no se invoca (AC1, RNF-1).
- [x] T3 · Persistencia de plantillas guardadas con propietario (`data/plantillas.json`,
  atómica) y derivación de parámetros ±50 % desde el programa (RF-3).
- [x] T4 · Endpoints `GET /v1/plantillas`, `POST /v1/plantillas`,
  `POST /v1/plantillas/{id}/instanciar` con `usuario_actual` y `garantizar_propietario`;
  regenerar `contracts/openapi-v1.json` y `frontend/src/generated/api.ts`.
- [x] T5 · Pruebas de AC1, AC2, AC3 (firma geométrica) y aislamiento entre usuarios en
  `tests/test_hu49_plantillas.py`, más no regresión del flujo por texto, del CSV del BOM y
  de los endpoints tocados.
- [x] T6 · UI: `frontend/src/views/TemplatesView.vue`, ruta y nav, llamadas en
  `frontend/src/api.ts`, pruebas Vitest y un escenario E2E en `frontend/e2e/`.
- [x] T7 · Documentación: `specs/README.md` (filas 036 y 050), `plan.md`, `tasks.md`,
  `README.md`, `CONSTITUTION.md` (§4, §6, §9 si cambia la arquitectura) y `evidence.md`.
- [x] T8 · `make corpus-dorado` y `make check` en verde con `M2_DOWNLOAD_SECRET`; commits
  por unidad; sin push ni PR.

## Evidencia de cierre

- T6: sin escenario Playwright; `/plantillas` queda cubierta por Vitest (`frontend/tests/plantillas.test.ts`). Añadirla a la auditoría de accesibilidad E2E es un seguimiento.
- Verificación independiente (item 2, permisos): sin bloqueantes. B no ve ni instancia plantillas de A (404 idéntico al de un id inexistente), las tres rutas dan 401 sin sesión, ninguna respuesta expone `usuario` ni `programa` y los ids raros dan 404 sin construir.
- Hallazgos menores corregidos tras la verificación: la instancia ocupa la ventana por sesión de HU-32 (`reservar_ventana`); `valores` usa tipos estrictos; un entero desbordado da 422; una brida guardada hereda las clases ASME permitidas.
- `make check` en verde: Ruff, Vitest 124/124, pytest 903 y cobertura 90,29 %. `make corpus-dorado`: 15 casos sin divergencias.
