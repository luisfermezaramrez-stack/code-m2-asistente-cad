# SPEC-040 · HU-39 — Visor 3D: vistas ortogonales, medidas y captura

- **ID**: SPEC-040
- **Historia**: issue por crear · Ola 2 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: —
- **Rama**: `feature/hu-39-visor-ortogonal-medidas`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

El visor de la pieza usa three.js 0.187 (`frontend/package.json:15`) con `GLTFLoader` y
`OrbitControls` (`frontend/src/GlbViewer.vue:1-8`). Sólo permite orbitar, acercar,
alejar y restablecer la vista (`frontend/src/GlbViewer.vue:124`,
`frontend/src/GlbViewer.vue:141-143`). Usa una `PerspectiveCamera`; no hay
`OrthographicCamera` ni captura por `toDataURL`.

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

## Criterios de aceptación

### AC1 — Vistas reproducibles

- **Dado** una pieza cargada en el visor
- **Cuando** se selecciona la vista frontal, superior o lateral dos veces
- **Entonces** el encuadre es el mismo en ambas ocasiones.

### AC2 — Vistas exportables

- **Dado** cualquiera de las tres vistas
- **Cuando** se pide la captura
- **Entonces** se descarga un PNG de esa vista.

### AC3 — Medidas coherentes con el CSV

- **Dado** una pieza construida y su CSV
- **Cuando** se muestran las cotas
- **Entonces** coinciden con las dimensiones del CSV dentro de la tolerancia declarada
  (Supuesto: ±2 %, la misma del banco en `src/m2_cad/banco.py:28`).

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
- Diferencia entre cotas del visor y CSV dentro de tolerancia en todas las piezas de prueba.
