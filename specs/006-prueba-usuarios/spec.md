# Feature Specification: Prueba de uso simulada (HU-11)

**Feature Branch**: `006-prueba-usuarios`

**Created**: 2026-11-03 · **Updated**: 2026-11-14 (cambio de alcance a prueba simulada)

**Status**: Draft

**Input**: User description: "HU-11 (1 SP) — Como docente evaluador, quiero ver una prueba de uso simulada por los 3 integrantes del grupo sobre las tareas de placa, escuadra y pieza fuera del catálogo, para validar el protocolo de prueba (guion, registro e informe) antes de una prueba con usuarios reales."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simulación de las tareas (Priority: P1)

Los 3 integrantes del grupo simulan las 3 tareas (placa, escuadra, pieza fuera del catálogo) siguiendo el kit de prueba.

**Why this priority**: Valida que el guion y las fichas sirven antes de usarlos con usuarios reales.

**Independent Test**: las 9 ejecuciones simuladas están registradas según el kit (AC1).

**Acceptance Scenarios**:

1. **Given** el kit de prueba, **When** los 3 integrantes simulan las 3 tareas, **Then** queda registrada cada una de las 9 ejecuciones (AC1).

---

### User Story 2 - Conteo frente al umbral (Priority: P1)

El informe cuenta las tareas completadas frente al umbral de 7 de 9.

**Why this priority**: Comprueba que el informe calcula el criterio de éxito que se usará en la prueba real.

**Independent Test**: el informe muestra n/9 y el veredicto frente a ≥ 7/9 (AC2).

**Acceptance Scenarios**:

1. **Given** las 9 ejecuciones simuladas, **When** se consolidan, **Then** el informe muestra el conteo y el veredicto frente a ≥ 7/9 (AC2).

---

### User Story 3 - Tiempo registrado (Priority: P2)

Se registra el tiempo por tarea.

**Why this priority**: Valida la hoja de registro de tiempos.

**Independent Test**: tiempo por tarea registrado (AC3).

**Acceptance Scenarios**:

1. **Given** cada ejecución simulada, **When** se registra, **Then** incluye su tiempo (AC3).

---

### User Story 4 - Problemas priorizados (Priority: P2)

Los problemas se listan por gravedad y los 2 más graves quedan documentados.

**Why this priority**: Valida el formato de priorización de hallazgos.

**Independent Test**: problemas listados por gravedad; los 2 más graves documentados (AC4).

**Acceptance Scenarios**:

1. **Given** los hallazgos simulados, **When** se consolidan, **Then** se listan por gravedad y los 2 más graves quedan documentados (AC4).

---

### User Story 5 - Transparencia y datos personales (Priority: P1)

Todos los datos se marcan como simulados y el informe no incluye datos personales.

**Why this priority**: Evita que una simulación se interprete como evidencia de usabilidad real y cumple la Ley 1581 de 2012.

**Independent Test**: el informe y cada tabla de resultados llevan la marca "SIMULADO"; no hay nombres ni datos personales (AC5).

**Acceptance Scenarios**:

1. **Given** el informe, **When** se revisa, **Then** está marcado como simulado, no se presenta como evidencia de usabilidad real y no contiene datos personales (AC5).

---

### Edge Cases

- ¿Qué pasa si se quiere usar el informe como evidencia de usabilidad? → no es válido; hace falta la prueba real con usuarios externos (fuera del alcance de esta HU).
- ¿Qué pasa con la pieza fuera del catálogo? → lo esperado es la declinación con motivo (HU-05), que cuenta como tarea completada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Los 3 integrantes DEBEN simular las 3 tareas siguiendo el kit (AC1).
- **FR-002**: El informe DEBE mostrar el conteo de tareas completadas frente a ≥ 7/9 (AC2).
- **FR-003**: Se DEBE registrar el tiempo por tarea (AC3).
- **FR-004**: Los problemas DEBEN listarse por gravedad y los 2 más graves documentarse (AC4).
- **FR-005**: Todos los resultados DEBEN marcarse como "SIMULADO" y el informe NO DEBE incluir datos personales (AC5).

### Key Entities

- **Tarea**: placa, escuadra, pieza fuera del catálogo.
- **Participante**: integrante del grupo, con código anónimo (P1–P3).
- **Informe**: resultados simulados, tiempos y problemas, sin datos personales.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 9/9 ejecuciones simuladas registradas (AC1).
- **SC-002**: el informe muestra el conteo y el veredicto frente a ≥ 7/9 (AC2).
- **SC-003**: 100 % de tareas con tiempo registrado (AC3).
- **SC-004**: 2 problemas más graves documentados (AC4).
- **SC-005**: 100 % de las tablas de resultados marcadas como "SIMULADO"; 0 datos personales (AC5).

## Assumptions

- Las 3 tareas se definen a partir de las familias del catálogo (placa y escuadra) + una pieza fuera de catálogo.
- **Cambio de alcance (2026-11-14):** la HU pasa de una prueba con 3 usuarios externos a
  una **prueba simulada** por los integrantes del grupo. Su objetivo es validar el
  protocolo (kit, registro e informe), no demostrar usabilidad. La prueba con usuarios
  externos queda como trabajo futuro. Kit: `docs/prueba-usuarios/kit.md`.
