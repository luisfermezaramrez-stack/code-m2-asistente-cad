# Evidencia · HU-55 (SPEC-056)

Fecha: 2026-11-27
Issue: https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/115
Rama: `feature/hu-55-releases-automaticos` (worktree aislado desde `origin/main` `267964e`)
PR: https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/153
Revisión solicitada a: `luisfermezaramrez-stack`

## Spec-first y dependencias

- Leídas `spec.md`, `plan.md` y `tasks.md` antes de tocar código.
- `SPEC-032` presente en `main`: PR #130 `a71c3cc` y PR #138 `0906338` son ancestros
  de `origin/main`.
- `SPEC-058` también integrada: PR #120 `f787d4a` es ancestro de `origin/main`; por tanto
  no se crea rama de release: `main` es la única rama de integración y publicación.
- No existía rama ni PR previa de HU-55; `gh api .../branches/feature/hu-55-releases-automaticos`
  devolvió 404.
- Auditoría `jan-project-standard` sin `--force`:
  `✓ OK: 4 · ≠ DIFIERE: 21 · ✖ FALTA: 0`.

## Implementación

- `src/m2_cad/releases.py`: parseo de Conventional Commits; `feat` → minor,
  `fix`/`perf` → patch, `BREAKING CHANGE`/`!:` → major; aviso explícito cuando cambia el
  contrato `/v1`; render de `CHANGELOG.md`; lectura y sincronización de la versión en
  `pyproject.toml`.
- `scripts/generar_release.py`: CLI con `--dry-run`, `--verificar`, `--preparar`,
  `--version` y `--titulo`. El modo seco no crea etiquetas ni publica releases.
- `tests/test_releases_automaticos.py`: pruebas de AC1, AC2, AC3 y RNF-3.
- `CHANGELOG.md` inicial con `v1.0.1`; `pyproject.toml` y `uv.lock` sincronizados en `1.0.1`.
- `.github/workflows/ci.yml`: permisos mínimos, validación del título de PR, `workflow_dispatch`
  y job `release` condicionado a `push` en `main` del repositorio oficial, con
  `gh release create "v$VERSION"`.
- `Makefile`: `release-dry-run`, `release-check`, `release-version`; `release-check`
  incluido en `check` y `scripts/generar_release.py` incluido en `lint`.
- Documentación: `README.md`, `CONSTITUTION.md` y este índice.

## Validación

| Comando | Resultado |
|---|---|
| `uv run --locked pytest -q tests/test_releases_automaticos.py` | `7 passed in 0.29s` |
| `make release-check` | `Coherencia verificada: pyproject y CHANGELOG en v1.0.1.` |
| `make release-dry-run` | Base `v1.0.1`; `82` commits convencionales; versión propuesta `1.1.0`; `Etiquetas creadas: ninguna; releases publicadas: ninguna.` |
| SHA evaluado | `0463881c86f2966a3586ef54cb4b983e88bb4c4c` (head del PR tras integrar `main`) |
| `make check` | Lint, API types/contract, prompts, Vitest `94/94`, typecheck y build OK; pytest `739 passed`, `6 failed`, cobertura `92.23%` (≥ 70 %) |
| `uv lock --check` | `Resolved 172 packages` — lockfile coherente con `pyproject.toml` |
| `git tag --list` | Solo `v1.0`, `v1.0.1` — no se crearon etiquetas |
| Auditoría `jan-project-standard` | `OK 4 · DIFIERE 21 · FALTA 0` |
| `--titulo "feat(hu-55): ..."` local | `Título convencional: feat(hu-55)` |
| CI automático (PR #153) | https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46028065656 sobre `0463881c86f2966a3586ef54cb4b983e88bb4c4c` — `titulo-pr` ✓, `test` ✓, `e2e` ✓; `release` omitido al no ser `push main` |
| CI manual (PR #153) | https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46028074113 sobre `0463881c86f2966a3586ef54cb4b983e88bb4c4c` — `test` ✓, `e2e` ✓; `titulo-pr`/`release` omitidos por ser `workflow_dispatch` |

Las 6 fallas de `make check` son preexistentes y ajenas a HU-55:

- `tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia`
  (7 divergencias de huellas STEP por CAD local).
- `tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas` y
  `::test_ac1_duplicados_concurrentes_son_idempotentes` (`msvcrt.locking` → Errno 36 en Windows).
- `tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos` y
  `::test_ac4_no_borra_directorio_con_enlace_interno` (WinError 1314, requiere privilegio de symlink).
- `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`
  (`p95=247.4 ms` en Windows; mlflow local).

Ninguna falla proviene de `src/m2_cad/releases.py`, `scripts/generar_release.py` ni
`tests/test_releases_automaticos.py`.

## Criterios de aceptación

- **AC1** — Release semántico desde Conventional Commits: `7` pruebas nuevas en verde;
  el seco propone `1.1.0` sobre `v1.0.1` con `82` commits convencionales.
- **AC2** — Changelog y salida de release: `v1.1.0 - 2026-11-27` generado en seco;
  `pyproject.toml` y `CHANGELOG.md` coherentes en la versión base; `git tag --list`
  sigue sin etiquetas nuevas.
- **AC3** — Integración CI/CD: workflow con `permissions` explícitos, título validado,
  job `release` limitado a `push main`, tag `v$VERSION` y notas desde `.release-notes.md`;
  CI automático del PR en verde sobre `0463881` (`titulo-pr`, `test` y `e2e`) y CI manual
  en verde sobre el mismo SHA (`test` y `e2e`). La publicación real se dejó para el job
  de CI, sin ejecutarla localmente.

## Limitaciones

- No se creó tag ni release real, por instrucción de validar solo en seco.
- El CI automático apareció tras integrar `main` en la rama y verificó el SHA `0463881`;
  el run manual enlazado arriba es una verificación adicional reproducible, no un sustituto.
- `titulo-pr` pasó en el CI automático y además se validó localmente con el título exacto
  del PR, porque el dispatch manual no expone `github.event.pull_request.title`.
- El job `release` solo se ejecutará tras merge en `main` y requiere que `GITHUB_TOKEN`
  pueda escribir en esa rama; con protección activa puede necesitar un token con push.
