---

description: "Actividades de implementación para HU-09 (CI/CD con GitHub Actions y pre-commit)"

---

# Tasks: CI/CD con GitHub Actions y pre-commit (HU-09)

**Input**: `specs/005-ci-github-actions/spec.md` + `plan.md`

**Prerequisites**: spec.md ✅, plan.md ✅ · El scaffold ya trae `.github/workflows/ci.yml` y `.pre-commit-config.yaml` (falta completarlos)

**Organización**: tareas agrupadas por historia de usuario (US1–US5).

**Mapeo CPM**: HU-09 · actividad L (Pruebas pytest y CI, días 8–9).

## Formato: `[ID] [P?] [US#] Descripción`

---

## Phase 1: User Story 1 - CI en cada PR (P1)

- [ ] T001 [US1] Configurar `.github/workflows/ci.yml` para ejecutar pytest y Ruff en cada PR a `develop` (con `uv sync`) (AC1)

---

## Phase 2: User Story 2 - Cobertura (P2)

- [ ] T002 [US2] Configurar pytest-cov para medir cobertura de `src/` y fijar el umbral ≥ 70 % en la CI (AC2)

---

## Phase 3: User Story 3 - Ruff limpio (P1)

- [ ] T003 [US3] Ajustar `[tool.ruff]` (reglas E, F, I, B) y dejar el código con 0 errores de Ruff (AC3)

---

## Phase 4: User Story 4 - pre-commit bloqueante (P1)

- [ ] T004 [US4] Configurar `.pre-commit-config.yaml` para bloquear errores de Ruff y archivos de pesos (`.gguf`, `.safetensors`) antes de cada commit (AC4)

---

## Phase 5: User Story 5 - develop protegido (P2)

- [ ] T005 [US5] Configurar la protección de rama `develop` en GitHub: CI en verde + una aprobación obligatoria (AC5)

---

## Dependencies & Execution Order

- T001 primero (base de CI).
- T002, T003, T004 pueden ir en paralelo tras T001.
- T005 es configuración de GitHub (branch protection), independiente.

## Criterios de aceptación cubiertos

| AC | Tarea |
|----|-------|
| AC1 (pytest + Ruff en PR) | T001 |
| AC2 (cobertura ≥ 70 %) | T002 |
| AC3 (0 errores Ruff E/F/I/B) | T003 |
| AC4 (pre-commit bloquea Ruff y pesos) | T004 |
| AC5 (develop exige CI verde + aprobación) | T005 |

## Notes

- El CI usa `uv sync` (regla del curso: sin pip install ni requirements.txt).
- `.gguf`/`.safetensors` ya están en `.gitignore`; pre-commit es la segunda barrera.
- Dependabot apunta a develop (target-branch), así que sus PRs también pasan por esta CI.
