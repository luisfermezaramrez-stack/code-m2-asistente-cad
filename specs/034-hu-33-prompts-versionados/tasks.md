# SPEC-034 — HU-33 · Tareas

## Fase 1 — Especificación

- [x] Revisar SPEC-034, el prompt inline del pipeline y las columnas del registro.
- [x] Fijar el contrato del prompt versionado (`Prompt` con id, versión, etiqueta y sha256).
- [x] Decidir que el chequeo de AC2 entra en `make check` y en el job `lint` del espejo.
- [x] Redactar `plan.md` y `tasks.md`.

## Fase 2 — Implementación

- [x] T1 — `prompts/planner-v1.txt`, `prompts/manifest.toml` y `src/m2_cad/prompts.py`.
- [x] T2 — Pipeline carga el prompt por id; columnas `prompt` y `prompt_hash` en el registro y en MLflow.
- [x] T3 — `scripts/verify_prompts.py`, `make prompts-check` y el job `lint` del espejo, con paridad.
- [x] T4 — Pruebas AAA de AC1, AC2 y AC3 sin red.

## Fase 3 — Calidad

- [x] AC1: fila del registro con id y hash, y la corrida de MLflow con el mismo valor.
- [x] AC2: mutación de contenido sin subir versión → el chequeo falla con mensaje claro.
- [x] AC3: pipeline carga por id, hash igual al archivo y fila con ese id y hash.
- [x] No regresión: formato JSON, familias y rechazo fuera de catálogo siguen en verde.
- [x] `make check` en verde; registro CSV y contrato `/v1` declarados como consumidos.
