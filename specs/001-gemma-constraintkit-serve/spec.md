# Feature Specification: Servir Gemma 4 12B ConstraintKit (HU-01)

**Feature Branch**: `001-gemma-constraintkit-serve`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "HU-01 (5 SP) — Como desarrollador del equipo, quiero tener Gemma 4 12B ConstraintKit (GGUF Q6_K) servido con llama.cpp y el contenedor de constraint-kit funcionando en la GPU alquilada, para conectar el pipeline sobre un entorno verificado y reproducible desde el día 4."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pesos del modelo descargados y verificados (Priority: P1)

El equipo descarga el archivo GGUF Q6_K (9,8 GB) del modelo y verifica su integridad contra el SHA-256 publicado por el autor, de modo que el entorno parta de pesos íntegros y reproducibles.

**Why this priority**: Sin pesos íntegros nada aguas abajo es confiable; es la base de todo el pipeline.

**Independent Test**: Se descarga el GGUF y `sha256sum` coincide con el hash publicado en la tarjeta del modelo (Hugging Face).

**Acceptance Scenarios**:

1. **Given** el enlace oficial al GGUF Q6_K, **When** se descarga el archivo, **Then** el SHA-256 calculado coincide con el publicado (AC1).
2. **Given** un archivo con hash distinto, **When** se verifica, **Then** el entorno se marca como inválido y no se usa.

---

### User Story 2 - Modelo servido con llama.cpp (Priority: P1)

llama.cpp sirve el modelo con un contexto de 8 192 tokens ocupando como máximo 16 GB de VRAM, dentro del límite de la GPU alquilada.

**Why this priority**: Define el contrato de inferencia (contexto y memoria) sobre el que se monta el pipeline.

**Independent Test**: Se levanta el servidor y se confirma que carga con `--ctx-size 8192` y VRAM ≤ 16 GB (AC2).

**Acceptance Scenarios**:

1. **Given** llama.cpp instalado y el GGUF presente, **When** se inicia el servidor, **Then** el modelo carga con 8 192 tokens y reporta ≤ 16 GB de VRAM (AC2).

---

### User Story 3 - Contenedor de constraint-kit funcionando (Priority: P1)

El contenedor del autor (con Python 3.12 y las dependencias C++ de OpenCascade/SolveSpace) queda operativo y pasa las 113 pruebas de su suite.

**Why this priority**: El único entorno probado por el autor es ese contenedor; fuera de él fallan 27 de 113 pruebas.

**Independent Test**: Se ejecuta la suite dentro del contenedor y 113 de 113 pruebas pasan (AC3).

**Acceptance Scenarios**:

1. **Given** la imagen del contenedor del autor, **When** se ejecuta la suite, **Then** 113 de 113 pruebas pasan (AC3).

---

### User Story 4 - Prueba end-to-end de generación (Priority: P2)

Cinco solicitudes de ejemplo devuelven un programa que pasa la validación `/dsl/check`, confirmando que modelo + contenedor generan salida válida de punta a punta.

**Why this priority**: Verifica la integración real modelo→motor, no solo piezas aisladas.

**Independent Test**: Se envían 5 solicitudes y las 5 devuelven un programa que pasa `/dsl/check` (AC4).

**Acceptance Scenarios**:

1. **Given** modelo servido y contenedor activo, **When** se envían 5 solicitudes, **Then** 5 de 5 devuelven un programa que pasa `/dsl/check` (AC4).

---

### User Story 5 - Versiones documentadas (Priority: P2)

Las versiones exactas del modelo, llama.cpp, constraint-kit y el contenedor quedan registradas en el README para reproducibilidad.

**Why this priority**: Permite reconstruir el entorno exacto y es criterio de aceptación explícito.

**Independent Test**: El README lista las versiones de modelo, llama.cpp, constraint-kit y contenedor (AC5).

**Acceptance Scenarios**:

1. **Given** el entorno operativo, **When** se documenta, **Then** el README registra las versiones exactas (AC5).

---

### Edge Cases

- ¿Qué pasa si la GPU alquilada no está disponible el día 1? → Reserva anticipada; plan B con DeepSeek (HU-06 / objetivo 2).
- ¿Qué pasa si la descarga del GGUF se interrumpe? → Reanudar y re-verificar SHA-256.
- ¿Qué pasa si el contenedor no pasa 113/113? → Usar la imagen del autor sin modificar (la modificación de dependencias C++ es la causa conocida de los fallos).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE verificar que el SHA-256 del GGUF coincide con el publicado (AC1).
- **FR-002**: El sistema DEBE servir el modelo con llama.cpp usando un contexto de 8 192 tokens y ≤ 16 GB de VRAM (AC2).
- **FR-003**: El sistema DEBE pasar 113 de 113 pruebas del contenedor de constraint-kit (AC3).
- **FR-004**: El sistema DEBE devolver, para 5 de 5 solicitudes, un programa que pasa `/dsl/check` (AC4).
- **FR-005**: El sistema DEBE registrar las versiones (modelo, llama.cpp, constraint-kit, contenedor) en el README (AC5).

### Key Entities

- **Modelo**: Gemma 4 12B ConstraintKit (GGUF Q6_K, 9,8 GB), servido por llama.cpp.
- **Contenedor**: imagen del autor de constraint-kit (Python 3.12 + OpenCascade/SolveSpace).
- **Programa generado**: salida DSL validada por `/dsl/check`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: SHA-256 del GGUF verificado al 100 % (AC1).
- **SC-002**: Modelo cargado con 8 192 tokens y ≤ 16 GB de VRAM (AC2).
- **SC-003**: 113/113 pruebas del contenedor en verde (AC3).
- **SC-004**: 5/5 solicitudes devuelven programa que pasa `/dsl/check` (AC4).
- **SC-005**: README con versiones registradas (AC5).

## Assumptions

- La GPU alquilada tiene ≥ 16 GB de VRAM (ideal 24 GB).
- El contenedor del autor se usa sin modificar (causa conocida de fallos).
- El SHA-256 publicado es la fuente de verdad de integridad.
- Python 3.12 en contenedor (constraint del proyecto M2; no 3.13).
