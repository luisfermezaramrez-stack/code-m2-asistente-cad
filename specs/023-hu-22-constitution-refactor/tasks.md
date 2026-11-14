# SPEC-023 — Tareas del refactor de CONSTITUTION.md

- **ID**: SPEC-023 · **Tipo**: refactor · **Historia**: HU-22 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [x] T01 — Especificar la historia (esta spec) y cargarla en el tablero (#77). · Depende de: —
- [x] T02 — Actualizar §0 «Estado» de `CONSTITUTION.md` (AC1). · Depende de: T01
      · Evidencia: §0 «Entregada ✅ — `v1.0` en `main` (`0caa8ee`)»; HU-01 a HU-21 cerradas.
- [x] T03 — Actualizar §4 de `CONSTITUTION.md` y `AGENTS.md` con el rango de specs (AC2). ·
      Depende de: T01
      · Evidencia: §4 y `AGENTS.md` con «001–023».
- [x] T04 — Actualizar §10 de `CONSTITUTION.md` (AC3). · Depende de: T01
      · Evidencia: §10: historias cerradas y diagrama (HU-19, PR #69) marcados.
- [x] T05 — Registrar la decisión en §9 y la fila SPEC-023 en `specs/README.md` (AC4). ·
      Depende de: T02–T04
      · Evidencia: Fila 2026-11-14 en §9; fila 023 en `specs/README.md`.
- [x] T06 — Ejecutar `make check` (AC5). · Depende de: T05
      · Evidencia: `make check` 311 passed, cobertura 96,52 %.
- [x] T07 — PR hacia `develop` con `Closes #77`, enlace a esta spec y revisión de un
      compañero. · Depende de: T06
      · Evidencia: PR #78 aprobada y fusionada en `develop` (`bd28c57`); #77 cerrada.
