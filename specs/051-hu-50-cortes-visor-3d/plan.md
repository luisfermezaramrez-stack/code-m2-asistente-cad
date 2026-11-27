# Plan de implementación · HU-50 (SPEC-051)

- **Rama**: `feature/hu-50-cortes-visor-3d`, creada desde `origin/main` en `042adfb`.
- **Issue**: [#110](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/110).
- **Orden**: issue + spec → plan → tareas → código → pruebas → documentación → PR.
- **Dependencia**: SPEC-040/HU-39 ya fusionada (#148, `eb99715`) en `main`; reutiliza su cámara ortográfica, vistas, cotas y captura.
- **Auditoría del estándar**: no destructiva, `OK 4 · DIFIERE 21 · FALTA 0`; sin `--force`.

## Objetivo

Añadir un plano de corte alineado a X/Y/Z en `GlbViewer.vue`, con posición ajustable, inversión y desactivación, sección cerrada en el cliente, operable por teclado y compatible con vistas/cotas/captura de SPEC-040. Sin tocar backend, contrato, SSE ni CSV.

## Decisiones de diseño

1. La nota de contexto de SPEC-051 que habla de `PerspectiveCamera` quedó obsoleta tras SPEC-040: el visor usa `OrthographicCamera` y `preserveDrawingBuffer`. Este plan respeta ese estado y no modifica la cámara.
2. `frontend/src/viewerCortes.ts` concentra la lógica pura: ejes, estado activo/posición/inversión, normal canónica, constante del plano en espacio centrado, limitación al rango de la caja y etiqueta accesible. Se prueba con Vitest sin importar `three`.
3. El estado por defecto es «corte desactivado» y eje `z`; al activarlo se usa la posición media del eje. Si no hay prop `cajaMm`, se usa la caja geométrica de `Box3` calculada al cargar el GLB (caso de `/historial`).
4. AC1 usa `Plane` de three.js: `renderer.localClippingEnabled = true` y `material.clippingPlanes = [plano]` sobre los materiales de la malla. El plano se crea una sola vez por modelo y se muta en sitio; no se recarga el GLB.
5. RF-2 se resuelve con una tapa calculada en el cliente: dos pasadas de stencil sobre la geometría (frontal/backface) marcan el interior y una malla de relleno con `stencilFunc = NotEqualStencilFunc` pinta la sección. Así los agujeros pasantes siguen visibles en la cara cortada. La tapa usa el color de acento del tema y entra en el mismo frame que `toDataURL`.
6. AC2 muta normal/constante del `Plane` y la posición/visibilidad de la tapa; cambiar `clippingPlanes` entre vacío y un plano marca `needsUpdate` una vez. Invertir deriva la normal desde el flag, sin acumular `negate()`.
7. AC3 usa botones nativos con texto visible, `role="group"` / `aria-label`, `aria-pressed`, un `<input type="range">` etiquetado con `aria-valuetext`, y un `role="status" aria-live="polite"` que anuncia eje, posición e inversión. Atajos: `C` activa/desactiva, `I` invierte, `4`/`5`/`6` eligen X/Y/Z, `]`/`[` mueven la posición. Se documentan en `#viewer-help`.
8. Las pruebas amplían el `vi.mock('three')` actual con `Plane`, `PlaneGeometry`, `Mesh`, `MeshBasicMaterial`, `Group`, caras y operaciones de stencil; el GLB simulado expone materiales. No hay red, GPU ni API key. Se comprueba plano, constantes, re-render, `fetch` único y accesibilidad.

## Criterios de aceptación cubiertos

| AC | Evidencia prevista |
|----|--------------------|
| AC1 — Corte por eje | Vitest: activar Z a media altura de la caja `40x30x5` produce normal `(0,0,1)`, constante `0`, `localClippingEnabled`, materiales con un plano y tapa visible. |
| AC2 — Ajuste y desactivación | Vitest: mover el range cambia la constante y fuerza render sin nuevo `fetch`; invertir cambia la normal; desactivar deja `clippingPlanes` vacío y la tapa oculta. |
| AC3 — Accesibilidad | Vitest: grupos y nombres accesibles, `aria-pressed`, `aria-valuetext`, anuncio en vivo y atajos de teclado sobre el contenedor del visor. |

## Riesgos y fuera de alcance

- Stencil depende del orden de render y de que `renderer.clearStencil()` se llame tras la tapa; se verifica en el mock y se documenta la comprobación visual pendiente como manual/E2E.
- `caja_mm` y la caja geométrica pueden diferir; el corte usa la geométrica para colocar el plano y `caja_mm` para las cotas y la etiqueta, sin mezclar tolerancias.
- El build avisa del chunk grande de `GlbViewer`; aviso conocido de HU-38/HU-39, sin cambio estructural.
- No se implementan cortes oblicuos, varios planos, exportación DXF/PDF ni persistencia del corte.
