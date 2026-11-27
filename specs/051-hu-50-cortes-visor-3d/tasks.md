# Tareas · HU-50 (SPEC-051)

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [x] T0 · Verificar que #148 está fusionado en `main`, que #110 sigue abierta y asignada a
  `cetrujillo`, que no hay rama/PR previa de HU-50 y auditar el estándar sin `--force`.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de escribir código.
- [x] T2 · Crear `frontend/src/viewerCortes.ts` con estado, normal, constante, límites y
  etiqueta accesible; añadir `tests/viewerCortes.test.ts`.
- [x] T3 · Ampliar `GlbViewer.vue`: `Plane`, clipping de materiales, tapa con stencil,
  caja geométrica de reserva y `localClippingEnabled`.
- [x] T4 · Añadir controles de corte, `aria-live`, atajos de teclado y estilos.
- [x] T5 · Ampliar `tests/GlbViewer.test.ts` con AC1, AC2 y AC3 sin GPU.
- [x] T6 · Actualizar `CONSTITUTION.md`, `README.md` e índice de specs en la misma rama.
- [x] T7 · Ejecutar pruebas frontend, `make check`, pre-commit y auditoría; registrar
  `evidence.md`, abrir PR #155 con `Closes #110` y solicitar revisión.
