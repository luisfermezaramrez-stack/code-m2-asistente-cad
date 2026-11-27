# Plan de implementación · HU-52 (SPEC-053)

## Contexto

SPEC-053 depende de SPEC-034 (prompts versionados) y SPEC-045 (banco en replay y corrida
real registrada). PR #151 (SPEC-045) sigue en revisión, así que esta rama se crea desde
`feature/hu-44-banco-ci-replay` y el PR final apunta a `main`; al fusionarse #151 el diff
queda limitado a HU-52. La promoción de una variante nunca es automática (RNF-3): el
comparador sólo produce evidencia.

## Decisiones técnicas

1. **Variante explícita**: `src/m2_cad/ab.py` define `Variante` con prompt cargado por
   id/versión (`prompts.cargar_version`, añadido de forma aditiva a SPEC-034), modelo y
   versión de modelo (`seguimiento.version_modelo()`), más un artefacto de replay opcional.
   Dos variantes usan el mismo banco y la misma temperatura `pipeline.TEMPERATURA_LLM`
   (RNF-2); el comando lo verifica antes de ejecutar.
2. **Ejecución aislada**: para cada variante se fija temporalmente el prompt del
   planificador y el modelo, se corre `banco.evaluar_caso` sobre las mismas filas y se
   restauran los globales en un `finally`. Las corridas reales gastan tokens y viven fuera
   de CI; el modo replay usa respuestas grabadas por variante sin red, key ni tokens.
3. **MLflow** (RF-2, AC1, AC3): una corrida padre por variante en el experimento
   `m2-cad-ab`, con tag `comparacion_id`, `variante`, `prompt_version`, `prompt_sha256`,
   `modelo` y `version_modelo`; los mismos datos como parámetros y las métricas del banco.
   Se agrupan por `comparacion_id`. El seguimiento sigue siendo best-effort.
4. **Reporte** (RF-3, RF-4, AC2): `comparar()` es puro y produce métricas por familia
   (piezas conformes, declinaciones correctas, errores silenciosos, latencia, tokens y
   costo) y la lista de casos que cambiaron de resultado. `markdown()` genera el reporte;
   la CLI escribe JSON y Markdown en `outputs/ab/`.
5. **Sin promoción**: no hay selección automática de ganador; el reporte sólo evidencia
   diferencias para que una persona decida.

## Piezas

| Pieza | Contenido |
|---|---|
| `prompts/planner-v2.txt` + `prompts/manifest.toml` | Segunda versión registrada, no vigente, para la comparación de ejemplo. |
| `src/m2_cad/prompts.py` | `cargar_version(id, version, raiz=None)`, aditivo al contrato de SPEC-034. |
| `src/m2_cad/ab.py` | Variante, ejecución aislada, comparación pura y Markdown. |
| `scripts/comparar_ab.py` | CLI con modo real/replay, IDs y salida; códigos 0/2. |
| `Makefile` | `make ab` (real) y `make ab-replay` (variantes ya grabadas). |
| `tests/test_hu52_ab.py` | AC1–AC3, mismos banco/temperatura, replay y trazabilidad. |

## Verificación

- Ruff y pre-commit sobre los archivos de la rama; pytest específico y suite completa con
  cobertura; contratos y frontend para comprobar que el prompt no cambia el OpenAPI.
- `make prompts-check` y una corrida A/B en replay con dos variantes grabadas.
- Evidencia en `specs/053-hu-52-ab-prompts-modelos/evidence.md`; `CONSTITUTION.md` se
  actualiza en el mismo commit de código.
