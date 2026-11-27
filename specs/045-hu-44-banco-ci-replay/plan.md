# Plan de implementación · HU-44 (SPEC-045)

- **Rama**: `feature/hu-44-banco-ci-replay`, creada desde `origin/main` (27/11/2026).
- **Dependencias**: [SPEC-026](../026-hu-25-reintentos-cache-llm/spec.md) y
  [SPEC-034](../034-hu-33-prompts-versionados/spec.md), ya cerradas y fusionadas
  (PR #126 y PR #141).
- **Orden**: spec → plan → tareas → código → pruebas → validaciones → evidencia → PR.
- **Estado de partida**: las 4 dependencias indirectas de este MLOps ya están resueltas; HU-44
  es la primera de las cuatro historias pendientes y desbloquea HU-46 y HU-52.

## Objetivo

Medir en cada PR la tasa de aceptación del banco HU-02 **sin gastar tokens ni usar red**, y
conservar una corrida real programada que deje su baseline en MLflow.

## Decisiones de diseño

1. **Respuestas grabadas versionadas en un artefacto JSON.**
   `data/banco_replay.json` guarda, por caso del banco, el contenido de la respuesta del
   proveedor junto con la versión de prompt (`planner-v1`), su `sha256`, el modelo y la clave
   canónica de la petición. `VERSION = 1` y un esquema validado en
   `src/m2_cad/banco_replay.py` hacen explícito cualquier cambio del formato.
2. **La clave reutiliza la canónica de la caché de HU-25.**
   `llm_resiliente.clave_cuerpo(cuerpo, url)` extrae la normalización que ya usa `_clave`
   (URL + cuerpo JSON ordenado, sin credenciales). El replay la usa para identificar la
   respuesta; la huella de credencial de la caché en memoria queda fuera para que el mismo
   artefacto funcione en CI, sin API key, y en el host.
3. **Replay por proveedor inyectado, no por doble del pipeline.**
   `banco.main(... --replay)` sustituye `pipeline.llm.chat` por un proveedor que devuelve la
   respuesta grabada y fija una URL local ficticia para no exigir API key. El resto del
   pipeline (verificación DSL, construcción B-rep, comparación ±2 %, MLflow opcional) corre
   igual: lo que se mide sigue siendo la aceptación real de la pieza. Las respuestas pasan
   por `llm_resiliente.consultar` y por su validador, igual que una respuesta pagada.
4. **Falla explícita antes de gastar o callar.**
   `preparar()` valida versión de prompt, modelo, clave y cobertura de los 40 casos antes de
   ejecutar el primer caso. Una grabación ausente o una versión de prompt cambiada aborta con
   código 2 y mensaje en español; nunca se llama al modelo como fallback (RNF-3).
5. **Umbral configurable, `make bench` intacto.**
   `--replay` es opt-in y `--umbral` (por defecto `1.0`) hace fallar el proceso con código 1
   si `acierto < umbral`. Sin `--replay`, `make bench` conserva su comportamiento y sus
   opciones actuales (RNF-2). El resumen en modo replay añade `modo`, `prompt_version` y
   `umbral` para que el fallo sea auditable en el JSON de salida.
6. **Origen de las respuestas sembradas.**
   No hay `DEEPSEEK_API_KEY` en este entorno, así que el artefacto inicial se deriva de las
   referencias del propio banco (`medidas` → programa DSL; negativos → `unsupported`), con
   `origen: "referencia-banco"` declarado en el JSON. `scripts/verify_banco_replay.py
   --grabar` permite regenerarlo contra el proveedor real (`origen: "proveedor"`); el límite
   queda consignado en `evidence.md`.
7. **CI y baseline real separados.**
   `ci.yml` añade `make bench-replay` con `MLFLOW_TRACKING_ENABLED=0`: sin red, sin key y sin
   GPU. Un workflow aparte (`banco-baseline.yml`), programado y manual, corre `make bench`
   con `DEEPSEEK_API_KEY`, apunta `MLFLOW_TRACKING_URI` a `vars.MLFLOW_TRACKING_URI` y sube
   el CSV/JSON como artefacto; ahí se registra el baseline real de SPEC-045/AC2.
8. **Sin cambios al contrato público.** No se toca `api.py`, OpenAPI ni los tipos generados:
   `api-contract-check` y `api-types-check` deben seguir en verde.
9. **Pruebas sin servicios externos.** Se prueban esquema, clave estable, cobertura,
   cambio de prompt, ausencia de llamadas de red, cero tokens, caída bajo umbral y compatibilidad
   del runner real con dobles inyectados.
10. **Constitución viva.** `CONSTITUTION.md` se actualiza en el mismo commit con el nuevo
    módulo, el target `make bench-replay` y el workflow programado, según el estándar
    `jan-project-standard`.

## Criterios de aceptación cubiertos

| AC | Evidencia prevista |
|----|--------------------|
| AC1 — Caída detectada sin tokens | `make bench-replay` con `acierto < umbral` devuelve 1; el resumen acredita `tokens_entrada = tokens_salida = 0` y el proveedor simulado nunca contacta la red. |
| AC2 — Baseline real en MLflow | Workflow `banco-baseline.yml` (schedule + `workflow_dispatch`) corre `make bench` con key y `MLFLOW_TRACKING_URI`; la corrida padre de `banco.py` ya registra params/métricas en `m2-cad-banco`. |
| AC3 — Respuestas versionadas | El artefacto declara `prompt.id`, `prompt.version` y `prompt.sha256` validados contra `prompts.cargar()`; cambiar el prompt sin regrabar aborta el replay. |

## Riesgos y fuera de alcance

- Las respuestas sembradas son referencias deterministas, no inferencias del proveedor: no
  detectan un cambio de calidad del modelo, pero sí una regresión del pipeline, del kernel o
  del prompt. La regrabación real y el baseline programado cierran esa brecha.
- No se añaden alertas de regresión histórica (SPEC-047) ni comparación A/B (SPEC-053).
- No se cambian prompts ni tolerancias para pasar el umbral.
