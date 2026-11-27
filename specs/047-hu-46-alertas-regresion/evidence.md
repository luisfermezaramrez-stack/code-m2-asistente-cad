# Evidencia · HU-46 (SPEC-047)

Rama: `feature/hu-46-alertas-regresion` (creada desde `feature/hu-44-banco-ci-replay`).
PR: pendiente de creación; apunta a `main` y depende de #151 (SPEC-045), que sigue en
revisión. No se fusiona nada antes de la aprobación de esa dependencia.

## Implementación

- `src/m2_cad/alertas.py`: módulo puro, esquema v1 del baseline, métricas por caso,
  deltas contra umbrales del artefacto, desglose por familia/causa y Markdown de alerta.
- `scripts/verificar_alertas.py`: CLI; salidas `0` sin regresión, `1` con regresión y `2`
  artefacto inválido; `--no-fail` para el workflow programado; `--actualizar-baseline`
  exige `--autor`, `--motivo` y `--corrida-origen` y mantiene `historial`.
- `src/m2_cad/banco.py`: el CSV por caso incluye `causa`, normalizada con
  `declinacion.normalizar()` (catálogo cerrado de SPEC-027). El resumen y `make bench`
  no cambian.
- `data/alertas_baseline.json`: 40 casos, `acierto=1.0`,
  `declinaciones_correctas=10`, `errores_silenciosos=0`, umbrales 0 y una entrada de
  `actualizado` con autor, fecha, corrida `replay-20261127T144002Z`, motivo e issue #106.
- `Makefile`: objetivo `alertas`. `ci.yml`: comparación justo tras `make bench-replay`.
  `banco-baseline.yml`: permiso `issues: write`, comparación con `--no-fail`, apertura de
  issue con `outputs/alertas/ultimo.md` y publicación del artefacto.

## Comandos y resultados

| Comando | Resultado |
|---|---|
| `.venv/bin/ruff check src/m2_cad/alertas.py src/m2_cad/banco.py scripts/verificar_alertas.py tests/test_hu46_alertas.py` y `ruff format --check` | 4 archivos limpios |
| `pytest -q tests/test_hu46_alertas.py` | 8 passed |
| `pytest -q tests/test_hu46_alertas.py tests/test_hu44_banco_replay.py tests/test_banco.py tests/test_declinacion.py tests/test_banco_seguimiento.py` | 57 passed |
| `make bench-replay UMBRAL=1.0` | 40/40, salida 0; CSV con 40 causas válidas |
| CLI `--actualizar-baseline` (creación inicial) | `baseline-replay-20261127T144002Z-20261127T144014Z`, historial 1 |
| `make alertas` sobre esa corrida | salida 0, `regresion=false`, sin `.md` |
| `pytest --cov=src/m2_cad --cov-report=term-missing` (suite completa) | 710 passed, 1 fallo preexistente; cobertura total 90.59 % ≥ 70 % |
| `scripts/verify_prompts.py`, `generate_api_contract.py --check`, `generate_api_types.py --check` | contratos actualizados |
| `npm --prefix frontend test` / `run typecheck` / `run build` | 82 tests, typecheck y build OK |
| `uv run --no-sync python -B scripts/verificar_alertas.py --corrida-dir outputs/banco-replay --no-fail` (ruta del workflow) | salida 0, `regresion=false`, sin Markdown |
| `pre-commit run --files <archivos de la rama>` | todos los hooks pasaron (ruff, ruff-format, whitespace, eof, yaml, json y pesos) |

El único fallo de la suite completa es
`tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia`:
8 huellas STEP distintas en macOS x86_64 con la versión local de OCCT. Es anterior a HU-46,
no toca los archivos de esta rama y pasa en el job Linux de CI.

## Criterios de aceptación

- **AC1**: `test_ac1_regresion...` degrada un caso, exige salida 1, `degradadas` no vacío,
  caso `HU02-P01` en `casos_cambiados` y `DEGRADADA` en `ultimo.md`. El job de CI falla
  porque `make alertas` propaga el código 1.
- **AC2**: `test_ac2_sin_regresion...` exige salida 0, `regresion=false`, ausencia de
  Markdown y bytes del baseline intactos (`make alertas` lo confirma sobre 40 casos reales
  del replay).
- **AC3**: `test_ac3_desglose...` convierte una declinación en error silencioso y comprueba
  en el Markdown la familia `fuera_alcance` y la transición
  `familia_no_soportada → ninguna`. La causa se valida contra el catálogo de SPEC-027.
- **AC4**: `test_ac4_actualizar_baseline...` verifica que sin `--autor` la salida es 2 y que
  con la actualización explícita quedan `por`, `fecha`, `corrida`, `motivo`, `issue` y dos
  entradas en `historial`. Una comparación normal nunca escribe el baseline.

## Límites conocidos

- No hay `DEEPSEEK_API_KEY`, así que el baseline inicial se deriva del replay de HU-44
  (`origen: referencia-banco`): mide estabilidad del pipeline y del prompt, no inferencia
  real del proveedor. La corrida pagada sigue en `banco-baseline.yml` y podrá sustituir la
  referencia mediante el procedimiento explícito de AC4.
- `make check` no arranca en este host: `uv run --locked` no resuelve `nlopt==2.11.0` para
  `macosx_13_0_x86_64`. Se usaron los ejecutables de `.venv/bin` y `uv run --no-sync`,
  que es lo que hacen los targets nuevos. La suite completa se corrió con
  `MLFLOW_TRACKING_ENABLED=0` y un `M2_DOWNLOAD_SECRET` efímero de 32 bytes.
