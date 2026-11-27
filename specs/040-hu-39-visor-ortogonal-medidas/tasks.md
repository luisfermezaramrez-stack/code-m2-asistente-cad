# Tareas · HU-39 (SPEC-040)

Checklist completado en orden de ejecución; la evidencia está en [evidence.md](./evidence.md).

- [x] T0 · Leer #99, SPEC-040, `CONSTITUTION.md`, `AGENTS.md` y las specs vecinas; confirmar que no hay rama ni PR de HU-39; crear `feature/hu-39-visor-ortogonal-medidas` desde `origin/main` en `094fe9b` sin tocar el trabajo local de HU-28.
- [x] T1 · Ejecutar la auditoría no destructiva del estándar (0 FALTA, 21 DIFIERE) y redactar `plan.md` y `tasks.md`.
- [x] T2 · Crear `viewerMedidas.ts` con parseo de `caja_mm`, conversión de unidades, direcciones de vista, tolerancia ±2 % y nombre de PNG.
- [x] T3 · Sustituir la cámara de `GlbViewer.vue` por ortográfica, añadir las tres vistas reproducibles y conservar controles y atajos (AC1).
- [x] T4 · Mostrar cotas generales desde `caja_mm` y selector de unidades mm/pulgadas (AC3, AC4).
- [x] T5 · Capturar la vista actual como PNG con `preserveDrawingBuffer` y re-render, con error si el lienzo está vacío (AC2).
- [x] T6 · Pasar `cajaMm` desde `NewRequestView.vue` y añadir estilos con tokens del sistema de diseño.
- [x] T7 · Añadir pruebas Vitest con WebGL simulado y patrón AAA, sin red, API key ni GPU.
- [x] T8 · Actualizar `CONSTITUTION.md`, `README.md` e índice de specs; ejecutar `make check`, commitear, subir y abrir PR a `main` con `Closes #99`.
