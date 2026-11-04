---

description: "Actividades de implementación para HU-06 (Registro de solicitudes — parte de Luis Meza)"

---

# Tasks: Registro de solicitudes de la API (HU-06 — parte de Luis Meza)

**Input**: `specs/004-registro-solicitudes/spec.md` + `plan.md`

**Prerequisites**: spec.md ✅, plan.md ✅ · Depende de HU-04 (pipeline genera resultado/latencia) y de la API FastAPI (J. C. Pérez, actividad J)

**Organización**: tareas agrupadas por historia de usuario (US1–US2).

**Mapeo CPM**: HU-06 · actividad H (Registro de solicitudes, día 10). La actividad J (API) es de J. C. Pérez.

## Formato: `[ID] [P?] [US#] Descripción`

---

## Phase 1: User Story 1 - Registro completo (P1)

- [ ] T001 [US1] Implementar el módulo de registro en `src/m2_cad/registro.py` con los campos id, hora, texto, traducción, resultado, latencia, error y versión del modelo
- [ ] T002 [US1] Integrar el registro en cada POST /generar de `src/m2_cad/api.py` (consumir la respuesta del pipeline)
- [ ] T003 [US1] Validar que en 20 llamadas hay 0 campos vacíos en el registro (AC3)

---

## Phase 2: User Story 2 - Sin datos personales (P1)

- [ ] T004 [US2] Garantizar que el registro excluye nombres y correos (Ley 1581) (AC4)
- [ ] T005 [P] [US2] Añadir prueba automática del registro (campos completos + exclusión de datos personales) en `tests/test_api.py` o `tests/test_registro.py`

---

## Dependencies & Execution Order

- T001 → T002 → T003 (módulo → integración → validación).
- T004 y T005 pueden ir en paralelo tras T001.
- Depende de que la API (J. C. Pérez) exponga el resultado y la latencia para registrar.

## Criterios de aceptación cubiertos (parte de Luis Meza)

| AC | Tarea |
|----|-------|
| AC3 (0 campos vacíos en 20 llamadas) | T001, T002, T003 |
| AC4 (excluye nombres y correos) | T004, T005 |

## Notes

- AC1, AC2 y AC5 (endpoints y cobertura de la API) son de J. C. Pérez; no están en este desglose.
- El registro es la fuente de trazabilidad de los objetivos 1 y 2: cada resultado debe ligarse a su solicitud, versión y hora.
- `data/registro.csv` está gitignoreado (no versiona datos).
