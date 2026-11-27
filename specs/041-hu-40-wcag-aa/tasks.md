# Tareas · HU-40 (SPEC-041)

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [x] T0 · Leer SPEC-041, `CONSTITUTION.md`, `AGENTS.md`, frontend y E2E existentes;
  auditoría no destructiva de `jan-project-standard` en worktree propio (0 `FALTA`).
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Quitar el manejador que captura `Tab` en `App.vue` y hacer que el enlace de
  salto enfoque `<main tabindex="-1">` (RF-3, AC2).
- [x] T3 · Hacer `ol.steps` persistente y región viva para anunciar cada etapa nueva sin
  mover el foco (RF-4, AC3).
- [x] T4 · Añadir `axe-core@4.14.1`, el helper de auditoría y
  `e2e/accesibilidad.spec.ts` con 4 vistas × 2 temas (RF-1, RNF-1, AC1).
- [x] T5 · Añadir `e2e/teclado.spec.ts`: salto, Tab sin trampa, envío, progreso,
  descarga y foco estable ante SSE (RF-3, AC2, AC3).
- [x] T6 · Ampliar `frontend/tests/tokens.test.ts` al tema oscuro explícito y ejecutar
  axe con `color-contrast` en ambos temas (RF-5, AC4).
- [x] T7 · Actualizar `frontend/README.md`, `specs/README.md`, `CONSTITUTION.md` y
  `evidence.md`; verificar que el estándar sigue sin `FALTA`.
- [x] T8 · `npm test`, `typecheck`, `build`, `make e2e` y `make check`.
- [ ] T9 · Commit conventional, push de `feature/hu-40-wcag-aa`, PR con `Closes #100` y
  revisión solicitada; sin merge.
