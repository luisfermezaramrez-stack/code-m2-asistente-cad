---

description: "Actividades de implementación para HU-11 (Prueba de uso simulada)"

---

# Tasks: Prueba de uso simulada (HU-11)

**Input**: `specs/006-prueba-usuarios/spec.md` + `plan.md`

**Prerequisites**: spec.md ✅, plan.md ✅ · Depende de HU-10 (servicio desplegado) y HU-08 (interfaz Vue)

**Organización**: tareas agrupadas por historia de usuario (US1–US5).

**Mapeo CPM**: HU-11 · actividad O (Prueba con usuarios, día 14).

## Formato: `[ID] [P?] [US#] Descripción`

---

## Phase 1: Preparación

- [x] T001 [US1] Definir las 3 tareas y el guion: placa, escuadra y pieza fuera del catálogo
- [x] T002 [US1] Agendar las 3 sesiones con los integrantes del grupo y asignar moderador cruzado (presencial o videollamada) (AC1)

**Checkpoint**: guion listo y participantes agendados.

---

## Phase 2: Ejecución (User Story 1 y 3)

- [x] T003 [US1] Simular la prueba: 3 integrantes × 3 tareas siguiendo el kit (AC1)
- [x] T004 [P] [US3] Registrar el tiempo por tarea (AC3)

---

## Phase 3: Consolidación (User Story 2 y 4)

- [x] T005 [US2] Contar las tareas completadas y mostrar el veredicto frente a ≥ 7 de 9 (AC2)
- [x] T006 [US4] Listar los problemas por gravedad y documentar los 2 más graves (AC4)

---

## Phase 4: Informe (User Story 5)

- [x] T007 [US5] Redactar el informe en `docs/prueba-usuarios.md` marcado como SIMULADO y sin datos personales (AC5)

---

## Dependencies & Execution Order

- T001 → T002 → T003 (guion → agenda → ejecución).
- T004 en paralelo con T003 (mismo momento, registro).
- T005 y T006 tras T003; T007 cierra.

## Criterios de aceptación cubiertos

| AC | Tarea |
|----|-------|
| AC1 (9 ejecuciones simuladas registradas) | T002, T003 |
| AC2 (conteo frente a ≥ 7/9) | T005 |
| AC3 (tiempo por tarea) | T004 |
| AC4 (problemas por gravedad; 2 más graves documentados) | T006 |
| AC5 (marca SIMULADO + sin datos personales) | T007 |

## Notes

- "Pieza fuera del catálogo" → el resultado esperado es la declinación con motivo (HU-05); cuenta como tarea completada si el sistema declina correctamente.
- El informe es entregable versionado en `docs/`, no material de referencia.
- La prueba es **simulada**: valida el protocolo, no la usabilidad. La prueba con usuarios externos queda como trabajo futuro.
