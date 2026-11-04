# Feature Specification: Declinación y marca "preliminar" (HU-05)

**Feature Branch**: `003-declinacion-preliminar`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "HU-05 (1 SP) — Como ingeniero responsable del diseño, quiero que el asistente rechace con un motivo en español las piezas que no puede construir y marque toda salida como 'diseño preliminar', para evitar que una geometría inventada o sin revisión profesional llegue a un proyecto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declinación con motivo (Priority: P1)

Las solicitudes fuera del catálogo se declinan con un motivo en español y sin generar STEP.

**Why this priority**: Evita entregar geometría inventada; es la salvaguarda central de seguridad del producto.

**Independent Test**: 3 de 3 solicitudes fuera del catálogo se declinan con motivo y sin STEP (AC1).

**Acceptance Scenarios**:

1. **Given** una solicitud fuera del catálogo, **When** el asistente la procesa, **Then** devuelve una declinación con motivo en español y sin STEP (AC1).

---

### User Story 2 - Sin falsas declinaciones (Priority: P1)

Las solicitudes válidas del catálogo no se declinan por error.

**Why this priority**: Una declinación indebida rompe la confianza del usuario.

**Independent Test**: 0 de 5 solicitudes del catálogo se declinan por error (AC2).

**Acceptance Scenarios**:

1. **Given** 5 solicitudes válidas del catálogo, **When** el asistente las procesa, **Then** ninguna se declina por error (AC2).

---

### User Story 3 - Marca "preliminar" en toda salida (Priority: P2)

Toda salida (interfaz y STEP) lleva la marca "diseño preliminar".

**Why this priority**: Señala que la verificación es solo geométrica y exige revisión profesional.

**Independent Test**: el 100 % de las salidas lleva la marca en interfaz y STEP (AC3).

**Acceptance Scenarios**:

1. **Given** una salida exitosa, **When** se muestra/descarga, **Then** la marca "preliminar" aparece en interfaz y STEP (AC3).

---

### Edge Cases

- ¿Qué pasa si el motivo de declinación es ambiguo? → usar el motivo del verificador/DSL, en español.
- ¿Qué pasa si la marca no cabe en el STEP? → usar metadatos/atributo del STEP.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE declinar con motivo en español y sin STEP las piezas que no puede construir (AC1).
- **FR-002**: El sistema NO DEBE declinar por error solicitudes válidas del catálogo (AC2).
- **FR-003**: El sistema DEBE marcar el 100 % de las salidas como "diseño preliminar" en interfaz y STEP (AC3).
- **FR-004**: Una prueba automática DEBE cubrir los tres casos anteriores (AC4).

### Key Entities

- **Declinación**: motivo en español, sin STEP.
- **Marca "preliminar"**: atributo presente en interfaz y STEP.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 3/3 declinaciones fuera de catálogo correctas (AC1).
- **SC-002**: 0/5 falsas declinaciones (AC2).
- **SC-003**: 100 % de salidas marcadas "preliminar" (AC3).
- **SC-004**: prueba automática cubre los 3 casos (AC4).

## Assumptions

- El catálogo de familias (plate, sheet_bracket, adapter, flange, spacer, tornillería, extrusion, pipe) es la frontera de validez.
- La marca "preliminar" se propaga a la interfaz (Gradio) y al STEP.
