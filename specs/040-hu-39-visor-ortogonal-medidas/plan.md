# Plan de implementación · HU-39 (SPEC-040)

- **Rama**: `feature/hu-39-visor-ortogonal-medidas`, creada desde `origin/main` en `094fe9b`.
- **Issue**: [#99](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/99).
- **Orden**: issue + spec → plan → tareas → código → pruebas → documentación → PR.
- **Estado al tomar la HU**: sin rama, sin PR y sin avance previo de HU-39 en el remoto. `spec.md` auditada en PR #82; `plan.md` y `tasks.md` se redactan aquí.
- **Auditoría del estándar**: no destructiva, 0 FALTA y 21 DIFIERE; las diferencias son personalizaciones ya declaradas en `CONSTITUTION.md`.

## Objetivo

Añadir al visor GLB tres vistas ortogonales reproducibles, cotas generales tomadas de `caja_mm` (nunca del CSV), captura PNG de la vista actual y cambio de unidades mm/pulgadas, sin perder orbitar, zoom, restablecer ni su operación por teclado.

## Decisiones de diseño

1. `frontend/src/viewerMedidas.ts` concentra la lógica pura: lectura de `caja_mm` (`40.00x30.00x5.00`), conversión mm↔pulgada (`25.4 mm`), formato a dos decimales, direcciones de las tres vistas, tolerancia relativa del ±2 % del banco y nombre del PNG. No depende de three.js, así que se prueba sin WebGL.
2. `GlbViewer.vue` sustituye `PerspectiveCamera` por `OrthographicCamera` y calcula el frustum desde la caja de la geometría y la relación de aspecto del contenedor; `aplicarVista` recoloca la cámara y reinicia `zoom`, por lo que seleccionar dos veces la misma vista da exactamente el mismo encuadre (RNF-3). La posición es `dirección × 3 × diámetro`, con direcciones canónicas +Z, +Y y +X.
3. RNF-4 se resuelve con **ambas** medidas: `WebGLRenderer({ preserveDrawingBuffer: true })` y un `render()` inmediato antes de `toDataURL('image/png')`. Si el PNG no tiene cabecera válida se muestra un error accesible en lugar de descargar un archivo vacío.
4. Las cotas se pasan como prop opcional `cajaMm` desde `NewRequestView.vue` leyendo `job.resultado.caja_mm`. No se toca el contrato OpenAPI, el SSE ni el CSV. Si no hay `caja_mm`, el visor indica que las cotas no están disponibles y no inventa medidas.
5. El selector de unidades es un `<select>` etiquetado; al cambiarlo se recalculan las tres cotas y el nombre del PNG. Se conservan los botones y atajos actuales (flechas, `+`, `−`, `Inicio`) y se añaden `1`/`2`/`3` para vistas y `U` para unidades, sin alterar `useGeneration.ts` ni `api.ts`.
6. Las pruebas usan WebGL simulado: `vi.mock` de `three` y sus addons, `fetch` y `ResizeObserver` simulados, sin red, API key ni GPU (RNF-2). La suite comprueba encuadres repetidos, PNG descargado, cotas contra `caja_mm` y conversión de unidades.
7. No se implementan cortes (SPEC-051), DXF/PDF (SPEC-043/044) ni auditoría axe (SPEC-041). FUERA DE ALCANCE: HU-40.

## Criterios de aceptación cubiertos

| AC | Evidencia prevista |
|----|--------------------|
| AC1 — Vistas reproducibles | Prueba de selección y re-selección de frontal, superior y lateral: misma posición y mismo zoom; `aria-pressed` sobre la vista activa. |
| AC2 — Vistas exportables | Prueba de descarga PNG con cabecera `data:image/png`, nombre con la vista y error visible si el lienzo está vacío. |
| AC3 — Medidas coherentes con `caja_mm` | Prueba de que el visor muestra `40.00/30.00/5.00 mm` desde `resultado.caja_mm` y helper que verifica ±2 % contra la caja simulada. |
| AC4 — Ajuste de unidades | Prueba de cambio a pulgadas: `1.57/1.18/0.20 in` en las tres cotas y nombre de archivo con `in`. |

## Riesgos y fuera de alcance

- `three` no expone una forma fácil de inspeccionar la cámara desde el DOM en un navegador real; la determinismo se verifica con la cámara simulada de Vitest, que registra cada `render`.
- El build de producción avisa del chunk de `GlbViewer`; aviso conocido de HU-38, sin cambio en esta HU.
- `make precommit` tiene un desfase preexistente del hook `ruff-format` documentado en la evidencia de HU-41; no se ejecuta sobre archivos ajenos a esta HU.
