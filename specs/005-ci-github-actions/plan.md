# Implementation Plan: CI/CD con GitHub Actions y pre-commit (HU-09)

**Branch**: `005-ci-github-actions` | **Date**: 2026-11-03 | **Spec**: `specs/005-ci-github-actions/spec.md`

**Input**: Feature specification from `/specs/005-ci-github-actions/spec.md`

## Summary

Dejar operativa la integración continua: workflow de GitHub Actions (pytest + Ruff + cobertura) sobre PRs a develop, Ruff con reglas E/F/I/B sin errores, pre-commit bloqueante (Ruff + pesos) y protección de develop (CI verde + aprobación).

## Technical Context

**Language/Version**: Python 3.12 · tooling ya presente en el scaffold

**Primary Dependencies**: pytest, pytest-cov, Ruff, pre-commit (grupo dev de `pyproject.toml`)

**Storage**: N/A (configuración de CI/tooling)

**Testing**: pytest + pytest-cov (cobertura ≥ 70 % en `src/`)

**Target Platform**: GitHub Actions (ubuntu) + pre-commit local

**Project Type**: repositorio Python (src-layout)

**Constraints**: sin `pip install`; se usa `uv` (el CI instala con `uv sync`)

**Scale/Scope**: PRs a `develop`; Dependabot también apunta a develop

## Constitution Check

*GATE: uv/uv.lock (no requirements.txt), src-layout, Conventional Commits en español. El CI debe usar `uv sync` para instalar dependencias.*

## Project Structure

```text
.github/workflows/
└── ci.yml                  # pytest + Ruff + cobertura en PR a develop

.pre-commit-config.yaml     # Ruff + bloqueo de archivos de pesos

pyproject.toml              # [tool.ruff] reglas E,F,I,B · [tool.pytest.ini_options] · pytest-cov
```

**Structure Decision**: la configuración ya existe en el scaffold; esta HU la completa (cobertura, protección de develop, bloqueo de pesos) y la deja en verde.

## Complexity Tracking

*(Sin violaciones.)*
