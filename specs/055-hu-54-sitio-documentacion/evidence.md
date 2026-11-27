# Evidencia de implementación · HU-54 (SPEC-055)

## Contexto

- Issue: https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/114
- SPEC: `specs/055-hu-54-sitio-documentacion/spec.md`
- Base: `origin/main` en `094fe9b` tras `git fetch origin --prune`.
- HU-29 / SPEC-030 (runbook) verificada como ancestro de `main` en el merge `3b29542`.
- Worktree: `C:\Users\cetd9\AppData\Local\Temp\opencode\hu54-docs-site`.
- Rama: `feature/hu-54-sitio-documentacion`.

## AC1 — Build local

**Estado: CUMPLIDO.**

```text
$ make docs-build
uv run --locked python scripts/build_docs_site.py
staging: 181 Markdown, 20 recursos enlazados
uv run --locked mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory:
            C:\Users\cetd9\AppData\Local\Temp\opencode\hu54-docs-site\.site
INFO    -  Documentation built in 1.84 seconds
```

- No hay errores ni advertencias de enlaces rotos (`validation.links.not_found: warn`
  bajo `--strict`).
- Los 30 enlaces a STEP no versionados de `docs/hu07/**/reporte.md` se convierten en
  código en el staging generado; el Markdown versionado no se reescribe.
- Los archivos punto enlazados (`.python-version`, `.env.example`, `.gitignore`,
  `.github/dependabot.yml`, `.opencode/rules/tgrep.md`) se reinyectan en el staging y se
  publican sin romper enlaces.
- `docs-build/` y `.site/` quedan gitignored; la fuente es siempre el Markdown versionado.

## AC2 — Publicación

**Estado: PREPARADO; depende de fusión en `main` y de habilitar GitHub Pages.**

- `.github/workflows/docs-pages.yml` construye con `make docs-build` y despliega con
  `actions/upload-pages-artifact@v4` + `actions/deploy-pages@v4` en `push` a `main`.
- El workflow usa el mismo `uv` fijado (`0.13.5`), vendoriza constraint-kit y sincroniza
  con `uv.lock`, sin `pip` y sin GPU/API key.
- Consulta actual al API de Pages:

```text
$ gh api repos/luisfermezaramrez-stack/code-m2-asistente-cad/pages
{"message":"Not Found", ... "status":"404"}
gh: Not Found (HTTP 404)
```

**Falta exactamente:** fusionar el PR en `main` y habilitar GitHub Pages en el repo con
fuente *GitHub Actions* (Configuración → Pages → Build and deployment → Source:
GitHub Actions). Un PR sobre una rama no puede publicar; el workflow tampoco puede
activar Pages por sí solo.

## AC3 — Runbook accesible

**Estado: CUMPLIDO.**

- `mkdocs.yml` declara `Runbook operativo: docs/runbook-operativo.md` dentro de la nav de
  Operación.
- En el sitio generado: `.site/docs/runbook-operativo/index.html`, con
  `<a href="./" class="dropdown-item active">Runbook operativo</a>` y el `<h1>` del
  runbook. El texto se sirve desde SPEC-030 sin duplicarse en un archivo nuevo.

## Pruebas y validación

```text
$ uv run --locked pytest tests/test_docs_sitio.py -q
.....                                                                    [100%]
5 passed in 1.12s

$ make lint
All checks passed!

$ make check
... 9 test files / 82 tests Vitest passed
... vue-tsc --noEmit sin errores
... vite build ✓ built in 456ms
staging: 181 Markdown, 20 recursos enlazados
INFO    -  Documentation built in 1.84 seconds
FAILED tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia
FAILED tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas
FAILED tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos
FAILED tests/test_hu30_retencion.py::test_ac4_no_borra_directorio_con_enlace_interno
FAILED tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms
5 failed, 696 passed, 33 warnings in 100.88s
TOTAL 3702 295 92% — Required test coverage of 70.0% reached.
```

Las 5 fallas son preexistentes y ajenas a HU-54, reproducidas en Windows con el venv
prestado: 7 divergencias de huella STEP del corpus dorado, `msvcrt.locking` con
`EDEADLK` en 80 escrituras concurrentes, `WinError 1314` al crear symlinks y p95 de
92,6 ms en la sobrecarga de MLflow (límite 50 ms). Ninguna toca `mkdocs.yml`, el script
de staging, el workflow ni los specs. La nueva prueba `tests/test_docs_sitio.py` pasa.

Para ejecutar `make check` en este worktree se usó el venv de la copia principal con
`UV_PROJECT_ENVIRONMENT`, `UV_NO_SYNC=1`, `PYTHONPATH=src` y un `M2_DOWNLOAD_SECRET`
efímero, además de `make frontend-install` para poblar `node_modules/`.

## Estándar del proyecto

```text
$ python .../jan-project-standard/scripts/new_project.py --path . --audit
✓ OK: 4 · ≠ DIFIERE: 21 · ✖ FALTA: 0
```

Sin `--force`; las 21 diferencias son personalizaciones preexistentes del repositorio.

## Entrega

- PR: https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/150 — abierto,
  base `main`, head `feature/hu-54-sitio-documentacion`, `Closes #114`.
- CI del PR: `test`, `e2e`, `dependencias`, `secretos` y `espejo` en verde; el merge está
  `BLOCKED` sólo por `reviewDecision=REVIEW_REQUIRED` (sin aprobaciones registradas).
- La rama se actualizó con `origin/main` mediante merge no destructivo (`95414e8`) porque
  `main` avanzó con HU-51; no hubo conflictos y el build estricto sigue limpio con
  183 Markdown y 20 recursos enlazados.
- Publicación real: NO; requiere aprobación y merge en `main`, además de habilitar Pages
  con fuente GitHub Actions.
