# Evidencia de implementación · HU-52 (SPEC-053)

## Alcance y punto de partida

- **Rama**: `feature/hu-52-ab-prompts-modelos`, creada desde `feature/hu-44-banco-ci-replay`
  (`358a557`) porque SPEC-045 sigue en revisión en PR #151. El PR final apunta a `main`
  ([PR #154](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/154));
  cuando se fusione #151 el diff queda limitado a HU-52. Se integró `origin/main` en la
  rama: el único conflicto fue el historial de `CONSTITUTION.md` y se resolvió conservando
  las filas de HU-40, HU-44 y HU-52.
- **Spec-first**: [`plan.md`](./plan.md) y [`tasks.md`](./tasks.md) se escribieron antes del
  código; este archivo consigna la ejecución y sus límites reales.
- **Estándar `@jan-project-standard`**: auditoría no destructiva del repo antes de tocar nada
  (`5 OK`, `20 DIFIERE`, `0 FALTA`; los `DIFIERE` son personalizaciones legítimas del repo).
  `CONSTITUTION.md` se actualiza en el mismo commit del código; sin `--no-verify`.
- **Sin red, API key ni GPU**: no hay `DEEPSEEK_API_KEY` en el entorno. No se ejecutó una
  comparación real contra el proveedor; la evidencia de AC1 usa MLflow simulado y la
  demostración de CLI usa replay con respuestas sembradas de HU-44 (`origen: referencia-banco`).

## Qué se implementó

| Pieza | Evidencia |
|---|---|
| `src/m2_cad/prompts.py` | `cargar_version(id, version, raiz=None)` nuevo, aditivo al contrato de SPEC-034; `cargar()` sigue devolviendo `planner-v1` como vigente. |
| `prompts/planner-v2.txt` + `prompts/manifest.toml` | Segunda versión registrada (`sha256 0824e516…`), `vigente = false`; `planner-v1` no se editó. |
| `src/m2_cad/ab.py` | `Variante`, fijación/restauración de prompt y modelo, dos corridas `m2-cad-ab`, métricas por familia, casos cambiados y Markdown. Sin selección de ganador. |
| `src/m2_cad/banco_replay.py` | `cargar`/`preparar` aceptan `prompt_esperado` y `modelo_esperado` opcionales; por defecto conservan la validación de HU-44. |
| `scripts/comparar_ab.py` | CLI con modos real/replay; en replay infiere el modelo del artefacto si no se da `--modelo-*`. Salidas `0` (comparación) y `2` (configuración/artefacto inválido). |
| `Makefile` | `make ab` (real, gasta tokens) y `make ab-replay`; `scripts/comparar_ab.py` entra en `make lint`. Ninguna comparación real entra en CI. |
| `tests/test_hu52_ab.py` | 6 pruebas AC1–AC3, RNF-1–RNF-3, replay por variante y rechazo de artefacto ajeno. |
| `README.md`, `CONSTITUTION.md`, `specs/README.md`, `spec.md` | Documentación de uso, decisión técnica y estado en la misma rama. |

## Criterios de aceptación

| AC | Cómo se verificó | Resultado |
|---|---|---|
| AC1 · dos corridas A/B | `test_ac1_dos_corridas_mlflow_con_trazabilidad` intercepta `seguimiento.iniciar_corrida`: dos corridas en `m2-cad-ab`, `comparacion_id` común, estado `completado`, métricas registradas. | ✅ |
| AC2 · reporte por familia y casos cambiados | `test_ac2_reporte_por_familia_y_casos_cambiados`: `plate` 2→1 piezas conformes; `fuera_alcance` 2→1 declinaciones correctas y 1 error silencioso; casos `HU02-P02` y `HU02-N01` marcados. Markdown y JSON escritos. | ✅ |
| AC3 · trazabilidad | `test_ac3_prompt_y_modelo_se_fijan_y_se_restauran`: cada evaluación ve el prompt/modelo de su variante; se conservan etiquetas `prompt_version`, `prompt_sha256`, `modelo`, `version_modelo`; los globales del pipeline se restauran. | ✅ |
| RF-5 / RNF-1 | CLI ejecutada en replay sin red, API key ni tokens; las pruebas no usan MLflow real ni GPU. | ✅ |
| RNF-2 | `test_rnf_mismo_banco_temperatura_y_variantes_distintas`: mismo banco y `TEMPERATURA_LLM = 0.1`; variantes idénticas o replay parcial se rechazan. | ✅ |
| RNF-3 | El JSON y el Markdown no contienen `ganador`/`promovida`; el campo `promocion` dice «decisión explícita». | ✅ |

## Validaciones ejecutadas

| Comando (host local, Python 3.12 del `.venv`) | Resultado |
|---|---|
| `.venv/bin/ruff check src tests scripts` | ✅ Todos los archivos pasan (`E, F, I, B`). |
| `.venv/bin/ruff format --check` sobre los 5 archivos Python de HU-52 | ✅ 5 archivos ya formateados. El chequeo de todo el repo señala 4 archivos preexistentes no tocados por HU-52 (`api.py`, `seguridad_ci.py`, `test_api_seguimiento.py`, `test_declinacion.py`). |
| `.venv/bin/pre-commit run --files …` sobre todos los archivos de la rama | ✅ Ruff, ruff-format, higiene y bloqueo de pesos: `Passed`. |
| `pytest tests/test_hu52_ab.py tests/test_prompts.py tests/test_hu44_banco_replay.py` | ✅ 47 pruebas pasan; 3 `FutureWarning` de CadQuery. |
| `pytest --cov=src/m2_cad --cov-report=term -q` (tras integrar `main`) | 750 pasan, 1 falla preexistente, cobertura total **91,85 %** (umbral 70 %). Antes de la fusión de `main`: 708 pasan y 91,71 %. |
| `scripts/generate_api_contract.py --check` | ✅ Contrato OpenAPI v1 actualizado (el prompt no cambia la API). |
| `scripts/generate_api_types.py --check` | ✅ Tipos OpenAPI actualizados. |
| `scripts/verify_prompts.py` | ✅ 3 versiones verificadas por hash. |
| `npm --prefix frontend test` / `run typecheck` / `run build` | ✅ 82 pruebas, typecheck y build correctos. |
| CLI A/B en replay (2 casos, artefactos por variante) | ✅ `exit=0`; dos corridas simuladas, acierto 1.0, 0 cambios, reporte `ab-20261127T155118Z.md`. |
| CLI con artefacto de otra variante | ✅ `exit=2` con mensaje que nombra el modelo/prompt divergente. |
| CI del PR #154 | ✅ `test` (run `46029545532`, 2 m 2 s), `e2e`, `secretos`, `dependencias` y `espejo` en verde. |

### Fallo preexistente de la suite

`tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia`
falla en este host macOS x86_64 con 8 huellas STEP distintas por OCCT (por ejemplo
`acepta-plate-hu02-p05`: esperada `4105a43a…`, obtenida `61c6844c…`). NO fue introducido
por HU-52 y pasa en CI Linux. Las 6 pruebas nuevas y las 41 relacionadas pasan aquí.

### Límite local

`make check` no arranca en este host: `uv run --locked` no resuelve `nlopt==2.11.0` para
`macosx_13_0_x86_64`. Por eso se ejecutaron los mismos controles con `.venv/bin/*`,
`uv run --no-sync`, `MLFLOW_TRACKING_ENABLED=0` y un `M2_DOWNLOAD_SECRET` efímero de 32 bytes.
Los hooks de pre-commit se corrieron sobre los archivos de la rama, no con `--all-files`,
para no reescribir los 4 archivos preexistentes con formato distinto.

## Salida de la demostración en replay

```text
Comparación replay-hu52: 2 casos, modo replay.
  A: planner-v1 @ modelo-a · acierto=1.000 · declinaciones=1
  B: planner-v2 @ modelo-b · acierto=1.000 · declinaciones=1
  cambios: 0 · reporte: .../salida/ab-20261127T155118Z.md
```

Los artefactos de la demostración y el reporte quedaron fuera del repositorio, en
`/private/var/folders/3f/mxy98r_n5zvc17dggb1nj69h0000gn/T/hu52-replay/`. No se versionan:
el repo guarda código, prompts y documentación, no evidencia pagada ni pesos.

## Estado final

- Código, pruebas y documentación completos en la rama; sin cambios sin commitear al cierre.
- Comparación real documentada pero **no ejecutada** localmente: requiere API key y gasto
  de tokens. La evidencia disponible cubre la lógica completa con modelos simulados y replay.
- PR #154 abierto, `MERGEABLE`, con todos los checks en verde; pendiente de aprobación y de la fusión de #151 (la protección de `main` marca `BLOCKED` hasta la revisión).
