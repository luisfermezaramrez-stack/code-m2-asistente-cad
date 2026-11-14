# SPEC-020 — Tareas del diagrama de arquitectura

- **ID**: SPEC-020 · **Tipo**: refactor · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [ ] T01 — Reescribir `docs/arquitectura.json` con los componentes del plan y sus citas
      de código (AC1). · Depende de: —
- [ ] T02 — Fijar `meta.repository.revision` en el commit de esta spec. · Depende de: T01
- [ ] T03 — `archify validate --quality showcase --repo-root .` sin hallazgos (AC2). · Depende de: T02
- [ ] T04 — `archify deliver` para regenerar `docs/arquitectura.html` y el recibo (AC3). · Depende de: T03
- [ ] T05 — README: enlazar el tablero y retirar el aviso «Pendiente (HU-14)» (AC4). · Depende de: —
- [ ] T06 — Crear la historia en el tablero y abrir la PR hacia `develop` con `Closes #N`,
      enlace a esta spec y revisión de un compañero. · Depende de: T04, T05
