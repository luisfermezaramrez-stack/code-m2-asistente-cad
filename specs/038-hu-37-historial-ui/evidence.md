# Evidencia de implementación · HU-37 (SPEC-038)

- **Fecha**: 2026-11-27
- **Rama**: `feature/hu-37-historial-ui`, creada desde `origin/main` en `3363859` (incluye #142 de HU-38 y #143 de HU-35)
- **Issue**: [#97](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/97)
- **PR**: [#145](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/145)
- **Especificación**: [spec.md](./spec.md) · [plan.md](./plan.md) · [tasks.md](./tasks.md)

## Alcance entregado

- `src/m2_cad/api.py`: `GET /v1/registros` con `RespuestaRegistros`/`RegistroResumen` (`id`, `hora`, `texto`, `estado`, `motivo`), filtros `resultado` y `texto` resueltos en el servidor, sólo filas propias, orden descendente y tope de 200; `_estado_registro`/`_motivo_registro` derivan el estado con precedencia documentada; `GET /v1/registros/{identificador}` devuelve `estado` y `motivo` derivados y emite `X-Download-Token` tras comprobar sesión y propiedad.
- `src/m2_cad/registro.py`: lector público `listar(ruta)` y `leer(identificador, ruta)`, único acceso al CSV; `api._leer_registro` los reutiliza conservando su contrato previo (404 puntual, 422 con id mal formado).
- `contracts/openapi-v1.json` y `frontend/src/generated/api.ts`: regenerados desde `app.openapi()`; añaden la ruta de colección, sus parámetros, los dos esquemas y la cabecera `X-Download-Token`.
- `frontend/src/api.ts`: helpers de listado y consulta puntual con `signal`, `Artifact` del STEP servido desde el registro, sondeo `HEAD` del GLB vivo y validación del `estado` recibido; se reutilizan `downloadArtifact`, `publicMessage` y `Artifact` sin duplicar la descarga.
- `frontend/src/views/HistoryView.vue`: listado real al montar, filtros por resultado y texto contra el backend, estados `cargando`/`error`/`vacio` derivados de la carga real y sin lectura de `?estado=`.
- `frontend/src/views/HistoryDetailView.vue` y `frontend/src/router.ts`: ruta `/historial/:identificador` (`historial-solicitud`) que reabre la solicitud con su estado y motivo, descarga el STEP y ofrece `GlbViewer` sólo si el trabajo sigue vivo.
- `tests/test_hu37_historial.py`, `frontend/tests/historial.test.ts` y `frontend/tests/fakeCadService.ts`: pruebas de los cuatro criterios y extensión del backend simulado (listado con filtros, consulta puntual con token, STEP y trabajos vivos).
- `odd/tasks/hu-37-historial-ui.md`: documento de trabajo con las specs verbatim y el mapa real del registro y de los tokens de descarga.

## Criterios de aceptación

| AC | Prueba | Resultado |
| --- | --- | --- |
| AC1 — Persistencia ante recarga | `test_ac1_ac2_dos_lecturas_del_mismo_registro_devuelven_lo_mismo`; `historial.test.ts` remonta la app | Dos lecturas del mismo registro y una recarga devuelven las mismas solicitudes; nada queda en `localStorage`. |
| AC2 — Otro equipo | La misma pareja de pruebas, con clientes independientes sobre el mismo CSV | El cliente no guarda historial y el backend prevalece (RNF-1). |
| AC3 — El listado usa un endpoint de listado | `test_ac3_el_listado_devuelve_todas_las_solicitudes_sin_ids_conocidos`; `historial.test.ts` comprueba la petición a `/v1/registros` | El listado llega de `GET /v1/registros` sin que el cliente recorra ids; HU-31 no tenía endpoint de colección y HU-35 sólo exponía versiones de una pieza. |
| AC4 — Reabrir y descargar | `test_rf4_el_step_se_descarga_tras_reiniciar_con_el_token`; `historial.test.ts` reabre y descarga | Con el gestor de trabajos vacío, el token de `GET /v1/registros/{id}` habilita `/step` (200 con el STEP) y sin cabecera sigue respondiendo 403. |

Requisitos funcionales y no funcionales cubiertos: RF-1/RF-2 (listado y filtros), RF-3/RF-4 (reapertura y descargas), RF-5 (endpoint de listado), RNF-1 (sin copia autoritativa), RNF-2 (sin red, API key ni GPU: pipeline inyectado y backend simulado), RNF-3 (`aria-live`, `role="status"`, foco visible y textos de la base de HU-38).

## Evidencia ROJO/VERDE

| Unidad | ROJO observado | VERDE observado |
| --- | --- | --- |
| T2/T4 · listado y token (pytest) | `pytest tests/test_hu37_historial.py -q` → **8 failed**: `assert 404 == 200` en `/v1/registros`, `KeyError: 'registros'` en las demás y `assert None` al faltar `X-Download-Token` | **8 passed**; después del ajuste de coherencia, **9 passed** |
| T8 · estado derivado (pytest) | **1 failed, 8 passed** — `E KeyError: 'estado'` en `tests/test_hu37_historial.py:291` | **9 passed** |
| T6/T7 · UI (Vitest) | `npm --prefix frontend test` → **2 archivos fallidos, 6 pruebas de 87** (las 5 nuevas y la prueba de estados del router) | **10 archivos, 87 pruebas en verde** |
| T8 · sin derivación en el cliente (Vitest) | **1 failed | 87 passed (88)** — `AssertionError: expected 'Construida' to be 'Declinada'` | **88 passed (88)** |

## Validaciones

- `uv run python -m pytest tests/test_hu37_historial.py -q`: **9 passed**.
- `uv run ruff check src tests`: **All checks passed!**
- `make api-contract` y `make api-types`: contrato y tipos escritos desde `app.openapi()`.
- `make api-contract-check` y `make api-types-check`: **Contrato OpenAPI v1 actualizado** y **Tipos OpenAPI actualizados** (exit 0).
- `uv run python -m pytest tests/test_hu31_api_v1.py tests/test_hu37_historial.py -q`: **26 passed**.
- `uv run python -m pytest tests/test_hu53_autenticacion.py -q`: **29 passed** (aislamiento por usuario intacto).
- `npm --prefix frontend test`: **88 passed** en 10 archivos, después del último ajuste de la vista de detalle.
- `npm --prefix frontend run typecheck`: limpio (`vue-tsc --noEmit`).
- `npm --prefix frontend run build`: correcto; se mantiene el aviso conocido del chunk de `GlbViewer` (>500 kB).

## Unidades de trabajo

| Commit | Unidad | Contenido |
| --- | --- | --- |
| `83a8790` | Backend y contrato | `GET /v1/registros`, token en la consulta puntual, lector del registro, contrato y tipos regenerados, `tests/test_hu37_historial.py`. |
| `5dec3de` | UI | Helpers de `api.ts`, `HistoryView`, `HistoryDetailView`, ruta de reapertura, doble de prueba y pruebas Vitest. |
| documentación | Docs | `plan.md`, `tasks.md`, `evidence.md`, `CONSTITUTION.md`, `README.md` e índice de specs. |


`make check` no puede concluir en verde en este equipo Windows por causas ambientales, y se comprobó que **no son regresión de HU-37**:

- **Etapas previas a `cov`**: `make check` ejecuta `lint`, `prompts-check`, `api-contract-check`, `api-types-check` y `frontend-check` **antes** de `cov`; la corrida llegó hasta la etapa `cov` y falló allí (`Makefile:61`), lo que prueba que las cinco etapas anteriores pasaron.
- **`tests/test_api.py` (8 fallos)**: verificación diferencial independiente sobre `origin/main` (`3363859`): **8 failed, 13 passed** en la base y **8 failed, 13 passed** en la rama, con la **misma lista de identificadores** y el mismo mensaje `RuntimeError: Configure M2_DOWNLOAD_SECRET con un secreto aleatorio de al menos 32 bytes.` (`src/m2_cad/seguridad_descargas.py:35`). `tests/conftest.py` no define esa variable y es byte-idéntico en ambos árboles. Con un secreto de 48 bytes, **ambos árboles pasan 21/21**, lo que aísla la variable de entorno como única causa.
- **Suite completa, `origin/main` frente a la rama**: en `origin/main` sin el secreto, `uv run python -m pytest -q --tb=line` da **51 failed, 634 passed, 10 errors**; los 61 ítems son `M2_DOWNLOAD_SECRET` (45 fallos + 10 errores de preparación + 3 cascadas en `test_sse.py`) y 3 más por dependencias Node ausentes en un árbol limpio (`test_api_types.py` ×2 y `test_web.py`, que exigen `npm ci`/`vite build`). Con el secreto, la base queda en **692 passed, 3 failed** (cobertura 92,03 %), y esos 3 son los de dependencias Node.
- **La rama, con el secreto definido**: `M2_DOWNLOAD_SECRET=… uv run python -m pytest -q` → **704 passed, 0 failed**. Los 58 ítems que fallaban sin el secreto (48 fallos + 10 errores) coinciden exactamente con el conjunto ambiental de la base, y los 9 tests nuevos de HU-37 explican el salto de 695 a 704.
- **Conclusión**: el fallo de `make check` es exclusivamente de preparación del entorno. La CI de `main` instala el frontend y define `M2_DOWNLOAD_SECRET` efímero antes de `make check` (`.github/workflows/ci.yml`), que es justo lo que hace falta aquí y lo que se aplicó para obtener el 704/704.
