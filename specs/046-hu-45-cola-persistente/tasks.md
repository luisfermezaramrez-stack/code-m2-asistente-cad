# Tareas · HU-45 (SPEC-046)

Checklist completado en orden de ejecución; la evidencia está en [evidence.md](./evidence.md).

- [x] T0 · Leer spec, SPEC-031, `CONSTITUTION.md`, `api.py`, `trabajos.py`, `pipeline.py` y
  `persistencia_registro.py`; auditoría no destructiva (0 FALTA, 20 DIFIERE legítimos).
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Crear `src/m2_cad/cola_trabajos.py`: store JSON atómico, `TrabajoPersistido`,
  encolado, reclamo, reanudación, eventos, cancelación y drenaje.
- [x] T3 · Crear `src/m2_cad/worker.py`: CLI con `--cola`, `--procesador`, `--registro`,
  `--una-vez`, señales SIGTERM y finalizador con registro/métricas sin duplicados.
- [x] T4 · Integrar `api.py`: dependencia de cola, `/generar` SSE encola, consulta y
  cancelación con fallback al gestor, y retención que respeta la cola.
- [x] T5 · Añadir `tests/test_hu45_cola_persistente.py` y `tests/worker_stub.py` con
  AC1–AC3, deduplicación y drenaje sin eventos truncados.
- [x] T6 · Exponer `make worker`, documentar `M2_COLA_PATH` y el servicio worker en
  `README.md`, `.env.example`, Docker Compose y `CONSTITUTION.md` (misma rama).
- [x] T7 · Ejecutar Ruff (check + formato), pytest con cobertura, `api-types-check` y
  frontend (Vitest, typecheck, build).
- [x] T8 · Escribir `evidence.md` y abrir el PR a `main` (enlace en `evidence.md`).
