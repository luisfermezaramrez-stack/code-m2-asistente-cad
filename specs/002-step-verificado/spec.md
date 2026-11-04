# Feature Specification: Generar pieza STEP verificada (HU-04)

**Feature Branch**: `002-step-verificado`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "HU-04 (2 SP) — Como diseñador CAD, quiero recibir un archivo STEP con la pieza solicitada y verificada geométricamente, junto con su GLB y su lista de materiales, para abrirla en mi programa CAD y revisarla antes de usarla en el proyecto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Programa generado y verificado (Priority: P1)

El pipeline genera el programa constraint-kit de la pieza y el verificador lo aprueba sin errores.

**Why this priority**: Es la salida técnica central; sin programa verificado no hay pieza.

**Independent Test**: Se envía una solicitud y el programa pasa el verificador sin errores (AC1).

**Acceptance Scenarios**:

1. **Given** una solicitud válida del catálogo, **When** el pipeline genera el programa, **Then** el programa pasa el verificador sin errores (AC1).

---

### User Story 2 - STEP que abre en FreeCAD (Priority: P1)

El archivo STEP exportado abre en FreeCAD sin advertencias, garantizando interoperabilidad con el CAD del diseñador.

**Why this priority**: El STEP es el entregable principal que el diseñador consume.

**Independent Test**: El STEP se abre en FreeCAD sin advertencias (AC2).

**Acceptance Scenarios**:

1. **Given** el STEP exportado, **When** se abre en FreeCAD, **Then** no hay advertencias (AC2).

---

### User Story 3 - Geometría dentro de tolerancia (Priority: P2)

El volumen y la caja envolvente de la pieza construida están dentro de ±2 % del valor esperado en 5 casos.

**Why this priority**: Confirma que las medidas exactas se conservan (valor central del producto).

**Independent Test**: En 5 casos, volumen y caja envolvente dentro de ±2 % (AC3).

**Acceptance Scenarios**:

1. **Given** 5 casos de referencia, **When** se comparan volumen y caja envolvente, **Then** la desviación es ≤ ±2 % (AC3).

---

### User Story 4 - Entregables completos STEP + GLB + CSV (Priority: P2)

Cada respuesta incluye STEP, GLB (vista 3D) y CSV (lista de materiales).

**Why this priority**: Son los tres artefactos comprometidos del producto.

**Independent Test**: Cada respuesta trae STEP, GLB y CSV (AC4).

**Acceptance Scenarios**:

1. **Given** una solicitud exitosa, **When** se devuelve la respuesta, **Then** incluye STEP, GLB y CSV (AC4).

---

### User Story 5 - Tiempo de generación registrado (Priority: P2)

Se registra el tiempo de generación de cada pieza para medir latencia (objetivo 2).

**Why this priority**: Habilita la métrica de latencia del objetivo 2.

**Independent Test**: Se registra el tiempo de generación por solicitud (AC5).

**Acceptance Scenarios**:

1. **Given** una solicitud exitosa, **When** se genera la pieza, **Then** se registra el tiempo de generación (AC5).

---

### Edge Cases

- ¿Qué pasa si el STEP no abre en FreeCAD? → corregir el exportador B-rep (OpenCascade).
- ¿Qué pasa si la pieza excede ±2 %? → revisar los generadores deterministas (medidas del prompt).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El pipeline DEBE generar un programa que pasa el verificador sin errores (AC1).
- **FR-002**: El sistema DEBE exportar un STEP que abre en FreeCAD sin advertencias (AC2).
- **FR-003**: El sistema DEBE mantener volumen y caja envolvente dentro de ±2 % en 5 casos (AC3).
- **FR-004**: Cada respuesta DEBE incluir STEP, GLB y CSV (AC4).
- **FR-005**: El sistema DEBE registrar el tiempo de generación (AC5).

### Key Entities

- **Programa constraint-kit**: piezas, parámetros y uniones de la solicitud.
- **STEP (ISO 10303)**: geometría B-rep exportada.
- **GLB**: malla para vista 3D (generada con Blender).
- **CSV**: lista de materiales.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % de los programas pasan el verificador (AC1).
- **SC-002**: STEP abre en FreeCAD sin advertencias (AC2).
- **SC-003**: 5/5 casos dentro de ±2 % (AC3).
- **SC-004**: 100 % de respuestas con STEP + GLB + CSV (AC4).
- **SC-005**: 100 % de generaciones con tiempo registrado (AC5).

## Assumptions

- El verificador de constraint-kit es la fuente de verdad geométrica.
- FreeCAD disponible para la validación del STEP.
- Blender disponible para generar el GLB.
