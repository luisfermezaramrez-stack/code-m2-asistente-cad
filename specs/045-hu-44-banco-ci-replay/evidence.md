# Evidencia de implementación · HU-44 (SPEC-045)

- **Fecha**: 2026-11-27
- **Rama**: `feature/hu-44-banco-ci-replay`, creada desde `origin/main` (`094fe9b`)
- **Issue**: [#104](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/104)
- **PR**: [#151](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/151)
- **Especificación**: [spec.md](./spec.md) · [plan.md](./plan.md) · [tasks.md](./tasks.md)

## Alcance entregado

- `src/m2_cad/banco_replay.py`: artefacto `data/banco_replay.json` versionado (`VERSION = 1`),
  validación de esquema, prompt (`id`, `versión`, `sha256`, `etiqueta`), modelo y cobertura de
  los 40 casos antes de correr; proveedor en memoria con clave canónica y `usage` en cero.
- `src/m2_cad/llm_resiliente.py`: `clave_cuerpo(cuerpo, url)` extrae la normalización de la
  caché de SPEC-026 sin incluir la credencial, para que el mismo artefacto sirva en CI sin key.
- `src/m2_cad/pipeline.py`: `cuerpo_planificador()` es la única definición del cuerpo enviado
  al planificador; `_respuesta_modelo` la reutiliza.
- `src/m2_cad/banco.py`: banderas `--replay`, `--respuestas` y `--umbral` (1.0 por defecto),
  con URL ficticia para evitar API key/red, resumen enriquecido y códigos de salida 1
  (umbral) y 2 (artefacto inválido). `make bench` permanece intacto.
- `scripts/verify_banco_replay.py` y `make bench-replay`: verificación de CI; `--solo-verificar`
  y `--grabar` para mantenimiento del artefacto.
- `.github/workflows/ci.yml`: paso `Banco en replay con respuestas grabadas` tras el corpus
  dorado. `.github/workflows/banco-baseline.yml`: lunes 03:17 UTC y `workflow_dispatch`, con
  `DEEPSEEK_API_KEY`, `MLFLOW_TRACKING_URI` y artefactos del resumen.
- Documentación: `README.md`, `CONSTITUTION.md` y `specs/README.md` actualizados en la rama.

## Criterios de aceptación

| AC | Resultado verificado |
|----|----------------------|
| **AC1** · Caída de aceptación detectada sin tokens | `make bench-replay UMBRAL=1.0`: 40/40 correctos, `acierto = 1.0`, `tokens_entrada = tokens_salida = 0`, `costo_usd = 0.0`, salida 0. `tests/test_hu44_banco_replay.py::test_ac1_bajo_el_umbral_el_banco_falla_y_deja_el_resumen` degrada un caso y verifica salida 1 con `umbral = 1.0` y JSON escrito. `test_ac1_replay_no_llama_al_modelo_y_gasta_cero_tokens` sustituye `llm.chat` por una función que falla si se llama: no se invoca. |
| **AC2** · Corrida real programada con baseline en MLflow | Workflow `banco-baseline.yml` configurado con `schedule` y `workflow_dispatch`; corre `python -m m2_cad.banco` (la corrida padre de `banco.py` ya registra params/métricas en `m2-cad-banco`) y publica CSV/JSON. **No ejecutado localmente**: no hay `DEEPSEEK_API_KEY`; su primera ejecución real queda para el entorno con secretos. |
| **AC3** · Respuestas versionadas con la versión del prompt | `data/banco_replay.json` declara `prompt = planner-v1` con `sha256 = b64b187d…b41b6d3`; las 40 respuestas repiten `prompt_version = planner-v1`. `test_cargar_rechaza_un_prompt_distinto_del_vigente` cambia la versión y obtiene `ErrorReplay` antes de correr. |

## Validaciones ejecutadas

| Comando | Resultado |
|---------|-----------|
| `.venv/bin/ruff format …` + `.venv/bin/ruff check src tests scripts/verify_banco_replay.py` | 3 archivos reformateados; `All checks passed!` |
| `pre-commit run --files <archivos de la rama>` | 8 hooks en verde (Ruff, formato, whitespace, fin de archivo, YAML y JSON) |
| `pytest -q tests/test_hu44_banco_replay.py` | **7 passed** en 23 s |
| `pytest -q tests/test_banco.py tests/test_banco_seguimiento.py tests/test_hu25_resiliencia.py tests/test_hu25_ac3_mensajes.py tests/test_prompts.py tests/test_ci_parity.py` | **96 passed** en 8 s |
| `pytest -q --cov=src/m2_cad --cov-report=term` (con `M2_DOWNLOAD_SECRET` efímero) | **702 passed, 1 failed**; cobertura **91.67 %** (≥ 70 %) |
| `npm --prefix frontend ci` → `npm test` → `npm run typecheck` → `npm run build` | **82 passed**, TypeScript limpio, build correcto |
| `uv run --no-sync python -B scripts/verify_prompts.py` | 2 prompts verificados por hash |
| `uv run --no-sync python scripts/generate_api_types.py --check` | Tipos OpenAPI actualizados |
| `uv run --no-sync python scripts/generate_api_contract.py --check` | Contrato OpenAPI v1 actualizado |
| `uv run --no-sync python -B scripts/verify_banco_replay.py --solo-verificar` | `replay válido: 40 respuestas, prompt planner-v1, origen referencia-banco` |
| `make bench-replay UMBRAL=1.0` | 40/40 correctos; `acierto=1.0`, `tokens=0`, `costo=0.0`; salida 0 |
| CI del PR [#151](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/151) ([run 46013610033](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46013610033)) | **Verde**: `test` (incluye `Corpus dorado` y `Banco en replay`), `e2e` y `Seguridad` ✓ |

### Fallo preexistente aislado

`tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia`
falla en este host con huellas STEP distintas para `acepta-screw-hu02-p26` y
`acepta-screw-hu02-p30`. Se reprodujo **antes** de crear la rama y no guarda relación con
HU-44: es una divergencia del OCCT de macOS x86_64 respecto del congelado en CI (Linux).
El resto de la suite (702 pruebas) pasa y el mismo test **sí pasa en el CI del PR #151**.
No se regeneró el corpus para ocultar la diferencia.

### Limitaciones del entorno local

- `make check` no puede arrancar aquí: `uv run --locked` intenta resolver `nlopt==2.11.0`,
  que no publica wheel para `macosx_13_0_x86_64`. Se ejecutaron sus equivalentes con el
  `.venv` existente y `uv run --no-sync` (Ruff, prompts, contrato, tipos, Vitest, TypeScript,
  build y pytest con cobertura). CI corre en Linux con `CFLAGS="-std=gnu17"` y no tiene esta
  limitación.
- El `node_modules` inicial estaba incompleto (`vue-router` ausente); tras `npm ci` desde
  `package-lock.json`, la verificación del frontend quedó en verde.
- `pre-commit run --all-files` toca archivos sin relación con esta HU (deriva de formato ya
  existente en `api.py`, `corpus_dorado.py`, `seguridad_descargas.py`, tres tests y tres specs
  antiguas). Esos cambios se revirtieron y la verificación final se limitó a los archivos de
  la rama, que pasan los 8 hooks.
- No hay credencial del proveedor en el host, por lo que las respuestas sembradas son
  **referencias derivadas del banco** (`origen: referencia-banco`), no inferencias pagadas.
  `python scripts/verify_banco_replay.py --grabar` está listo para reemplazarlas por
  respuestas reales (`origen: proveedor`) en un entorno con `DEEPSEEK_API_KEY` y ejecutar
  después el workflow de baseline. Esta distinción está declarada en el propio JSON y en el
  resumen de la corrida.

## Impacto en dependencias

- SPEC-026 (reintentos/caché) y SPEC-034 (prompts) se consumen sin modificar sus contratos.
- Desbloquea SPEC-047 (alertas de regresión) y SPEC-053 (A/B de prompts/modelos); ninguna de
  las dos se implementa aquí.

## Key Learnings:

1. La clave de caché de HU-25 incluye la huella de la credencial: reutilizarla tal cual habría
   impedido que un artefacto grabado con API key sirviera en CI sin key. Separar
   `clave_cuerpo()` (sin secreto) de `_clave()` (con huella) resuelve ambos casos.
2. `_respuesta_modelo` exige API key cuando la URL contiene `api.deepseek.com`, así que
   parchear sólo `llm.chat` no basta: el replay también debe fijar una URL ficticia.
3. Congelar las respuestas del modelo no mide calidad del modelo, pero congela su
   comportamiento: detecta regresiones del pipeline, del kernel y del prompt sin pagar tokens.
4. Mac x86_64 no puede resolver `nlopt` con `uv --locked` y su OCCT produce huellas STEP
   diferentes; hay que distinguir estos fallos de entorno de los fallos introducidos por un PR.
