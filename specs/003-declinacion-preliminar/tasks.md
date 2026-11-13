---

description: "Actividades de implementación para HU-05 (Declinación y marca preliminar)"

---

# Tasks: Declinación y marca "preliminar" (HU-05)

**Input**: `specs/003-declinacion-preliminar/spec.md` + `plan.md`

**Prerequisites**: spec.md ✅, plan.md ✅ · Depende de HU-04 (pipeline de generación)

**Organización**: tareas agrupadas por historia de usuario (US1–US3).

**Mapeo CPM**: HU-05 · actividad G (Pipeline de generación y verificación).

## Formato: `[ID] [P?] [US#] Descripción`

---

## Phase 1: User Story 1 - Declinación con motivo (P1)

- [x] T001 [US1] Implementar la declinación con motivo en español para piezas fuera del catálogo en `src/m2_cad/pipeline.py` (sin STEP)
- [x] T002 [US1] Validar 3 de 3 solicitudes fuera del catálogo declinadas con motivo y sin STEP (AC1) — prueba automática con salida simulada del modelo; falta validar con el modelo servido

---

## Phase 2: User Story 2 - Sin falsas declinaciones (P1)

- [x] T003 [US2] Validar que 0 de 5 solicitudes del catálogo se declinan por error (AC2) — prueba automática con 5 casos del banco HU-02; falta validar con el modelo servido

---

## Phase 3: User Story 3 - Marca "preliminar" (P2)

- [x] T004 [US3] Añadir la marca "diseño preliminar" en la interfaz Gradio (`src/m2_cad/interfaz.py`) y en el STEP (AC3)

---

## Phase 4: Prueba automática (P2)

- [x] T005 [US3] Añadir la prueba automática que cubre los tres casos (declinación, sin falsas declinaciones, marca) en `tests/test_pipeline.py` (AC4)

---

## Dependencies & Execution Order

- T001 → T002 → T003 (primero declinar bien, luego verificar que no declina de más).
- T004 y T005 pueden ir en paralelo tras T001.

## Criterios de aceptación cubiertos

| AC | Tarea |
|----|-------|
| AC1 (3/3 declinadas con motivo) | T001, T002 |
| AC2 (0/5 falsas declinaciones) | T003 |
| AC3 (marca "preliminar" en UI y STEP) | T004 |
| AC4 (prueba automática) | T005 |

## Notes

- La declinación es la salvaguarda de seguridad: nunca se entrega STEP de una pieza no construible.
- La marca "preliminar" aplica a TODA salida, sin excepción.
