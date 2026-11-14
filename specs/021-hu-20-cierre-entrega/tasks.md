# SPEC-021 — Tareas de la publicación de la entrega

- **ID**: SPEC-021 · **Historia**: HU-20 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [x] T01 — Especificar la historia (esta spec) y cargarla en el tablero (#72). · Depende de: —
- [ ] T02 — Esperar la fusión de la HU-21 (#73) en `develop` con CI en verde. · Depende de: T01
- [ ] T03 — PR `develop → main` y fusión (AC1). · Depende de: T02
- [ ] T04 — Crear y publicar la etiqueta anotada `v1.0` sobre `origin/main` (AC2). ·
      Hecho cuando: `git ls-remote --tags origin v1.0` la muestra. · Depende de: T03
- [ ] T05 — Registrar `v1.0` en `docs/informe-final.md` y marcar SPEC-017 T08; PR hacia
      `develop` con `Closes #72` (AC3). · Depende de: T04
