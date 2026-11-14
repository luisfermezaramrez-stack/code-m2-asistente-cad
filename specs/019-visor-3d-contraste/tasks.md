# SPEC-019 — Tareas del contraste del visor 3D

- **ID**: SPEC-019 · **Tipo**: refactor · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [ ] T01 — Añadir `--color-viewer-background` a `design/tokens.css` (AC2). · Depende de: —
- [ ] T02 — Usar el token en `scene.background` de `GlbViewer.vue` (AC2). · Depende de: T01
- [ ] T03 — Usar el token en `.model-canvas` de `style.css` (AC2, AC4). · Depende de: T01
- [ ] T04 — `make frontend-check` en verde (AC3). · Depende de: T02, T03
- [ ] T05 — Verificación visual en `localhost:8000` con una placa y un adaptador (AC1, AC4).
      · Depende de: T04
- [ ] T06 — Crear la historia en el tablero y abrir la PR hacia `develop` con `Closes #N`,
      enlace a esta spec y revisión de un compañero. · Depende de: T05
