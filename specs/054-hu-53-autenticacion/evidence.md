# HU-53 — Evidencias de implementación

**Fecha:** 25 de noviembre de 2026
**Issue:** #113
**Especificación:** SPEC-054 (dependencia arquitectónica: SPEC-037)
**Rama:** `feature/hu-53-autenticacion`
**PR:** pendiente de creación

## 1. Implementación

Se incorporó autenticación local y aislamiento por usuario sin añadir dependencias:

- `src/m2_cad/autenticacion.py`: configuración por entorno, hashes PBKDF2-SHA256,
  sesiones HMAC-SHA256 en cookie `m2_sesion` (`HttpOnly`, `SameSite=Lax`, `Secure`
  configurable), dependencia `usuario_actual` y control de propiedad.
- `src/m2_cad/usuarios.py` y `make hash-clave`: CLI para generar/verificar hashes sin
  versionar claves; la clave se lee por prompt o desde `M2_CLAVE_NUEVA`.
- `src/m2_cad/api.py`: nuevos `POST /auth/login`, `POST /auth/logout` y `GET /auth/me`;
  el usuario se exige en generación, consulta, cancelación, registros y descargas.
  `/health` y `/ready` permanecen abiertos. El token de HU-36 se sigue exigiendo.
- `src/m2_cad/trabajos.py`: `Trabajo` y `GestorTrabajos.crear` conservan el dueño.
- `src/m2_cad/registro.py`: columna final `usuario` y migración atómica de CSV de
  8 columnas, sin borrar filas; las anteriores se etiquetan como `anónimo`.
- MLflow: tags `usuario` en corridas SSE y JSON; el CSV incluye el mismo valor.
- Frontend: `frontend/src/auth.ts`, formulario y estado de sesión en `App.vue`, con
  generación bloqueada mientras la autenticación esté activa y no haya sesión.
- La rama parte de `origin/main` (`80d7850`), por lo que no incluye la cola de HU-45;
  la propiedad se implanta en el gestor en memoria existente.

## 2. Criterios de aceptación

| AC | Verificación | Resultado |
|---|---|---|
| AC1 — Acceso anónimo rechazado | `test_ac1_ac4_anónimo_no_genera_y_salud_queda_abierta`, `test_cookie_manipulada_o_expirada_no_autentica` | 401 en `/generar`, `/generaciones/{id}`, `/registros/{id}` y cancelación; `/health` 200 y `/ready` distinto de 401; cookie manipulada/expirada sin sesión. |
| AC2 — Aislamiento entre usuarios | `test_ac2_aislamiento_de_trabajos_registro_y_descargas` | El usuario B obtiene 404 al consultar, cancelar, leer el registro o descargar STEP/job de A, aun con token válido; A sí descarga su artefacto. |
| AC3 — Trazabilidad | `test_ac2_aislamiento_de_trabajos_registro_y_descargas`, `test_csv_anterior_se_migra_sin_perder_filas` | Registro con `usuario=ana`, sin clave en claro; filas heredadas migradas a `anónimo`; tags de MLflow con `usuario`. |
| AC4 — Salud abierta | `test_ac1_ac4_anónimo_no_genera_y_salud_queda_abierta` | `/health` y `/ready` accesibles sin cookie; `/auth/me` público informa `requerido`. |

Cobertura adicional: credenciales inválidas, logout, atributos de cookie, expiración y
firma HMAC, modo local explícito, migración de CSV y configuración inválida.

## 3. Validaciones realizadas

Entorno local: macOS x86_64, Python 3.12, `uv`; se usó `uv run --no-sync` porque
`nlopt==2.11.0` no publica wheel para macOS x86_64 (la CI con lock completo es la
referencia reproducible). Se fijó `M2_DOWNLOAD_SECRET` efímero para ejecutar la suite
heredada; HU-53 configura sus propios secretos en cada prueba.

| Validación | Comando | Resultado |
|---|---|---|
| Pruebas HU-53 | `uv run --no-sync pytest -q tests/test_hu53_autenticacion.py` | **12 aprobadas** |
| Ruff lint | `uv run --no-sync ruff check src tests scripts/...` | Sin errores |
| Ruff format | `uv run --no-sync ruff format --check src tests` | 44 archivos ya formateados |
| Tipos OpenAPI | `uv run --no-sync python scripts/generate_api_types.py --check` | Actualizados |
| Vitest | `npm --prefix frontend test` | **57 aprobadas** (5 archivos) |
| TypeScript | `npm --prefix frontend run typecheck` | Sin errores |
| Build SPA | `npm --prefix frontend run build` | Correcto (advertencia no bloqueante de chunk >500 kB) |
| Regresión y cobertura | `uv run --no-sync pytest -q --cov=src/m2_cad --cov-report=term` | **426 aprobadas**, **94,26 %** total; `autenticacion.py` 94 % |
| Smoke HG-15 | `uv run --no-sync python scripts/verify_hu15_deployment.py --simulate-model` | Correcto con `M2_AUTH_ENABLED=0` en el subprocess |
| Pre-commit (archivos preparados) | `uv run --no-sync pre-commit run --files …` | Todos los hooks pasaron |
| `git diff --check` | `git diff --check` | Sin errores |

## 4. Compatibilidad y seguridad

- Modo local explícito: `M2_AUTH_ENABLED=0` conserva el flujo anterior y registra
  `anónimo`; lo usan la batería heredada, el smoke HG-15 y el desarrollo sin sesión.
- Las respuestas ajenas son 404, sin revelar existencia ni contenido. La comprobación
  del token de descarga se mantiene antes de consultar el gestor (contrato HU-36).
- No se versionan secretos: `M2_AUTH_SECRET`, `M2_AUTH_USERS` y hashes reales viven
  en `.env` / entorno. La UI nunca guarda la clave en `localStorage`.
- `.gitignore` excluye el estado transaccional local (`data/*.lock`, `data/cola.json`).

## 5. Limitaciones y verificaciones pendientes

- No se probó OIDC: quedó fuera de alcance por diseño (SPEC-054 y `CONSTITUTION.md`).
- No se ejecutó despliegue Docker real con usuarios cargados; la configuración de
  Compose exige `M2_AUTH_SECRET` y `M2_AUTH_USERS` en el entorno.
- El resultado de CI y el enlace del PR se registran tras la publicación de la rama.

## 6. Conclusión

La autenticación, el aislamiento por propietario y la trazabilidad están implementados
y cubiertos por pruebas. Ruff, Vitest, TypeScript, build, generación de tipos, pre-commit
y la suite completa (426 pruebas, 94,26 % de cobertura) están en verde en local.
