# Feature Specification: Prueba con usuarios externos (HU-11)

**Feature Branch**: `006-prueba-usuarios`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "HU-11 (1 SP) — Como docente evaluador, quiero ver que 3 usuarios externos con experiencia en CAD completan sin ayuda las tareas de placa, escuadra y pieza fuera del catálogo, para comprobar que el producto es usable por su público objetivo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Usuarios realizan las tareas sin ayuda (Priority: P1)

Tres usuarios externos con experiencia en CAD completan, sin ayuda, las 3 tareas (placa, escuadra, pieza fuera del catálogo).

**Why this priority**: Es la evidencia central de usabilidad del producto (objetivo 4).

**Independent Test**: 3 usuarios con experiencia CAD hacen 3 tareas sin ayuda (AC1).

**Acceptance Scenarios**:

1. **Given** 3 usuarios externos con experiencia en CAD, **When** realizan las 3 tareas, **Then** las completan sin ayuda (AC1).

---

### User Story 2 - Umbral de éxito (Priority: P1)

Se completan 7 de 9 tareas o más (3 usuarios × 3 tareas).

**Why this priority**: Define el criterio de éxito del objetivo 4.

**Independent Test**: 7 de 9 tareas completadas o más (AC2).

**Acceptance Scenarios**:

1. **Given** las 9 tareas de los 3 usuarios, **When** se cuentan las completadas, **Then** son ≥ 7 (AC2).

---

### User Story 3 - Tiempo registrado (Priority: P2)

Se registra el tiempo por tarea para medir eficiencia.

**Why this priority**: Complementa la usabilidad con evidencia de tiempo.

**Independent Test**: tiempo por tarea registrado (AC3).

**Acceptance Scenarios**:

1. **Given** cada tarea, **When** el usuario la realiza, **Then** se registra su tiempo (AC3).

---

### User Story 4 - Problemas priorizados y atendidos (Priority: P2)

Los problemas se listan por gravedad y los 2 más graves se corrigen o documentan.

**Why this priority**: Cierra el ciclo de mejora a partir de la prueba real.

**Independent Test**: problemas listados por gravedad; los 2 más graves corregidos o documentados (AC4).

**Acceptance Scenarios**:

1. **Given** los hallazgos de la prueba, **When** se consolidan, **Then** se listan por gravedad y los 2 más graves se corrigen o documentan (AC4).

---

### User Story 5 - Consentimiento e informe sin datos personales (Priority: P2)

Se registra el consentimiento y se redacta un informe sin datos personales.

**Why this priority**: Cumple la Ley 1581 de 2012 y protege a los participantes.

**Independent Test**: consentimiento registrado e informe sin datos personales (AC5).

**Acceptance Scenarios**:

1. **Given** los participantes, **When** se recaba su consentimiento, **Then** queda registrado y el informe no incluye datos personales (AC5).

---

### Edge Cases

- ¿Qué pasa si un usuario no está disponible el día 14? → agendar desde el día 6; se acepta videollamada (mitigación de la propuesta).
- ¿Qué pasa si el producto falla en la tarea de "pieza fuera del catálogo"? → lo esperado es la declinación con motivo (HU-05), que también cuenta como tarea completada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 3 usuarios externos con experiencia en CAD DEBEN realizar 3 tareas sin ayuda (AC1).
- **FR-002**: Se DEBEN completar ≥ 7 de 9 tareas (AC2).
- **FR-003**: Se DEBE registrar el tiempo por tarea (AC3).
- **FR-004**: Los problemas DEBEN listarse por gravedad y los 2 más graves corregirse o documentarse (AC4).
- **FR-005**: Se DEBE registrar el consentimiento y el informe NO DEBE incluir datos personales (AC5).

### Key Entities

- **Tarea**: placa, escuadra, pieza fuera del catálogo.
- **Participante**: usuario externo con experiencia en CAD (anónimo en el informe).
- **Informe**: resultados, tiempos y problemas, sin datos personales.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 3/3 usuarios hacen 3 tareas sin ayuda (AC1).
- **SC-002**: ≥ 7/9 tareas completadas (AC2).
- **SC-003**: 100 % de tareas con tiempo registrado (AC3).
- **SC-004**: 2 problemas más graves corregidos o documentados (AC4).
- **SC-005**: 100 % consentimiento registrado; 0 datos personales en el informe (AC5).

## Assumptions

- Las 3 tareas se definen a partir de las familias del catálogo (placa y escuadra) + una pieza fuera de catálogo.
- La prueba puede hacerse presencial o por videollamada.
