# HU-53 — Evidencias de implementación

**Fecha:** 25 de noviembre de 2026
**Issue:** #113
**Especificación:** SPEC-054 (dependencia arquitectónica: SPEC-037)
**Rama:** `feature/hu-53-autenticacion`
**PR:** [#133](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/133)

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

## 5. Integración con HU-31, HU-32 y HU-45 y correcciones de revisión

La rama nació de `80d7850`; al integrar `main` (`2621414`) y atender la revisión del
PR #133 se corrigió:

| Hallazgo | Corrección | Prueba |
| --- | --- | --- |
| Trabajos de la cola HU-45 sin dueño | La cola guarda `usuario`; consultar, cancelar y descargar resuelven el trabajo con `_trabajo` (cola o gestor) y aplican `garantizar_propietario` | `test_cola_aisla_por_usuario_registra_al_dueno_y_entrega_descargas` |
| El worker registraba `anónimo` | `worker.registrar_terminal` pasa el usuario al CSV y al tag de MLflow | misma prueba |
| Descargas de la cola con 404 (bug de `main`) | `descargar_archivo` usa `_trabajo` | misma prueba |
| Idempotencia y topes de HU-32 por IP/`X-Session-ID` | Con autenticación, la sesión es el usuario y cada usuario tiene su espacio de claves | `test_idempotencia_y_topes_pertenecen_al_usuario` |
| `/auth/*` fuera de `/v1` | Rutas bajo `/v1/auth`; contrato y tipos regenerados; `/v1/uso` exige sesión | `test_auth_se_publica_solo_bajo_v1` |
| 422 sin usuario | El manejador registra el usuario de la cookie válida | `test_entrada_invalida_registra_al_usuario_autenticado` |
| Login sin límite | `LimiteIntentos`: 429 con `Retry-After` antes de derivar la clave | `test_login_limita_intentos_fallidos` |
| Sesión no revocable | La firma incluye el hash vigente del usuario | `test_sesion_se_revoca_al_quitar_usuario_o_cambiar_clave` |
| Enumeración por tiempo | PBKDF2 contra un hash ficticio si el usuario no existe | `test_usuario_inexistente_tambien_deriva_pbkdf2` |
| Configuración inválida respondía 500 | `validar_configuracion()` en el arranque | `test_configuracion_invalida_impide_arrancar` |
| `auth.ts` asumía modo local ante un error | Devuelve `sesionRequerida` | `frontend/tests/auth.test.ts` |
| Migración del CSV en cada escritura | Una comprobación por archivo y proceso | `test_migracion_del_registro_se_comprueba_una_vez_por_archivo` |

Verificación independiente sobre `d604675` (sin bypass del aislamiento; S7 parcial). Se
corrigió en una sola tanda:

| Hallazgo | Corrección | Prueba |
| --- | --- | --- |
| H1: el límite se esquivaba con intentos concurrentes | `LimiteIntentos.intentar` comprueba y anota bajo un lock | `test_login_concurrente_no_supera_el_limite` |
| H2: un acierto de otra cuenta reiniciaba el contador | Contadores por cliente+usuario y por cliente; un acierto retira sólo su marca | `test_login_exitoso_de_otra_cuenta_no_borra_los_fallos`, `test_limite_por_cliente_sobrevive_a_un_acierto` |
| H3: un anónimo escribía en el registro con JSON mal formado | El manejador de 422 responde 401 sin registrar | `test_anonimo_con_json_mal_formado_no_escribe_en_el_registro` |
| H5: el texto del 404 distinguía «ajeno» de «inexistente» | Mismo detalle que el recurso inexistente | `test_recurso_ajeno_responde_igual_que_uno_inexistente` |
| H6: un hash con 0 iteraciones pasaba la validación | La expresión exige al menos una iteración | `test_hash_sin_iteraciones_es_configuracion_invalida` |

Quedan documentados, sin cambio: H4 (reutilizar un `X-Request-ID` existente deja la
generación fuera del registro; anterior a HU-53, sin fuga de datos), H7 (el logout no
revoca un token copiado; diseño sin estado) y H8 (detrás de un proxy inverso hay que
configurar `--proxy-headers`).

`tests/conftest.py` mantiene la autenticación y la cola apagadas para la batería
heredada; las pruebas de esta sección las activan. Cada prueba se validó por mutación:
al quitar la corrección correspondiente, la prueba falla.

## 6. Limitaciones y verificaciones pendientes

- No se probó OIDC: quedó fuera de alcance por diseño (SPEC-054 y `CONSTITUTION.md`).
- No se ejecutó despliegue Docker real con usuarios cargados; la configuración de
  Compose exige `M2_AUTH_SECRET` y `M2_AUTH_USERS` en el entorno.
- El PR #133 fue abierto el 25 de noviembre de 2026. GitHub Actions (`CI / test`)
  finalizó en **SUCCESS** para el commit de código `5f7220b`; el commit posterior
  sólo documenta el enlace del PR.

## 7. Conclusión

La autenticación, el aislamiento por propietario y la trazabilidad están implementados
y cubiertos por pruebas. Ruff, Vitest, TypeScript, build, generación de tipos, pre-commit
y la suite completa (426 pruebas, 94,26 % de cobertura) estaban en verde en local antes de
integrar `main`. Tras la integración y las correcciones de la sección 5, `make check` pasa
con 481 pruebas de pytest (93,34 % de cobertura) y 58 de Vitest, y el smoke HG-15
(`--simulate-model`) termina correcto.
