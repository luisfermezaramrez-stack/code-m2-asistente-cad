# Tareas · HU-38 (SPEC-039)

Checklist completado en orden de ejecución; la evidencia está en [evidence.md](./evidence.md).

- [x] T0 · Leer `CONSTITUTION.md`, `AGENTS.md`, `SKILL.md`, SPEC-039 y las specs vecinas; verificar `origin/main` en `a2a9dd7` y crear el worktree sin tocar HU-28.
- [x] T1 · Ejecutar la auditoría no destructiva del estándar (0 FALTA, 21 DIFIERE) y redactar `plan.md` y `tasks.md`.
- [x] T2 · Añadir `vue-router@4.6.5`, crear `router.ts`, extraer `NewRequestView.vue` y convertir `App.vue` en shell con tres vistas (AC1).
- [x] T3 · Persistir borrador y timeout en `useGeneration.ts` y recuperar tema desde `localStorage` al abrir cada URL (AC2).
- [x] T4 · Crear `VistaEstado.vue`, `estadosVista.ts` y `NotFoundView.vue`; distinguir vacío, cargando, error y ruta desconocida (AC3).
- [x] T5 · Atender `Tab`, `Shift+Tab` y `Enter` en la navegación, conservando skip link y `:focus-visible` (AC4).
- [x] T6 · Servir las tres rutas desde `web.py` con fallback SPA y preservar el 404 JSON de API y `/assets` (AC5).
- [x] T7 · Ampliar pruebas Vitest y pytest con patrón AAA, sin red, API key ni GPU.
- [x] T8 · Actualizar `CONSTITUTION.md`, `README.md` e índice de specs, ejecutar `make check` y abrir el PR a `main`.
