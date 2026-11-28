# Tareas · HU-48 (SPEC-049) — alcance B

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [x] T0 · Spike de RF-1 (commit `7761e3b`) y aprobación humana del alcance B: RF-4/AC4 fuera.
- [x] T1 · Redactar `plan.md` y `tasks.md`, incluida la decisión de AC2 (CSV escrito en M2).
- [x] T2 · Prueba en RED de la tabla de precios (`tests/test_materiales.py`).
- [x] T3 · `data/materiales.toml` + `src/m2_cad/materiales.py` +
  `scripts/verify_materiales.py` + `make materiales-check` (dentro de `check` y del `lint` del
  espejo).
- [x] T4 · Prueba en RED del guard de material y del CSV extendido
  (`tests/test_hu48_materiales_bom.py`): AC2, AC3 y RNF-3.
- [x] T5 · `Causa.MATERIAL_NO_SOPORTADO` en `declinacion.py` y `validar_materiales()` en
  `verificar_programa`, con alias `al` → `aluminum`.
- [x] T6 · `_resumen_materiales` por `(tipo, material)` y `_csv_materiales` en `pipeline.py`;
  retirar el uso de `constraint_kit.bom`.
- [x] T7 · Actualizar `tests/test_pipeline.py` (cabecera extendida) sin perder la prueba que
  fija el comportamiento previo de las cuatro columnas.
- [x] T8 · `make corpus-dorado` y `make check` con `M2_DOWNLOAD_SECRET`.
- [x] T9 · Documentar `spec.md` (decisión del spike), `specs/README.md`, `CONSTITUTION.md`,
  `README.md` si aplica, y `evidence.md`.
