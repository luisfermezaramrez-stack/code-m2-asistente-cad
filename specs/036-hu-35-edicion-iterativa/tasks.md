# SPEC-036 — HU-35 · Tareas

## Fase 1 — Especificación

- [x] Revisar SPEC-036 y el contrato de prompts de HU-33 (`Prompt`, `cargar`, manifiesto).
- [x] Decidir la identificación de la pieza previa: `solicitud_id` con dueño (HU-53).
- [x] Decidir el almacén de versiones y el formato del diff.
- [x] Redactar `plan.md` y `tasks.md`.

## Fase 2 — Implementación

- [x] T1 — `prompts/editor-v1.txt` + entrada `editor` en el manifiesto, `versiones.py`
      (índice, `diff_programas`, validación de id) y sus pruebas.
- [x] T2 — `pipeline.editar_pieza`: prompt de edición, verificación determinista y
      declinación con causa; `_respuesta_modelo` con `sistema` inyectable.
- [x] T3 — Endpoints `POST /v1/generar/{id}/editar` y `GET /v1/generar/{id}/versiones`,
      aislamiento por usuario, topes e idempotencia, y contrato regenerado.
- [x] T4 — Integración: `/generar` escribe la versión 1, registro y MLflow con
      `operacion`/`version_pieza`/`solicitud_origen`.

## Fase 3 — Calidad

- [x] AC1: edición verificada con diff y versión anterior conservada.
- [x] AC2: edición que rompe la verificación → 422 con causa y sin reemplazo.
- [x] AC3: historial con las tres versiones en orden, programa y artefactos.
- [x] No regresión de `/generar`, `make check` y `make prompts-check` en verde.
- [x] Contrato y tipos del frontend regenerados; `CONSTITUTION.md` actualizada.
