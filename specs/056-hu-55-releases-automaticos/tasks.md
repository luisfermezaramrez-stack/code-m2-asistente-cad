# Tareas · HU-55 (SPEC-056)

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [x] T0 · Leer SPEC-056, SPEC-032 y SPEC-058; verificar que SPEC-032 está en `main`
  (`a71c3cc`, `0906338`) y que no hay rama ni PR previa de HU-55; auditoría no destructiva.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Crear `src/m2_cad/releases.py` con parseo de Conventional Commits, cálculo
  semántico, regla de contrato `/v1` y render del changelog.
- [x] T3 · Crear `scripts/generar_release.py` con modos `--dry-run`, `--verificar`,
  `--preparar`, `--titulo` y `--version`, sin etiquetas ni releases en seco.
- [x] T4 · Añadir `tests/test_releases_automaticos.py` para AC1–AC3 y RNF-3.
- [x] T5 · Añadir `CHANGELOG.md` inicial y sincronizar `pyproject.toml` con `v1.0.1`.
- [x] T6 · Añadir validación del título de PR y job `release` a `.github/workflows/ci.yml`.
- [x] T7 · Exponer `make release-dry-run`, `release-check` y `release-version`; incluir
  `release-check` en `make check`.
- [x] T8 · Documentar `README.md`, `CONSTITUTION.md` y `specs/README.md` en la misma rama.
- [ ] T9 · Ejecutar el flujo en seco, `make check`, pre-commit y auditoría; abrir PR con
  `Closes #115`, solicitar revisión y escribir `evidence.md`.
