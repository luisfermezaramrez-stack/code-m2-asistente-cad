# SPEC-017 · HU-13 — Tareas del informe final

- **ID**: SPEC-017 · **Historia**: #13 · **Responsable**: los 3 integrantes
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [ ] T01 — Confirmar con la propuesta del M2 la correspondencia objetivo ↔ indicador.
      · Responsable: Luis Meza · Depende de: —
- [ ] T02 — Crear `docs/informe-final.md` con la estructura del plan y los valores de
      SPEC-016 (objetivos 1 y 2). · Responsable: Carlos Trujillo · Depende de: SPEC-016 T09
- [ ] T03 — Añadir latencia p90 de SPEC-010 (objetivo 3). · Responsable: Juan Camilo
      Pérez · Depende de: SPEC-010 T07
- [ ] T04 — Añadir autonomía de usuarios de SPEC-006 (objetivo 4). · Responsable: Luis
      Meza · Depende de: HU-11
- [ ] T05 — Estado del tablero (Done / total) con la brecha por historia y verificación
      de enlaces. · Responsable: los 3 · Depende de: T02–T04
- [ ] T06 — Enlazar el informe desde el README. · Depende de: T05
- [ ] T07 — PR hacia `develop` con `Closes #13`, enlace a esta spec y revisión cruzada.
      · Depende de: T06
- [ ] T08 — Tras promover a `main`, crear y publicar la etiqueta anotada `v1.0`. ·
      Hecho cuando: `git tag -l v1.0` la muestra en el remoto. · Depende de: T07
