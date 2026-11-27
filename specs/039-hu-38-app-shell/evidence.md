# Evidencia de implementación · HU-38 (SPEC-039)

- **Fecha**: 2026-11-26
- **Rama**: `feature/hu-38-app-shell`, creada desde `origin/main` en `a2a9dd7`
- **Issue**: [#98](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/98)
- **PR**: se abre desde esta rama; enlace registrado en el índice de specs tras la publicación
- **Especificación**: [spec.md](./spec.md) · [plan.md](./plan.md) · [tasks.md](./tasks.md)

## Alcance entregado

- `frontend/src/router.ts`: `createAppRouter(history)` con `/` → `/nueva-solicitud`, tres vistas y ruta comodín.
- `frontend/src/App.vue`: shell con cabecera, aviso profesional, skip link, navegación, sesión y `RouterView`; la generación vive en `frontend/src/views/NewRequestView.vue`.
- `frontend/src/useGeneration.ts`: borrador y timeout en `localStorage` (`m2-cad-draft`); tema en `m2-cad-theme`.
- `frontend/src/components/VistaEstado.vue`, `frontend/src/estadosVista.ts` y `frontend/src/views/NotFoundView.vue`: estados `vacio`, `cargando`, `error` y ruta desconocida, con clases, colores y textos distintos.
- `src/m2_cad/web.py`: GET/HEAD de `/nueva-solicitud`, `/historial` y `/ajustes` sirven `index.html`; API, `/assets` y rutas desconocidas conservan 404 JSON.
- `CONSTITUTION.md`, `README.md` y `specs/README.md` actualizados en la misma rama.

## Criterios de aceptación

| AC | Prueba | Resultado |
| --- | --- | --- |
| AC1 — URL propia por vista | `router.test.ts`: ruta inicial `/nueva-solicitud`, `href` de los tres enlaces y cambio de vista | `/`, `/historial` y `/ajustes` muestran cada vista; `/` redirige a nueva solicitud. |
| AC2 — Estado recuperable | `router.test.ts`: remount con `createMemoryHistory` y URL copiada | Borrador, timeout y tema recuperados; historial y ajustes se abren directamente desde su URL. |
| AC3 — Estados nuevos diferenciados | `router.test.ts`: `?estado=vacio|cargando|error` en ambas vistas y ruta `/no-existe` | Clases `estado-vista--*`, `role` (`status`/`alert`), `aria-busy`, textos y `.sin-ruta` distintos. |
| AC4 — Navegación sólo con teclado | `router.test.ts`: `Tab`, `Shift+Tab`, `Enter` y skip link | Las tres entradas reciben foco en orden, `Enter` navega y el skip link es enfocable. |
| AC5 — Fallback SPA sin romper 404 JSON | `tests/test_web.py` + `TestClient` sobre build real | Las tres vistas devuelven 200 `text/html`; `/api/no-existe`, `/assets/ausente.js` y `/ruta-desconocida` devuelven 404 `application/json`. |

## Validaciones

- Auditoría no destructiva del estándar (`new_project.py --audit`): **0 FALTA, 21 DIFIERE**; las diferencias son personalizaciones legítimas ya documentadas en `CONSTITUTION.md`.
- `uv run ruff check src tests scripts/...`: **All checks passed**.
- `uv run python scripts/generate_api_contract.py --check`: contrato OpenAPI v1 actualizado.
- `uv run python scripts/generate_api_types.py --check`: tipos OpenAPI actualizados.
- `npm --prefix frontend test`: **81 pruebas en 9 archivos, todas pasan**.
- `npm --prefix frontend run typecheck`: limpio.
- `npm --prefix frontend run build`: correcto; Vite avisa del chunk de `GlbViewer` (>500 kB), conocido y fuera de esta HU.
- `pytest tests/test_web.py -q`: **21 passed**.
- `M2_DOWNLOAD_SECRET` efímero + `pytest tests/test_web.py tests/test_api.py tests/test_sse.py tests/test_seguridad_descargas.py tests/test_hu31_api_v1.py -q`: **116 passed, 3 warnings**.
- `make check`: Ruff, contratos, Vitest, TypeScript, build y cobertura pasan; la etapa `cov` termina con **605 passed, 5 failed** y cobertura **92,15 %** (mínimo 70 %).

## Fallos base verificados

Los cinco fallos restantes de `make check` se reprodujeron **idénticos** en un worktree limpio en `a2a9dd7`, por lo que no son regresión de HU-38:

- `tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia`: 7 huellas STEP distintas con el vendor local.
- `tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas`: `OSError: [Errno 36] Resource deadlock avoided` en `msvcrt.locking`.
- `tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos` y `...::test_ac4_no_borra_directorio_con_enlace_interno`: `OSError: [WinError 1314] El cliente no dispone de un privilegio requerido`.
- `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`: p95 de 82,0 ms en la base (92,4 ms en esta rama), medición local bajo carga.

Los entornos de CI usan Linux y `make vendor`; en este equipo Windows no se pudo ejecutar `make vendor` porque `bash` no está disponible, así que `vendor/constraint-kit` se copió del workspace principal. Ninguno de esos cinco fallos toca módulos añadidos o modificados por HU-38.
