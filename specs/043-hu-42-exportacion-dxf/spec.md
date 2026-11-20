# SPEC-043 · HU-42 — Exportación DXF de planos 2D

- **ID**: SPEC-043
- **Historia**: issue por crear · Ola 2 · Tamaño L · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: [SPEC-024](../024-hu-23-corpus-dorado-nucleo/spec.md)
- **Rama**: `feature/hu-42-exportacion-dxf`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

El pipeline entrega sólo STEP, GLB y CSV:

1. `src/m2_cad/pipeline.py:291-305` exporta STEP y GLB con `builder.export` y escribe el
   CSV de materiales.
2. `src/m2_cad/api.py:530` limita la descarga a la allowlist `{"step", "glb", "csv"}`.
3. `ezdxf` aparece en `uv.lock` sólo como dependencia del extra `kernel` de
   `constraint-kit` (`uv.lock:724`); el paquete propio no lo usa.

Un plano 2D es el entregable habitual para fabricar una pieza auxiliar. Es el ítem más
caro del backlog: exige proyectar la pieza a vistas ortogonales y acotarla, y SPEC-037
aporta el canal de artefactos por el que se descarga.

## Historia de usuario

**Como** diseñador, **quiero** descargar un plano DXF de la pieza con sus vistas y cotas
principales, **para** llevarla a un CAD 2D o a fabricación sin redibujarla.

## Requisitos

### Funcionales

- **RF-1**: proyección de la pieza a vistas ortogonales en un DXF.
- **RF-2**: capas separadas por tipo de arista (Supuesto: visibles y ocultas).
- **RF-3**: cotas principales de la pieza en el DXF.
- **RF-4**: descarga por el canal de artefactos de SPEC-037.

### No funcionales

- **RNF-1**: la generación es determinista: el mismo programa produce el mismo DXF.
- **RNF-2**: las pruebas no usan red, API key ni GPU; el núcleo geométrico se cubre con
  el corpus dorado de SPEC-024.
- **RNF-3**: no cambia la salida STEP/GLB/CSV existente.

## Criterios de aceptación

### AC1 — Abre en un visor CAD estándar

- **Dado** una pieza construida
- **Cuando** se descarga su DXF y se abre en un visor CAD estándar
- **Entonces** el archivo abre sin errores y muestra las vistas en sus capas.

### AC2 — Cotas coherentes con la verificación

- **Dado** el DXF de una pieza del corpus dorado
- **Cuando** se comparan sus cotas con la verificación determinista
- **Entonces** coinciden dentro de la tolerancia declarada.

### AC3 — Descarga por el canal de artefactos

- **Dado** una solicitud verificada
- **Cuando** se pide el DXF
- **Entonces** se entrega por el canal de artefactos de SPEC-037.

## Riesgo declarado

Mayor incógnita técnica del backlog (§9): la proyección 2D y las cotas dependen de lo
que exponga `constraint-kit`. Antes de comprometer la historia se hace un **spike de
medio día** sobre `constraint-kit`; si no expone proyección o cotas, el alcance se
revisa antes de redactar `plan.md`.

## Fuera de alcance

- PDF del plano y cajetín (SPEC-044).
- Acotación completa de fabricación y tolerancias geométricas (SPEC-049).
- Edición del DXF en la UI.

## Métricas de éxito

- DXF abre en un visor CAD estándar para todas las piezas del corpus dorado.
- Cotas dentro de tolerancia frente a la verificación determinista.
