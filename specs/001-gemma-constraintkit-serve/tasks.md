---

description: "Actividades de implementación para HU-01 (Servir Gemma 4 12B ConstraintKit)"

---

# Tasks: Servir Gemma 4 12B ConstraintKit (HU-01)

**Input**: `specs/001-gemma-constraintkit-serve/spec.md` + `plan.md`

**Prerequisites**: spec.md ✅, plan.md ✅

**Tests**: Incluidas (son parte de los criterios de aceptación de HU-01: SHA-256, suite 113/113, 5 solicitudes `/dsl/check`).

**Organización**: tareas agrupadas por historia de usuario (US1–US5) para permitir implementación y verificación independiente de cada una.

**Mapeo CPM**: cada actividad cierra una de las actividades A–D del cronograma de la propuesta (HU-01 · CPM A–D).

## Formato: `[ID] [P?] [US#] Descripción`

- **[P]**: puede correr en paralelo (archivos/entornos distintos, sin dependencia)
- **[US#]**: historia de usuario a la que pertenece la tarea (US1…US5)

---

## Phase 1: Setup (Infraestructura)

**Propósito**: reservar y preparar el entorno de la GPU alquilada.

- [ ] T001 [US1] Reservar la GPU alquilada (≥ 16 GB de VRAM) y registrar horas de uso *(CPM B)*
- [ ] T002 [P] [US2] Instalar/verificar llama.cpp en la GPU y preparar el directorio de pesos *(CPM A/B)*

---

## Phase 2: Foundational (Modelo y contenedor)

**Propósito**: infraestructura base que DEBE estar lista antes de cualquier verificación.

**⚠️ CRÍTICO**: sin modelo íntegro y contenedor operativo no hay pipeline.

- [ ] T003 [US1] Descargar el GGUF Q6_K (9,8 GB) y verificar `sha256sum` contra el hash publicado (AC1) *(CPM B)*
- [ ] T004 [US2] Configurar llama.cpp para cargar con `--ctx-size 8192` y verificar VRAM ≤ 16 GB (AC2) *(CPM D)*
- [ ] T005 [US3] Levantar el contenedor de constraint-kit usando la imagen del autor (Python 3.12 + OpenCascade/SolveSpace), sin modificarla (AC3) *(CPM C)*

**Checkpoint**: modelo íntegro + contenedor arriba → listo para verificar.

---

## Phase 3: User Story 3 - Contenedor verificado (P1)

**Goal**: la suite del contenedor pasa 113/113.

**Independent Test**: ejecutar la suite dentro del contenedor → 113 de 113 verdes.

- [ ] T006 [US3] Ejecutar la suite del contenedor (113 pruebas) y confirmar 113/113 en verde (AC3) *(CPM C)*

---

## Phase 4: User Story 4 - Prueba end-to-end (P2)

**Goal**: 5 de 5 solicitudes devuelven un programa que pasa `/dsl/check`.

**Independent Test**: enviar 5 solicitudes al modelo servido → los 5 programas pasan `/dsl/check`.

- [ ] T007 [US4] Enviar 5 solicitudes de prueba y validar que las 5 devuelven un programa que pasa `/dsl/check` (AC4) *(CPM D)*

---

## Phase 5: User Story 5 - Documentación (P2)

**Goal**: versiones exactas registradas para reproducibilidad.

**Independent Test**: el README lista modelo, llama.cpp, constraint-kit y contenedor con versiones.

- [X] T008 [P] [US5] Registrar en el README las versiones exactas (modelo, llama.cpp, constraint-kit, contenedor) (AC5) *(CPM A)*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — arranca de inmediato.
- **Foundational (Phase 2)**: depende de Setup; BLOQUEA las verificaciones.
- **Verificación (Phases 3–4)**: dependen de Foundational; T006 (suite) antes de T007 (end-to-end).
- **Documentación (Phase 5)**: puede correr en paralelo desde que el entorno esté operativo.

### Dentro de la HU

- T003 (descarga + SHA-256) antes de T004 (servir) — pesos íntegros primero.
- T005 (contenedor) antes de T006 (113 pruebas).
- T004 + T006 antes de T007 (end-to-end).

### Oportunidades de paralelismo

- T001 y T002 en paralelo.
- T008 en paralelo con T006/T007.

---

## Criterios de aceptación cubiertos

| AC | Tarea |
|----|-------|
| AC1 (SHA-256) | T003 |
| AC2 (8192 tokens / ≤16 GB VRAM) | T004 |
| AC3 (113/113 pruebas) | T005, T006 |
| AC4 (5/5 `/dsl/check`) | T007 |
| AC5 (versiones en README) | T008 |

## Notes

- **T001–T007 son infraestructura externa**: requieren la GPU alquilada, la descarga del modelo (9,8 GB) y el contenedor Docker. No se pueden ejecutar desde el repo; se realizan en el entorno de la GPU (día 1–4 del cronograma).
- Los pesos `.gguf` NO se versionan (ya en `.gitignore`).
- El contenedor del autor se usa sin modificar (modificar dependencias C++ es la causa conocida de fallos 27/113).
- Si el día 4 el modelo aún no responde dentro de constraint-kit → activar plan B DeepSeek (criterio de parada de la propuesta).
