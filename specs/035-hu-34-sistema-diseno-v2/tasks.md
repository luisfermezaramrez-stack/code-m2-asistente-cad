# Tareas · SPEC-035 / HU-34

- [x] T01 — Crear `frontend/src/design/tokens.css` con los mismos nombres de token y bloques de
  tema claro, oscuro por sistema y oscuro explícito.
- [x] T02 — Crear `frontend/src/design/theme.ts` con resolución `localStorage` → `matchMedia`,
  `data-theme`, suscripción al sistema y API de selección.
- [x] T03 — Cambiar `frontend/src/main.ts` para importar tokens desde el paquete e iniciar el tema.
- [x] T04 — Añadir el selector de tema a `frontend/src/App.vue` usando solo tokens existentes.
- [x] T05 — Mantener el fondo del visor sincronizado con el tema en `GlbViewer.vue` (RNF-3).
- [x] T06 — Añadir `frontend/tests/tokens.test.ts`: mismos nombres en ambos temas, escala,
  sin recursos remotos y contraste AA de todos los pares.
- [x] T07 — Añadir `frontend/tests/theme.test.ts`: preferencia del sistema, elección explícita
  y cambios del sistema sin preferencia guardada (AC3).
- [x] T08 — Crear `docs/diseno-v2.md` con tokens, tipografía, temas y tabla de contraste (RF-5).
- [x] T09 — Actualizar `README.md`, `frontend/README.md`, `design/README.md`,
  `design/validation.md` y `CONSTITUTION.md` en el mismo commit del cambio.
- [x] T10 — Quitar la copia de `design/tokens.css` del `Dockerfile` y el `fs.allow` externo de
  `vite.config.ts` (AC4).
- [x] T11 — Ejecutar frontend test/typecheck/build, Ruff y pytest con build compilado.
- [ ] T12 — Registrar evidencia en `specs/Evidence.md`, abrir PR y actualizar `specs/README.md`.

## Evidencia

Detalle completo en [`../Evidence.md`](../Evidence.md).
