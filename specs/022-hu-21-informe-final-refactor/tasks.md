# SPEC-022 — Tareas del refactor del informe final

- **ID**: SPEC-022 · **Tipo**: refactor · **Historia**: HU-21 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [x] T01 — Especificar la historia (esta spec) y cargarla en el tablero (#73). · Depende de: —
- [x] T02 — Actualizar el objetivo 4 y el resumen de `docs/informe-final.md` (AC1). ·
      Depende de: T01
      · Evidencia: objetivo 4 = 8/9 (simulado) y resumen actualizado.
- [x] T03 — Actualizar «Estado del tablero» y el enlace al proyecto 1 (AC2). · Depende de: T01
      · Evidencia: conteo 21/22 del 2026-11-14 y enlace al proyecto 1.
- [x] T04 — Actualizar SPEC-017 (estado, HU-11 simulada, `tasks.md`) y los AC del issue
      #13 (AC3). · Depende de: T02, T03
      · Evidencia: SPEC-017 «Implementada», tasks T02–T07 marcadas, AC de #13 marcados.
- [x] T05 — Actualizar `specs/README.md` con los estados reales (AC4). · Depende de: T04
      · Evidencia: PR de 006, 010, 016, 017, 019 y 020 y sus estados.
- [x] T06 — Verificar enlaces relativos del informe y `make check` (AC5). · Depende de: T05
      · Evidencia: 17/17 enlaces relativos existen; `make check` 311 passed, cobertura 96,52 %.
- [ ] T07 — PR hacia `develop` con `Closes #73`, enlace a esta spec y revisión de un
      compañero. · Depende de: T06
