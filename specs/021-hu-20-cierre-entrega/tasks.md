# SPEC-021 — Tareas del cierre de la entrega

- **ID**: SPEC-021 · **Historia**: HU-20 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [x] T01 — Especificar la historia (esta spec) y cargarla en el tablero. · Depende de: —
- [ ] T02 — Actualizar el objetivo 4 y el resumen de `docs/informe-final.md` (AC1). ·
      Depende de: T01
- [ ] T03 — Actualizar «Estado del tablero» y el enlace al proyecto 1 (AC2). · Depende de: T01
- [ ] T04 — Actualizar SPEC-017 (estado, HU-11 simulada, `tasks.md`) y los AC del issue
      #13 (AC3). · Depende de: T02, T03
- [ ] T05 — Actualizar `specs/README.md` con los estados reales (RF-7). · Depende de: T04
- [ ] T06 — Verificar enlaces relativos del informe (AC5) y `make check`. · Depende de: T05
- [ ] T07 — PR hacia `develop` con `Closes #72`, enlace a esta spec y revisión de un
      compañero. · Depende de: T06
- [ ] T08 — Promover `develop` a `main`, crear y publicar la etiqueta anotada `v1.0`
      (AC4). · Hecho cuando: `git ls-remote --tags origin v1.0` la muestra. · Depende de: T07
