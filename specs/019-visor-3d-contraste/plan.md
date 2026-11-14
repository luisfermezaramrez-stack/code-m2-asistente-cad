# SPEC-019 — Plan del contraste del visor 3D

- **ID**: SPEC-019 · **Tipo**: refactor · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

| Archivo | Cambio |
| --- | --- |
| `design/tokens.css` | Nuevo token `--color-viewer-background: #2f3e4f;` con un comentario de propósito |
| `frontend/src/GlbViewer.vue` | `scene.background` lee `--color-viewer-background` en vez de `--color-surface-subtle` |
| `frontend/src/style.css` | `.model-canvas` usa `var(--color-viewer-background)`, para que el contenedor coincida con el canvas mientras carga |

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Token nuevo en lugar de cambiar `--color-surface-subtle` | Ese token lo usan los botones deshabilitados y el área vacía de la vista previa; cambiarlo alteraría el resto de la interfaz. |
| Pizarra oscuro `#2f3e4f` | Contrasta con la pieza clara y sigue la paleta azul del proyecto (`--color-text` `#172b40`, `--color-accent` `#164e80`). |
| Leer el color del CSS en `GlbViewer.vue` | Mantiene una sola fuente de verdad: el diseño cambia en `tokens.css` sin tocar el componente. |

## 3. Cálculo de contraste (WCAG 2.1)

Luminancia relativa: `#2f3e4f` ≈ 0,046; `#d9d9d9` ≈ 0,694; `#f5f7fa` ≈ 0,928.

| Fondo | Contraste contra `#d9d9d9` |
| --- | --- |
| `#f5f7fa` (actual) | ≈ 1,3:1 |
| `#2f3e4f` (propuesto) | ≈ 7,7:1 |

El gris real de la pieza varía con la iluminación; `#d9d9d9` es una referencia aproximada.

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Caras en sombra muy oscuras quedan cerca del fondo | La luz hemisférica y el entorno `RoomEnvironment` mantienen las caras en grises medios; se revisa en vivo con piezas de varias familias. |
| El texto de ayuda queda sobre el fondo oscuro | El texto está fuera del contenedor del canvas; no cambia. |

## 5. Alternativas descartadas

- **Degradado o rejilla de suelo**: más código y más carga visual para el mismo objetivo.
- **Oscurecer el material de la pieza**: altera la lectura del metal y requiere tocar luces y exposición.

## 6. Estrategia de pruebas

- `make frontend-check` (Vitest, TypeScript y build): no deben cambiar las pruebas.
- Verificación visual en `http://localhost:8000` con una placa y un adaptador por loft.
- Verificación estructural: `grep` de `--color-viewer-background` en los tres archivos.
