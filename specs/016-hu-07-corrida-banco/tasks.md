# SPEC-016 · HU-07 — Tareas del reporte del banco

- **ID**: SPEC-016 · **Historia**: #7 · **Responsable**: Carlos Eduardo Trujillo
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

## 1. Clasificación y agregación (AC2)

- [ ] T01 — Pruebas en rojo para `error_silencioso` (positiva fuera de tolerancia,
      negativa construida, declinación correcta). · Depende de: —
- [ ] T02 — Añadir `error_silencioso` y `step` a `evaluar_caso` y al final de `CAMPOS`.
      · Hecho cuando: T01 en verde y la prueba de orden de columnas previo pasa. · Depende de: T01
- [ ] T03 — Prueba en rojo y luego implementación de `resumir_por_familia`. · Depende de: T02

## 2. STEP persistente y enlaces (AC3)

- [ ] T04 — Prueba en rojo: con `--conservar-step` el STEP queda en
      `outputs/banco/<modelo>-<marca>/<id>/`; sin la opción, no queda nada. · Depende de: T02
- [ ] T05 — Implementar `--conservar-step` en `main`. · Depende de: T04
- [ ] T06 — Incluir el `run_id` de la corrida hija de MLflow en el registro cuando el
      seguimiento está activo. · Depende de: T02

## 3. Reporte (AC1, AC2, AC4, AC5)

- [ ] T07 — Prueba en rojo y luego implementación de `reporte_markdown` (metas,
      cumple/no cumple, tabla por caso, sección de fallos). · Depende de: T03, T06
- [ ] T08 — Añadir `--reporte PATH` y el objetivo `make bench-report`. · Depende de: T05, T07
- [ ] T09 — Ejecutar `make bench-report` con DeepSeek y guardar
      `docs/reporte-banco.md`. · Hecho cuando: el reporte existe con las 6 familias. · Depende de: T08
- [ ] T10 — Si una meta falla: documentar la causa por caso y el ajuste, y repetir
      **una** vez conservando ambos reportes. · Depende de: T09

## 4. Cierre

- [ ] T11 — `make check` en verde; enlazar el reporte en la tarjeta #7 y en SPEC-017. · Depende de: T09
- [ ] T12 — PR hacia `develop` con `Closes #7`, enlace a esta spec y revisión de un
      compañero. · Depende de: T11
