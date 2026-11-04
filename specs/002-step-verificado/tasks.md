---

description: "Actividades de implementación para HU-04 (Generar pieza STEP verificada)"

---

# Tasks: Generar pieza STEP verificada (HU-04)

**Input**: `specs/002-step-verificado/spec.md` + `plan.md`

**Prerequisites**: spec.md ✅, plan.md ✅ · Depende de HU-01 (modelo servido) y HU-03 (traducción ES→EN)

**Organización**: tareas agrupadas por historia de usuario (US1–US5).

**Mapeo CPM**: HU-04 · actividad G (Pipeline de generación y verificación, días 5–7).

## Formato: `[ID] [P?] [US#] Descripción`

- **[P]**: puede correr en paralelo
- **[US#]**: historia de usuario a la que pertenece

---

## Phase 1: Foundational (Generación)

- [ ] T001 [US1] Implementar la generación del programa constraint-kit desde la solicitud traducida en `src/m2_cad/pipeline.py`
- [ ] T002 [US1] Conectar el verificador de constraint-kit y confirmar que el programa pasa sin errores (AC1)

**Checkpoint**: programa verificado → listo para exportar.

---

## Phase 2: User Story 2 - Exportación STEP (P1)

- [ ] T003 [US2] Implementar la exportación STEP (B-rep de OpenCascade) en `src/m2_cad/pipeline.py`
- [ ] T004 [US2] Validar que el STEP abre en FreeCAD sin advertencias (AC2)

---

## Phase 3: User Story 3 - Tolerancia geométrica (P2)

- [ ] T005 [US3] Validar volumen y caja envolvente en 5 casos, dentro de ±2 % (AC3)
- [ ] T006 [P] [US3] Añadir la prueba de tolerancia en `tests/test_pipeline.py`

---

## Phase 4: User Story 4 - Entregables GLB y CSV (P2)

- [ ] T007 [US4] Generar el GLB con Blender para la vista 3D (AC4)
- [ ] T008 [P] [US4] Generar el CSV de lista de materiales (AC4)

---

## Phase 5: User Story 5 - Registro de tiempo (P2)

- [ ] T009 [US5] Registrar el tiempo de generación por solicitud (AC5)

---

## Dependencies & Execution Order

- T001 → T002 (verificación) → T003/T004 (STEP).
- T005 depende de T003; T007/T008 pueden correr en paralelo tras T003.
- T009 independiente tras T001.

## Criterios de aceptación cubiertos

| AC | Tarea |
|----|-------|
| AC1 (programa verificado) | T001, T002 |
| AC2 (STEP en FreeCAD) | T003, T004 |
| AC3 (±2 % en 5 casos) | T005, T006 |
| AC4 (STEP + GLB + CSV) | T003, T007, T008 |
| AC5 (tiempo registrado) | T009 |

## Notes

- Los artefactos van a `outputs/` (gitignoreado).
- La verificación es solo geométrica; toda salida lleva la marca "preliminar" (HU-05).
- El núcleo CAD corre en CPU; la GPU es solo para inferencia del modelo.
