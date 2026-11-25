# Evidencia de implementación · HU-45 (SPEC-046)

- **Fecha**: 2026-11-25
- **Rama**: `feature/hu-45-cola-persistente`, creada desde `origin/main`
- **Issue**: [#105](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/105)
- **PR**: pendiente de apertura
- **Especificación**: [spec.md](./spec.md) · [plan.md](./plan.md) · [tasks.md](./tasks.md)

## Alcance entregado

- `src/m2_cad/cola_trabajos.py`: cola JSON persistente en `M2_COLA_PATH`, escrita con
  `_publicar_bytes` bajo `_bloqueo` de SPEC-031; `TrabajoPersistido` conserva la interfaz
  de `Trabajo` para `RespuestaSSE`.
- `src/m2_cad/worker.py`: CLI `python -m m2_cad.worker`, con `reanudar()`, `reclamar()`,
  SIGTERM de drenaje, finalizador con registro deduplicado y métricas reconstruidas desde
  la configuración persistida.
- `src/m2_cad/api.py`: `/generar` SSE encola cuando `M2_COLA_HABILITADA=1`; `/generaciones`
  y `DELETE /generaciones/{id}` consultan la cola con fallback al gestor en memoria;
  la retención respeta los trabajos activos de ambas colas.
- `Makefile` (`make worker`), `docker-compose.yml` (`m2-cad-worker`), `.env.example`,
  `README.md`, `.gitignore` y `CONSTITUTION.md` actualizados en la misma rama.

## Criterios de aceptación

| AC | Prueba | Resultado |
| --- | --- | --- |
| AC1 — Reinicio sin pérdida | `test_ac1_reinicio_sin_perdida_y_registro_no_duplicado` | Trabajo `en_proceso` de un worker caído → `reanudar()` + nuevo worker → `verificado`; una sola fila en el CSV. |
| AC2 — Drenaje sin cortar eventos | `test_ac2_drenaje_no_corta_eventos` | Cola cerrada durante la suscripción; los tres eventos llegan completos, el último es terminal y su payload de 2048 caracteres se parsea sin truncamiento; nuevos encolados devuelven 503. |
| AC3 — Worker separado | `test_ac3_worker_separado_del_proceso_api` | Subproceso `python -m m2_cad.worker` escribe un PID distinto al de la API y completa el trabajo; `test_api_sse_encola_sin_ejecutar_el_pipeline` confirma que la API sólo encola. |
| RNF-1 / compatibilidad | `test_consultar_y_cancelar_generacion_usan_la_cola` | Consulta 200 y cancelación 202 sobre trabajos persistidos, sin cambios en el contrato. |
| RNF-3 / deduplicación | `test_ac1_reinicio_sin_perdida_y_registro_no_duplicado` | Registrar dos veces el mismo `solicitud_id` deja una sola fila. |

## Validaciones

- `uv run --no-sync ruff format --check src tests scripts/...`: 47 archivos formateados.
- `uv run --no-sync ruff check src tests scripts/...`: **All checks passed**.
- `uv run --no-sync python scripts/generate_api_types.py --check`: tipos OpenAPI sin cambios.
- `uv run --no-sync pytest --cov=src/m2_cad --cov-report=term -q`: **420 passed**,
  cobertura total **91,86 %** (mínimo 70 %). En ejecuciones intermedias el test de
  sobrecarga de MLflow (<50 ms p95) fue intermitente bajo carga local; pasó aislado y en
  la ejecución final de la suite completa, sin cambio de código.
- `npm --prefix frontend test`: 50 pruebas Vitest en 3 archivos.
- `npm --prefix frontend run typecheck` y `npm --prefix frontend run build`: verdes.
- Pruebas sin red, API key ni GPU: procesador simulado, `MLFLOW_TRACKING_ENABLED=0` y
  `M2_DOWNLOAD_SECRET` efímero por ejecución. `data/cola.json` y su lock están gitignored.

## Límite conocido

Si el worker se detiene después de registrar pero antes de publicar el evento terminal,
una reanudación puede repetir la inferencia del modelo. No se duplica la fila del registro
porque `anexar_sin_duplicar` usa el `solicitud_id`, y el flag `registrado` impide repetir
el finalizador en la misma ejecución. Queda fuera de alcance un protocolo transaccional
entre inferencia, registro y publicación.

## Integración pendiente

PR #130 (HU-31) y PR #131 (HU-32) siguen abiertos sobre `main`. HU-45 no depende de
`/v1` ni del control de uso, pero sus cambios en `src/m2_cad/api.py` requerirán resolver
solapamientos al fusionarlos. No se fusionó ninguno de esos PR aquí.
