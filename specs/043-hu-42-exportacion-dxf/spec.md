# SPEC-043 · HU-42 — Exportación DXF de planos 2D

- **ID**: SPEC-043
- **Historia**: #102 (HU-42) · 5 SP · Etiquetas: Backend, spike · Hito: M4
- **Planificación**: Ola 2 · Tamaño L (ver «Tamaño») · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: [SPEC-024](../024-hu-23-corpus-dorado-nucleo/spec.md),
  [SPEC-037](../037-hu-36-endurecimiento-descargas/spec.md)
- **Rama**: `feature/hu-42-exportacion-dxf`
- **Estado**: Spec-first · implementación en curso; spike corrido y veredicto en
  [`plan.md`](./plan.md) §2
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

El pipeline entrega sólo STEP, GLB y CSV:

1. `src/m2_cad/pipeline.py:291-305` exporta STEP y GLB con `builder.export` y escribe el
   CSV de materiales.
2. `src/m2_cad/api.py:530` limita la descarga a la allowlist `{"step", "glb", "csv"}`.
3. `ezdxf` ya es importable: es dependencia directa de `build123d` (`uv.lock:290-296`)
   y del extra `kernel` de `constraint-kit` (`uv.lock:724`), activo en el proyecto
   (`pyproject.toml:9`). El paquete propio todavía no lo usa.

El `constraint-kit` vendoreado ya resuelve buena parte de la geometría 2D
(`vendor/constraint-kit/constraint_kit/drawing.py`):

- `overall_dimensions` (`drawing.py:30`): dimensiones generales de la caja envolvente.
- `section_dxf` (`drawing.py:38`): corte por un plano axial exportado a DXF válido.
- `projection_svg` (`drawing.py:52`): proyecciones ortogonales con eliminación de aristas
  ocultas, en **SVG**, para seis direcciones e isométrica (`drawing.py:18-19`).
- `drawing` (`drawing.py:63`): agrupa lo anterior; el kit lo expone en
  `POST /assembly/drawing` (`constraint_kit/api.py:519-530`).

Lo que **falta** es: las vistas ortogonales dentro de un DXF (hoy son SVG), las cotas por
arista (excluidas a propósito, `drawing.py:9-11`), una capa de aristas ocultas (la
eliminación de líneas ocultas las descarta) y el armado del plano en una sola hoja.
SPEC-037 aporta el canal de artefactos por el que se descarga.

## Historia de usuario

**Como** diseñador, **quiero** descargar un plano DXF de la pieza con sus vistas y cotas
principales, **para** llevarla a un CAD 2D o a fabricación sin redibujarla.

## Requisitos

### Funcionales

- **RF-1**: vistas ortogonales de la pieza (frontal, superior y lateral) armadas en una
  sola hoja DXF, reutilizando la proyección y las dimensiones generales del kit
  (`drawing.py:30`, `drawing.py:52`).
- **RF-2**: capas separadas por tipo de arista (Supuesto: visibles y ocultas); la capa de
  ocultas es nueva, porque el kit las elimina.
- **RF-3**: cotas en el DXF: las generales (ya calculadas por el kit) y cotas por arista,
  que el kit no genera.
- **RF-4**: descarga por el canal de artefactos de SPEC-037.

### No funcionales

- **RNF-1**: la generación es determinista: el mismo programa produce el mismo DXF.
- **RNF-2**: las pruebas no usan red, API key ni GPU; el núcleo geométrico se cubre con
  el corpus dorado de SPEC-024.
- **RNF-3**: no cambia la salida STEP/GLB/CSV existente.

## Criterios de aceptación

### AC1 — Abre en un visor CAD estándar

- **Dado** una pieza construida
- **Cuando** se descarga su DXF y se lee con `ezdxf` y su auditoría
- **Entonces** no hay errores, y el documento contiene las tres vistas y las capas de
  aristas visibles y ocultas. La apertura en un visor CAD estándar es verificación
  manual complementaria.

### AC2 — Cotas coherentes con la verificación

- **Dado** el DXF de una pieza del corpus dorado
- **Cuando** se comparan sus cotas con la verificación determinista
- **Entonces** las cotas generales coinciden con `caja_mm` (`src/m2_cad/pipeline.py:307`)
  y las cotas por arista con la geometría de la pieza, dentro de la tolerancia declarada.

### AC3 — Descarga por el canal de artefactos

- **Dado** una solicitud verificada
- **Cuando** se pide el DXF
- **Entonces** se entrega por el canal de artefactos de SPEC-037.

## Tamaño

Se mantiene **L** porque el alcance incluye cotas por arista y capas por tipo de arista,
que el kit no ofrece. Si la HU se limitara a llevar a DXF las vistas ortogonales que el kit
ya proyecta, sería **M**.

## Riesgo declarado

La auditoría resolvió la incógnita de §9: el kit expone sección DXF, proyección SVG y
dimensiones generales, pero no cotas por arista ni aristas ocultas. El **spike de medio
día** se acota a dos preguntas antes de `plan.md`: cómo llevar la proyección a entidades
DXF y cómo recuperar las aristas ocultas. Supuesto: el objeto que construye
`src/m2_cad/pipeline.py` puede pasarse a las funciones de `drawing.py`, que esperan
objetos de cadquery (`drawing.py:22-27`).

## Fuera de alcance

- PDF del plano y cajetín (SPEC-044).
- Acotación completa de fabricación y tolerancias geométricas (SPEC-049).
- Edición del DXF en la UI.

## Métricas de éxito

- DXF abre en un visor CAD estándar para todas las piezas del corpus dorado.
- Cotas dentro de tolerancia frente a la verificación determinista.
