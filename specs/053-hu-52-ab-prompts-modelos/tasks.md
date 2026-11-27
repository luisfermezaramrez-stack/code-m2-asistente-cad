# Tareas · HU-52 (SPEC-053)

Checklist en orden de ejecución; la evidencia final estará en [evidence.md](./evidence.md).

- [x] T0 · Auditar el repo con el estándar, confirmar dependencias (SPEC-034 y SPEC-045,
  PR #151 en revisión) y crear la rama desde `feature/hu-44-banco-ci-replay`.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Añadir `prompts.cargar_version()` y una segunda versión de `planner` no vigente,
  con hash verificado por `make prompts-check`.
- [x] T3 · Crear `src/m2_cad/ab.py`: variantes, ejecución aislada con prompt/modelo,
  métricas por familia, casos cambiados y reporte Markdown. Sin promoción automática.
- [x] T4 · Crear `scripts/comparar_ab.py`: CLI con variantes A/B, banco compartido, modo
  real/replay, trazabilidad en MLflow y salida `0`/`2`.
- [x] T5 · Añadir `make ab` y `make ab-replay` sin incluir la comparación real en CI.
- [x] T6 · Crear `tests/test_hu52_ab.py` para AC1–AC3, mismo banco/temperatura, replay,
  trazabilidad y ausencia de promoción automática (sin red, key, GPU ni MLflow real).
- [x] T7 · Documentar en `README.md`, actualizar `CONSTITUTION.md`, `specs/README.md` y el
  estado de `spec.md` en la misma rama.
- [x] T8 · Ejecutar Ruff, pre-commit, pytest (nuevas + relacionadas + suite con cobertura),
  contratos, frontend y una comparación A/B en replay; registrar evidencia y abrir PR.
