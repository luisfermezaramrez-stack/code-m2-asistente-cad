# SPEC-051 · HU-50 — Cortes y secciones en el visor 3D

- **ID**: SPEC-051
- **Historia**: #110 (HU-50) · 4 SP · Etiquetas: Frontend · Hito: M4
- **Planificación**: Ola 3 (opcional) · Tamaño L · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-040](../040-hu-39-visor-ortogonal-medidas/spec.md)
- **Rama**: `feature/hu-50-cortes-visor-3d`
- **Estado**: Spec-first · implementada en la rama de la HU; `plan.md`, `tasks.md` y `evidence.md` documentan la entrega
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

El visor 3D (`frontend/src/GlbViewer.vue`) carga el GLB con `GLTFLoader` y permite orbitar
con `OrbitControls` sobre una cámara ortográfica desde SPEC-040. No permite ver el interior
de la pieza: agujeros pasantes, espesores de pared o resaltes sólo se aprecian desde fuera.

El ítem 27 del borrador ("Visor 3D") se partió en dos: vistas ortogonales, medidas y
captura (SPEC-040) y cortes (esta spec), que reutiliza las vistas y la herramienta de
medida de SPEC-040 (`docs/backlog-v2.md` §7).

## Historia de usuario

**Como** diseñador de componentes, **quiero** cortar la pieza con un plano y ver su
sección, **para** revisar espesores y geometría interna sin abrir otra herramienta CAD.

## Requisitos

### Funcionales

- **RF-1**: plano de corte alineado a X, Y o Z, con posición ajustable a lo largo del eje.
- **RF-2**: la sección cortada se muestra cerrada (relleno de la cara de corte), no como
  una malla hueca. Supuesto: técnica de stencil o tapa calculada en el cliente.
- **RF-3**: invertir el lado visible del corte y desactivarlo para volver a la vista
  completa.
- **RF-4**: el corte se combina con las vistas ortogonales y la medida de SPEC-040.
- **RF-5**: los controles del corte son operables con teclado y tienen nombre accesible
  (criterio de SPEC-041).

### No funcionales

- **RNF-1**: el corte se calcula en el cliente sobre el GLB entregado; no requiere
  cambios en el backend.
- **RNF-2**: interacción fluida en piezas del banco. Supuesto: ≥ 30 fps en un portátil
  de referencia.
- **RNF-3**: pruebas unitarias con Vitest sin GPU; la verificación visual se cubre con
  E2E de SPEC-042.

## Criterios de aceptación

### AC1 — Corte por eje

- **Dado** una placa con agujeros pasantes cargada en el visor
- **Cuando** se activa un corte en Z a media altura
- **Entonces** (Vitest, sin GPU) el visor expone un plano de corte activo de eje Z cuya
  posición es la mitad de la altura de la caja de la pieza, y el material de la pieza
  recorta con ese plano; hoy falla porque el visor no tiene corte.
- **Verificación manual** (o captura E2E de SPEC-042): se ven la sección rellena y los
  agujeros atravesándola.

### AC2 — Ajuste y desactivación

- **Dado** un corte activo
- **Cuando** se mueve su posición o se desactiva
- **Entonces** la vista se actualiza sin recargar el modelo y al desactivar vuelve a la
  pieza completa.

### AC3 — Accesibilidad

- **Dado** el visor con foco en los controles de corte
- **Cuando** se opera sólo con teclado
- **Entonces** se puede elegir eje, mover el plano e invertir el corte.

## Fuera de alcance

- Vistas ortogonales, medidas y captura (SPEC-040).
- Varios planos simultáneos o cortes oblicuos.
- Exportar la sección a DXF o PDF (SPEC-043, SPEC-044).

## Métricas de éxito

- Todas las familias del banco se pueden inspeccionar con corte en los tres ejes.
- Sin caída perceptible de fluidez respecto del visor sin corte.
