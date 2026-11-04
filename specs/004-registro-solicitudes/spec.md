# Feature Specification: Registro de solicitudes de la API (HU-06 — parte de Luis Meza)

**Feature Branch**: `004-registro-solicitudes`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "HU-06 (3 SP, compartida) — Como evaluador del producto, quiero una API FastAPI (POST /generar y GET /health) que registre texto, traducción, resultado, latencia, error y versión del modelo de cada solicitud, para calcular las métricas de los objetivos 1 y 2 sin revisar casos a mano. **Parte de Luis Meza**: el registro de solicitudes (AC3 y AC4). La API (AC1, AC2, AC5) es de J. C. Pérez."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registro completo sin campos vacíos (Priority: P1)

Cada solicitud se registra con id, hora, texto, traducción, resultado, latencia, error y versión del modelo, sin campos vacíos.

**Why this priority**: El registro es la fuente de las métricas de los objetivos 1 y 2; sin él hay que revisar casos a mano.

**Independent Test**: en 20 llamadas, 0 campos vacíos en el registro (AC3).

**Acceptance Scenarios**:

1. **Given** una solicitud procesada por la API, **When** se escribe el registro, **Then** id, hora, texto, traducción, resultado, latencia, error y versión están presentes (AC3).

---

### User Story 2 - Registro sin datos personales (Priority: P1)

El registro excluye nombres y correos, cumpliendo la Ley 1581 de 2012.

**Why this priority**: Protección de datos personales; es un requisito legal.

**Independent Test**: el registro no contiene nombres ni correos (AC4).

**Acceptance Scenarios**:

1. **Given** una solicitud con datos del usuario, **When** se escribe el registro, **Then** no se guardan nombres ni correos (AC4).

---

### Edge Cases

- ¿Qué pasa si una llamada falla a mitad de proceso? → el campo `error` captura el fallo; los demás campos quedan con valores conocidos (no vacíos).
- ¿Qué pasa si el modelo responde con versión ausente? → registrar "desconocida" explícitamente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El registro DEBE incluir id, hora, texto, traducción, resultado, latencia, error y versión del modelo (AC3).
- **FR-002**: En 20 llamadas, el registro DEBE tener 0 campos vacíos (AC3).
- **FR-003**: El registro DEBE excluir nombres y correos (AC4).
- **FR-004**: El registro DEBE ligar cada resultado a su solicitud (trazabilidad, objetivo 1/2).

### Key Entities

- **Registro**: fila con id, hora, texto, traducción, resultado, latencia, error, versión.
- **Solicitud**: texto de entrada + traducción + resultado + latencia.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 campos vacíos en 20 llamadas (AC3).
- **SC-002**: 0 nombres/correos en el registro (AC4).
- **SC-003**: 100 % de resultados ligados a su solicitud (trazabilidad).

## Assumptions

- El registro es un CSV/almacén local (gitignoreado) o tabla del módulo `registro.py`.
- La API (endpoints POST /generar, GET /health) la implementa J. C. Pérez; esta HU solo consume su salida para registrar.
