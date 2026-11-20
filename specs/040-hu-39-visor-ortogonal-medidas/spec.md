# SPEC-040 · HU-39 — Visor 3D: vistas ortogonales, medidas y captura

- **ID**: SPEC-040
- **Historia**: issue por crear · Ola 2 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: —
- **Rama**: `feature/hu-39-visor-ortogonal-medidas`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

El visor de la pieza usa three.js 0.187 (`frontend/package.json:15`) con `GLTFLoader` y
`OrbitControls` (`frontend/src/GlbViewer.vue:1-8`). Sólo permite orbitar, acercar,
alejar y restablecer la vista: botones en `frontend/src/GlbViewer.vue:138-144` y atajos
de teclado en `frontend/src/GlbViewer.vue:120-127`. Usa una `PerspectiveCamera`
(`GlbViewer.vue:67`); no hay `OrthographicCamera` ni captura por `toDataURL`, y el
renderer se crea sin `preserveDrawingBuffer` (`GlbViewer.vue:52`).

Las dimensiones de la pieza no están en el CSV, que es el BOM de materiales
(`constraint_kit/bom.py:31`: `part_type,qty,total_mass_g,unit_mass_g`), sino en `caja_mm`
(`src/m2_cad/pipeline.py:307`), que viaja en el `resultado` del trabajo
(`pipeline.py:169`) y en su evento SSE terminal.

Para revisar una pieza preliminar el usuario necesita vistas normalizadas, medidas
legibles y una imagen que pueda adjuntar. Los cortes de sección quedan para SPEC-051
(el borrador 27 se partió en 040 y 051).

## Historia de usuario

**Como** diseñador que revisa una pieza, **quiero** verla en vistas frontal, superior y
lateral con sus cotas básicas y capturarla como imagen, **para** comprobar sus
dimensiones sin abrir un CAD externo.

## Requisitos

### Funcionales

- **RF-1**: el visor ofrece vistas frontal, superior y lateral con proyección
  ortogonal.
- **RF-2**: muestra cotas básicas sobre aristas de la pieza.
- **RF-3**: exporta la vista actual como PNG.
- **RF-4**: permite ajustar las unidades en que se muestran las cotas (Supuesto: mm y
  pulgadas).

### No funcionales

- **RNF-1**: se conservan los controles existentes (orbitar, zoom, restablecer) y su
  operación por teclado.
- **RNF-2**: las pruebas no usan red, API key ni GPU (WebGL simulado).
- **RNF-3**: las vistas son deterministas: la misma pieza produce el mismo encuadre.
- **RNF-4**: la captura no devuelve un lienzo vacío: o el renderer se crea con
  `preserveDrawingBuffer: true`, o se re-renderiza la escena inmediatamente antes de
  `toDataURL` en la misma tarea (`GlbViewer.vue:52`). La elección queda para `plan.md`.

## Criterios de aceptación

### AC1 — Vistas reproducibles

- **Dado** una pieza cargada en el visor
- **Cuando** se selecciona la vista frontal, superior o lateral dos veces
- **Entonces** el encuadre es el mismo en ambas ocasiones.

### AC2 — Vistas exportables

- **Dado** cualquiera de las tres vistas
- **Cuando** se pide la captura
- **Entonces** se descarga un PNG de esa vista que no es un lienzo vacío (RNF-4).

### AC3 — Medidas coherentes con `caja_mm`

- **Dado** una pieza construida y su `caja_mm` (en el `resultado` del trabajo o en el
  evento SSE terminal), nunca el CSV
- **Cuando** se muestran las cotas de las tres vistas
- **Entonces** las cotas generales de ancho, fondo y alto coinciden con `caja_mm` dentro
  de la tolerancia declarada (Supuesto: ±2 %, la misma del banco en
  `src/m2_cad/banco.py:28`).

### AC4 — Ajuste de unidades

- **Dado** cotas visibles
- **Cuando** se cambia la unidad
- **Entonces** todas las cotas se recalculan en la nueva unidad.

## Fuera de alcance

- Cortes de sección (SPEC-051).
- Exportación DXF/PDF de planos (SPEC-043 y SPEC-044).
- Cotas completas de fabricación; sólo cotas básicas.

## Métricas de éxito

- Tres vistas ortogonales reproducibles y exportables.
- Diferencia entre cotas del visor y `caja_mm` dentro de tolerancia en todas las piezas de
  prueba.
