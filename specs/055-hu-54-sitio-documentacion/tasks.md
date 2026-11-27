# Tareas de implementación · HU-54 (SPEC-055)

## T0 — Planificación

- [x] Leer SPEC-055 y verificar que SPEC-030 (HU-29) está integrada en `main`.
- [x] Crear worktree `feature/hu-54-sitio-documentacion` desde `origin/main`.
- [x] Escribir `plan.md` con la decisión MkDocs, exclusiones, nav, enlaces y publicación.

## T1 — Configuración del sitio

- [x] Crear `mkdocs.yml` con `docs_dir: docs-build`, `site_dir: .site`, nav de cinco
      secciones, reinyección de archivos punto y `validation.links.not_found: warn`.
- [x] Añadir `scripts/build_docs_site.py` para generar el staging desde los Markdown
      versionados, copiar recursos enlazados y neutralizar STEP inexistentes de HU-07.
- [x] Añadir `mkdocs==1.6.1` al grupo `dev` con `uv add --dev --no-sync` y regenerar `uv.lock`.
- [x] Añadir targets `docs-stage`, `docs-build` y `docs-serve` al `Makefile` e incluir
      `docs-build` en `check`; añadir el script a `lint`.
- [x] Ignorar `docs-build/`, `.site/` y `site/` en `.gitignore`.

## T2 — Enlaces y contenido

- [x] Corregir únicamente los enlaces que `mkdocs build --strict` marque como rotos, sin
      reescribir la documentación versionada: STEP no versionados y archivos punto.
- [x] Verificar que `docs/runbook-operativo.md` aparece en la navegación y que su contenido
      no se duplica en el sitio.

## T3 — Publicación y registros

- [x] Crear `.github/workflows/docs-pages.yml` con build estricto y deploy a GitHub Pages
      desde `main`.
- [x] Crear `tests/test_docs_sitio.py` con las invariantes de nav, strict y workflow.
- [x] Registrar la decisión en `CONSTITUTION.md` y el índice del sitio en `docs/README.md`.
- [x] Completar `evidence.md` con comandos, salidas, PR y estado real de publicación.

## T4 — Verificación y entrega

- [x] `make docs-build` sin errores ni advertencias de enlaces rotos.
- [ ] `make check` ejecutado: 696 pasan, 5 fallas preexistentes de Windows/CAD/MLflow;
      auditoría no destructiva sin FALTA y revisiones de git sin whitespace.
- [x] Commit, push y PR a `main` con `Closes #114` (PR #150).
- [x] Verificar CI del PR y reportar qué falta para AC2: aprobación, merge y Pages con
      fuente GitHub Actions.

## Criterios de aceptación cubiertos

- **AC1 — Build local:** T1, T2 y T4 (`make docs-build` estricto).
- **AC2 — Publicación:** T3 y T4 (workflow sobre `main`; estado real informado).
- **AC3 — Runbook accesible:** T1 y T2 (enlace directo desde la nav de Operación).
