# Feature Specification: CI/CD con GitHub Actions y pre-commit (HU-09)

**Feature Branch**: `005-ci-github-actions`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "HU-09 (2 SP) — Como integrante del equipo, quiero que GitHub Actions ejecute pytest y Ruff en cada pull request a develop y que pre-commit bloquee errores antes de cada commit, para integrar cambios sin romper lo que ya funciona."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CI en cada PR (Priority: P1)

GitHub Actions ejecuta pytest y Ruff en cada pull request hacia develop.

**Why this priority**: Es la barrera de calidad que evita regresiones al integrar.

**Independent Test**: un PR a develop dispara el workflow con pytest y Ruff (AC1).

**Acceptance Scenarios**:

1. **Given** un pull request a develop, **When** se abre, **Then** GitHub Actions ejecuta pytest y Ruff (AC1).

---

### User Story 2 - Cobertura mínima (Priority: P2)

La cobertura de pruebas en `src/` es ≥ 70 %.

**Why this priority**: Garantiza que el código del núcleo esté protegido por pruebas.

**Independent Test**: el reporte de cobertura de `src/` es ≥ 70 % (AC2).

**Acceptance Scenarios**:

1. **Given** la suite pytest, **When** se mide la cobertura de `src/`, **Then** es ≥ 70 % (AC2).

---

### User Story 3 - Ruff limpio (Priority: P1)

Cero errores de Ruff con las reglas E, F, I y B.

**Why this priority**: Mantiene estilo e importaciones consistentes y evita bugs comunes.

**Independent Test**: `ruff check` no reporta errores (AC3).

**Acceptance Scenarios**:

1. **Given** el código fuente, **When** corre Ruff (E, F, I, B), **Then** hay 0 errores (AC3).

---

### User Story 4 - pre-commit bloqueante (Priority: P1)

pre-commit bloquea errores de Ruff y archivos de pesos (`.gguf`) antes de cada commit.

**Why this priority**: Evita que entren al historial archivos enormes o código con errores.

**Independent Test**: un commit con error de Ruff o un `.gguf` es bloqueado (AC4).

**Acceptance Scenarios**:

1. **Given** un commit con error de Ruff, **When** se intenta, **Then** pre-commit lo bloquea (AC4).
2. **Given** un commit con un archivo de pesos, **When** se intenta, **Then** pre-commit lo bloquea (AC4).

---

### User Story 5 - develop protegido (Priority: P2)

`develop` exige CI en verde y una aprobación antes de fusionar.

**Why this priority**: Cierra el ciclo: nada entra a develop sin pasar la CI.

**Independent Test**: un PR sin CI verde o sin aprobación no se puede fusionar (AC5).

**Acceptance Scenarios**:

1. **Given** un PR a develop, **When** se intenta fusionar, **Then** requiere CI en verde y una aprobación (AC5).

---

### Edge Cases

- ¿Qué pasa si una dependencia rompe la CI? → Dependabot abre PR (target develop) y la CI lo valida antes de fusionar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: GitHub Actions DEBE ejecutar pytest y Ruff en cada PR a develop (AC1).
- **FR-002**: La cobertura de `src/` DEBE ser ≥ 70 % (AC2).
- **FR-003**: Ruff DEBE reportar 0 errores con reglas E, F, I y B (AC3).
- **FR-004**: pre-commit DEBE bloquear errores de Ruff y archivos de pesos (AC4).
- **FR-005**: develop DEBE exigir CI en verde y una aprobación (AC5).

### Key Entities

- **Workflow CI**: `.github/workflows/ci.yml`.
- **Config Ruff**: `pyproject.toml` (`[tool.ruff]`).
- **Config pre-commit**: `.pre-commit-config.yaml`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: CI corre pytest + Ruff en todo PR (AC1).
- **SC-002**: cobertura ≥ 70 % (AC2).
- **SC-003**: 0 errores Ruff (AC3).
- **SC-004**: pre-commit bloquea Ruff y pesos (AC4).
- **SC-005**: develop exige CI verde + aprobación (AC5).

## Assumptions

- La rama de integración es `develop` (según la propuesta y Dependabot).
- pytest-cov es la herramienta de cobertura (ya en el grupo dev de `pyproject.toml`).
