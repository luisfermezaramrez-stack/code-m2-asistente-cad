# Tareas · HU-32 (SPEC-033)

Checklist ejecutable en el orden indicado. Cada tarea termina con validación
local antes de pasar a la siguiente.

- [x] T0 · Leer spec, `CONSTITUTION.md`, `api.py`, `seguimiento.py`, `trabajos.py`
  y auditoría no destructiva del estándar (0 `FALTA`, 20 `DIFIERE` legítimos).
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Crear `src/m2_cad/control_uso.py`: `ConfiguracionUso`, `ControlUso`,
  `RegistroIdempotencia` y errores tipados. Sin dependencias de red ni de API.
- [x] T3 · Integrar en `api.py`: dependencia `obtener_control_uso`, reserva de
  cuota antes de crear el trabajo, idempotencia en JSON y SSE, y `GET /uso`.
- [x] T4 · Contabilizar `costo_usd` en `medir_solicitud` sin duplicar el cálculo
  ni inventar tokens.
- [x] T5 · Añadir `tests/test_hu32_costo_limites_idempotencia.py` con AC1–AC4,
  RNF-2/RNF-3, conflicto de idempotencia y agotamiento de ventana por sesión.
- [x] T6 · Regenerar `frontend/src/generated/api.ts` con el generador y
  comprobar `api-types-check`.
- [x] T7 · Documentar variables y cabeceras en `README.md` y `.env.example`;
  registrar la decisión en `CONSTITUTION.md` en el mismo commit.
- [x] T8 · Ruff (check + formato), `api-types-check`, 424 pytest (94,54 %) y
  frontend (50 Vitest + typecheck + build). Equivalente local de `make check`
  con `uv run --no-sync` por el wheel de `nlopt` en macOS x86_64.
- [ ] T9 · Escribir `evidence.md` (hecho) y abrir PR a `main` (pendiente).
