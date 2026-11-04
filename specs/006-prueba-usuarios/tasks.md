---

description: "Actividades de implementación para HU-11 (Prueba con usuarios externos)"

---

# Tasks: Prueba con usuarios externos (HU-11)

**Input**: `specs/006-prueba-usuarios/spec.md` + `plan.md`

**Prerequisites**: spec.md ✅, plan.md ✅ · Depende de HU-10 (servicio desplegado) y HU-08 (interfaz Gradio)

**Organización**: tareas agrupadas por historia de usuario (US1–US5).

**Mapeo CPM**: HU-11 · actividad O (Prueba con usuarios, día 14).

## Formato: `[ID] [P?] [US#] Descripción`

---

## Phase 1: Preparación

- [ ] T001 [US1] Definir las 3 tareas y el guion: placa, escuadra y pieza fuera del catálogo
- [ ] T002 [US1] Agendar a 3 usuarios externos con experiencia en CAD (desde el día 6; presencial o videollamada) (AC1)

**Checkpoint**: guion listo y participantes agendados.

---

## Phase 2: Ejecución (User Story 1 y 3)

- [ ] T003 [US1] Ejecutar la prueba: 3 usuarios × 3 tareas sin ayuda (AC1)
- [ ] T004 [P] [US3] Registrar el tiempo por tarea (AC3)

---

## Phase 3: Consolidación (User Story 2 y 4)

- [ ] T005 [US2] Contar las tareas completadas y validar ≥ 7 de 9 (AC2)
- [ ] T006 [US4] Listar los problemas por gravedad y corregir/documentar los 2 más graves (AC4)

---

## Phase 4: Informe (User Story 5)

- [ ] T007 [US5] Registrar el consentimiento de los participantes y redactar el informe en `docs/prueba-usuarios.md` sin datos personales (AC5)

---

## Dependencies & Execution Order

- T001 → T002 → T003 (guion → agenda → ejecución).
- T004 en paralelo con T003 (mismo momento, registro).
- T005 y T006 tras T003; T007 cierra.

## Criterios de aceptación cubiertos

| AC | Tarea |
|----|-------|
| AC1 (3 usuarios × 3 tareas sin ayuda) | T002, T003 |
| AC2 (≥ 7/9 tareas) | T005 |
| AC3 (tiempo por tarea) | T004 |
| AC4 (problemas por gravedad; 2 más graves) | T006 |
| AC5 (consentimiento + informe sin datos personales) | T007 |

## Notes

- "Pieza fuera del catálogo" → el resultado esperado es la declinación con motivo (HU-05); cuenta como tarea completada si el sistema declina correctamente.
- El informe es entregable versionado en `docs/`, no material de referencia.
- Si los usuarios no están disponibles el día 14 → videollamada (mitigación ya prevista en la propuesta).
