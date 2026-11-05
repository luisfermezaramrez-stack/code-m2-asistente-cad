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

- [x] T001 [US1] Configurar `.github/workflows/ci.yml` para ejecutar pytest y Ruff en cada PR a `develop` (con `uv sync`) (AC1)
  - Evidencia: el workflow ya corría en PR/push a `develop`; se agregó `concurrency`, `enable-cache` y `python-version-file: .python-version`. Pasos validados en local: `uv sync --dev` (exit 0), `uv run ruff check src tests`, `uv run pytest --cov=src/m2_cad`.

---

## Phase 2: User Story 2 - Cobertura (P2)

- [x] T002 [US2] Configurar pytest-cov para medir cobertura de `src/` y fijar el umbral ≥ 70 % en la CI (AC2)
  - Evidencia: `[tool.coverage.report] fail_under = 70` en `pyproject.toml`; el reporte imprime `Required test coverage of 70.0% reached` y falla por debajo del umbral tanto en la CI como en `make cov`.
  - Nota: hoy `src/m2_cad/*` son módulos vacíos (0 sentencias), así que el 100 % medido es vacío. El umbral empieza a exigir de verdad cuando entren el pipeline (HU-04) y el registro (HU-06).

---

## Phase 3: User Story 3 - Ruff limpio (P1)

- [x] T003 [US3] Ajustar `[tool.ruff]` (reglas E, F, I, B) y dejar el código con 0 errores de Ruff (AC3)
  - Evidencia: `uv run ruff check src tests` → `All checks passed!` con las reglas E, F, I y B ya fijadas en `[tool.ruff.lint]`.

---

## Phase 4: User Story 4 - pre-commit bloqueante (P1)

- [x] T004 [US4] Configurar `.pre-commit-config.yaml` para bloquear errores de Ruff y archivos de pesos (`.gguf`, `.safetensors`) antes de cada commit (AC4)
  - Evidencia: se agregó el hook local `no-model-weights` (`scripts/check-weights.sh`), que bloquea por extensión sin importar el tamaño. Verificado con un `.gguf` de 2 KB (bloqueado, exit 1) y con un error de Ruff no auto-corregible (bloqueado, exit 1).

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
