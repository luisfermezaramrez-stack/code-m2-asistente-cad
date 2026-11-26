# HU-32 — Evidencias de implementación (SPEC-033)

- **Fecha:** 25 de noviembre de 2026
- **Issue:** #92 · **Rama:** `feature/hu-32-costo-limites-idempotencia`
- **Spec:** [SPEC-033](spec.md) · [Plan](plan.md) · [Tareas](tasks.md)
- **Pull request:** [#131](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/131) contra `main`

## 1. qué se entregó

- `src/m2_cad/control_uso.py`: `ConfiguracionUso`, `ControlUso`,
  `RegistroIdempotencia` y errores tipados (`LimiteVentanaExcedido`,
  `PresupuestoExcedido`, `ConflictoIdempotencia`).
- `src/m2_cad/api.py`: dependencia `obtener_control_uso`, cabeceras
  `Idempotency-Key` y `X-Session-ID`, reserva de cuota antes de crear el trabajo,
  repetición sin costo en JSON y SSE, y `GET /uso`.
- `medir_solicitud` reutiliza el `costo_usd` existente: no calcula un costo nuevo
  ni inventa tokens cuando no hay `usage`.
- `frontend/src/generated/api.ts` regenerado con `make api-types`: incluye
  `RespuestaUso`, la cabecera `Idempotency-Key` y las respuestas 409/429.
- Documentación aditiva en `README.md`, `.env.example`, `CONSTITUTION.md` y
  `specs/README.md`. No se borró ni reemplazó documentación previa.

## 2. Criterios de aceptación

| AC | Evidencia | Resultado |
|----|-----------|-----------|
| AC1 — Presupuesto excedido | `test_ac1_presupuesto_excedido_no_llama_al_modelo`: gasto previo 0,0002 USD con presupuesto 0,0001 → 429, `X-Limite-Tipo=presupuesto`, contador de modelo en 0 | ✅ |
| AC2 — Idempotencia | `test_ac2_idempotencia_no_duplica_gasto_ni_trabajo`: misma clave → misma respuesta, `Idempotent-Replay: true`, mismo `X-Registro-ID`, 1 llamada y 1 generación; `test_ac2_clave_reutilizada_con_otro_texto_conflicta` → 409 | ✅ |
| AC3 — Límite por ventana | `test_ac3_limite_por_ventana_por_sesion`: 2 solicitudes permitidas, la 3.ª → 429 con `X-Limite-Tipo=ventana` y `Retry-After`; otra sesión conserva su cuota | ✅ |
| AC4 — Gasto acumulado | `test_ac4_gasto_acumulado_suma_costo_de_cada_generacion`: dos `usage` simulados → `GET /uso` = 0,0004 USD y 2 generaciones | ✅ |

Cobertura adicional: reintento SSE con estado terminal, configuración inválida,
expiración de ventana, costo no finito y ausencia de clave.

## 3. Requisitos no funcionales

- **RNF-1:** processor y `usage` simulados; sin red, API key ni GPU. Secreto
  `M2_DOWNLOAD_SECRET` efímero generado en la prueba y en CI.
- **RNF-2:** `test_sin_topes_ni_clave_el_comportamiento_no_cambia` y las 376
  pruebas previas de API/SSE siguen pasando sin cabeceras nuevas.
- **RNF-3:** el tope de capacidad de 128 trabajos conserva su 503; los nuevos
  rechazos son 429 tipados y se distinguen por `X-Limite-Tipo`.
- **Supuesto:** contadores en proceso (`--workers 1`), sesión por `X-Session-ID`
  o IP, y día UTC natural. Documentado en `plan.md` y `README.md`.

## 4. Validaciones

| Comando | Resultado |
|---------|-----------|
| `ruff format --check src tests` | 43 archivos ya formateados |
| `ruff check src tests scripts/...` | All checks passed |
| `python scripts/generate_api_types.py --check` | Tipos OpenAPI actualizados |
| `pytest --cov=src/m2_cad --cov-report=term` | **424 passed**, cobertura total **94,54 %** (≥ 70 %) |
| `npm --prefix frontend test` | 50 passed |
| `npm --prefix frontend run typecheck` | sin errores |
| `npm --prefix frontend run build` | build correcto |
| `pre-commit run` sobre los archivos del cambio | todos los hooks pasan |
| CI del PR #131 (`make check` + arranque integrado) | verde, run `45697911049` |

> Nota local: `make check` invoca `uv run --locked`, que en este macOS x86_64
> intenta resolver `nlopt==2.11.0` (sin wheel para esta plataforma). Las mismas
> comprobaciones se ejecutaron con `uv run --no-sync`, que reutiliza el entorno
> fijado; CI corre `make check` con `uv sync --locked` en Linux y no tiene esa
> limitación. No se cambió `uv.lock`.

## 5. Integración con HU-31

HU-32 nace de `origin/main` antes de que se fusionara PR #130 (API `/v1`). Al
integrar `main` en esta rama se resolvió el solapamiento en `api.py`: `GET /uso` se
publica como `GET /v1/uso` en el router versionado (ruta nueva, sin redirección
plana), `POST /v1/generar` documenta `Idempotency-Key` y la respuesta `429`
(`X-Session-ID` se lee de las cabeceras y no figura en el esquema), y se regeneraron `contracts/openapi-v1.json` y `frontend/src/generated/api.ts`.
Según `docs/versionado-api.md`, añadir cabeceras opcionales, una respuesta y una ruta
nueva es compatible con v1. No se ha reescrito ninguna rama ajena.

## Key Learnings:

1. La idempotencia debe evaluarse antes del presupuesto: un reenvío válido tiene que poder devolver la generación original aunque el saldo ya esté agotado.
2. El `X-Download-Token` obliga a fijar `M2_DOWNLOAD_SECRET` incluso en pruebas con modelo simulado; en CI se genera un secreto efímero antes de `make check`.
3. Los hooks de pre-commit fijan Ruff 0.6.9 y pueden reformatear archivos no relacionados; conviene revertir ese ruido y ejecutar los hooks solo sobre los archivos del cambio.
