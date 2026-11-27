# SPEC-027 — HU-26 · Tareas

## Fase 1 — Especificación

- [x] Revisar SPEC-027 y los puntos donde hoy se arma el motivo (`pipeline.py`, `api.py`).
- [x] Decidir asignación de causa en el origen y mapeo por códigos estructurados del verificador.
- [x] Decidir que la causa viaja al registro y a MLflow, no al cuerpo de `/v1`.
- [x] Redactar `plan.md` y `tasks.md`.

## Fase 2 — Implementación

- [x] T1 — Catálogo `Causa` y `causa_de_informe` en `src/m2_cad/declinacion.py`.
- [x] T2 — `PiezaDeclinada`, `ErrorVerificacion` y `ErrorGeneracion` con causa, mensaje y detalle técnico.
- [x] T3 — API: 422 con mensaje legible, causa propagada por `medido`.
- [x] T4 — Registro: columna `causa` y migración generalizada de columnas.
- [x] T5 — Seguimiento: etiqueta `causa_declinacion` en `Corrida.finalizar` y `medir_solicitud`.

## Fase 3 — Calidad

- [x] AC1: cada caso del corpus de declinaciones tiene una causa del catálogo.
- [x] AC2: mensaje en español, sin identificadores del DSL ni texto crudo del verificador, con «qué haría falta».
- [x] AC3: causa en el registro y en la etiqueta de MLflow, utilizable como dimensión.
- [x] No regresión: 422 intacto, contrato y tipos del frontend sin cambios, `make check` en verde con cobertura ≥ 70 %.
- [x] `plan.md`, `tasks.md`, estado en `specs/README.md` y `CONSTITUTION.md` actualizados.
