# SPEC-019 · HU-15 — Contraste del fondo del visor 3D

- **ID**: SPEC-019
- **Tipo**: refactor (estilo del visor; sin cambio de comportamiento)
- **Historia**: #63 (HU-18), derivada de HU-15 (#39) AC4 — Diseño
- **Responsable**: Luis Fernando Meza
- **Rama**: `refactor/visor-3d-contraste`
- **Estado**: Implementada, PR pendiente
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

> **Origen.** El problema se detectó en el ensayo de la demo del 2026-11-13 y el cambio se
> probó en local antes de redactar esta especificación. Esta spec fija el alcance y los
> criterios antes de integrar el código.

## Problema y contexto

El visor 3D (`frontend/src/GlbViewer.vue`) pinta la escena con el token
`--color-surface-subtle` (`#f5f7fa`). La pieza se renderiza en gris claro, así que pieza
y fondo casi se confunden: la silueta y las aristas se pierden, sobre todo en caras
iluminadas de frente. HU-15 AC4 exige contraste y estados legibles en la interfaz.

## Historia de usuario

**Como** diseñador CAD que revisa la pieza generada, **quiero** que el visor 3D tenga un
fondo que contraste con la pieza, **para** distinguir su forma y sus bordes sin esfuerzo.

## Requisitos

### Funcionales

- **RF-1**: un token propio `--color-viewer-background` en `design/tokens.css`, la fuente
  única de tokens de HU-15.
- **RF-2**: la escena de Three.js y el contenedor `.model-canvas` usan ese token.
- **RF-3**: el resto de la interfaz conserva sus colores; `--color-surface-subtle` no cambia.

### No funcionales

- **RNF-1**: relación de contraste ≥ 3:1 entre el fondo y el gris claro típico de la pieza
  (referencia `#d9d9d9`), el mínimo de WCAG 2.1 (1.4.11) para elementos gráficos.
- **RNF-2**: sin cambios en la carga del modelo, los controles ni la accesibilidad del visor.

## Criterios de aceptación

### AC1 — Contraste suficiente

- **Dado** una pieza generada y mostrada en el visor
- **Cuando** se compara el fondo con el gris de referencia `#d9d9d9`
- **Entonces** la relación de contraste es ≥ 3:1 (hoy es de aproximadamente 1,3:1).

### AC2 — Token único

- **Dado** `design/tokens.css`
- **Cuando** se busca el color del fondo del visor
- **Entonces** existe `--color-viewer-background` y ni `GlbViewer.vue` ni `style.css`
  fijan ese color directamente.

### AC3 — Sin regresiones

- **Dado** el cambio aplicado
- **Cuando** se ejecuta `make frontend-check`
- **Entonces** Vitest, la comprobación de TypeScript y el build pasan sin cambios en las
  pruebas existentes.

### AC4 — Resto de la interfaz intacto

- **Dado** la aplicación en `http://localhost:8000`
- **Cuando** se revisan los paneles fuera del visor
- **Entonces** conservan sus colores actuales.

## Fuera de alcance

- Cambiar materiales, luces o exposición de la escena.
- Tema oscuro para toda la aplicación.

## Métricas de éxito

- Contraste fondo/pieza de referencia ≥ 3:1 y 0 pruebas rotas.
