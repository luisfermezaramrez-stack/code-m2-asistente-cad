# Tareas · HU-46 (SPEC-047)

Checklist en orden de ejecución; la evidencia final estará en [evidence.md](./evidence.md).

- [x] T0 · Confirmar dependencias: rama creada desde `feature/hu-44-banco-ci-replay` (PR #151
  en revisión), leer spec, `CONSTITUTION.md`, `AGENTS.md`, `banco.py`, `declinacion.py` y el
  workflow de baseline.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Añadir `causa` al CSV por caso de `banco.py` con `declinacion.normalizar()`, sin
  cambiar el resumen ni `make bench`.
- [x] T3 · Crear `src/m2_cad/alertas.py`: esquema v1 del baseline, métricas por caso, deltas
  contra umbrales versionados, desglose por familia/causa y generación del resumen Markdown.
- [x] T4 · Crear `scripts/verificar_alertas.py`: CLI con `--corrida-dir`, `--corrida`, `--csv`,
  `--baseline`, `--salida`, `--no-fail` y `--actualizar-baseline` con trazabilidad obligatoria.
- [x] T5 · Generar `data/alertas_baseline.json` desde la corrida replay de HU-44 y declarar su
  origen (`referencia-banco`), autor, fecha y corrida.
- [x] T6 · Añadir `make alertas`, el paso en `ci.yml` y la comparación con issue en
  `.github/workflows/banco-baseline.yml`.
- [x] T7 · Crear `tests/test_hu46_alertas.py` con pruebas para AC1–AC4, catálogo cerrado,
  umbrales del artefacto, artefacto incompleto y modo `--no-fail`.
- [x] T8 · Documentar en `README.md`, actualizar `CONSTITUTION.md`, `specs/README.md` y el
  estado de `spec.md` en la misma rama.
- [x] T9 · Ejecutar Ruff, pre-commit, pytest (nuevas + relacionadas + suite con cobertura),
  contratos y frontend; ejecutar `make alertas` sobre el replay real y registrar evidencia.
  Abrir PR a `main` y añadir su número al evidence.
