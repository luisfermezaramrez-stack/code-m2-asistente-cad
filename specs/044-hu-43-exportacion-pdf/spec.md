# SPEC-044 · HU-43 — Exportación PDF de planos con cotas

- **ID**: SPEC-044
- **Historia**: #103 (HU-43) · 3 SP · Etiquetas: Backend · Hito: M4
- **Planificación**: Ola 2 · Tamaño M · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: [SPEC-043](../043-hu-42-exportacion-dxf/spec.md),
  [SPEC-037](../037-hu-36-endurecimiento-descargas/spec.md)
- **Rama**: `feature/hu-43-exportacion-pdf`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

No existe exportación PDF. `pypdf` aparece en `uv.lock` sólo como dependencia del extra
`service` de `constraint-kit` (`uv.lock:735`), y el kit lo usa para **extraer** texto de
PDF (`constraint_kit/spec_extract.py:117-126`), no para dibujar. Ni el kit ni el paquete
propio tienen un escritor de PDF vectorial, y la descarga está limitada a STEP, GLB y CSV
(`src/m2_cad/api.py:530`).

Hace falta, por tanto, una dependencia de generación de PDF vectorial: una nueva, o
promover a directa una transitiva ya presente (por ejemplo `matplotlib`, que llega por
`vtk`, `uv.lock:4423-4427`). `plan.md` evalúa su licencia y su peso en la imagen.

Un plano imprimible con cajetín es lo que se revisa en una reunión o se adjunta a una
orden de fabricación. Esta spec reutiliza las vistas y cotas que produce SPEC-043 (el
borrador 32 se partió en dos specs por costo real).

## Historia de usuario

**Como** diseñador, **quiero** un PDF del plano con vistas, cotas y cajetín, **para**
imprimirlo o adjuntarlo sin pasar por un CAD.

## Requisitos

### Funcionales

- **RF-1**: el PDF contiene las vistas acotadas de SPEC-043.
- **RF-2**: incluye un cajetín con material, masa, fecha e id de solicitud.
- **RF-3**: declara la escala del plano.
- **RF-4**: formato imprimible A4 y A3.

### No funcionales

- **RNF-1**: la generación es determinista salvo la fecha del cajetín.
- **RNF-2**: las pruebas no usan red, API key ni GPU.
- **RNF-3**: la descarga usa el mismo canal de artefactos que el DXF (SPEC-037).
- **RNF-4**: la dependencia de generación de PDF se declara en `pyproject.toml` con su
  licencia y su impacto en el tamaño de la imagen documentados.

## Criterios de aceptación

### AC1 — Página A4/A3 sin recortes

- **Dado** una pieza construida
- **Cuando** se genera el PDF en A4 y en A3
- **Entonces** el tamaño de página de cada uno es A4 (210 × 297 mm) o A3 (297 × 420 mm) y
  la caja envolvente de su contenido queda dentro de la página menos el margen
  (Supuesto: margen de 10 mm).

La impresión física sin recortes es **verificación manual**, fuera de CI.

### AC2 — Cajetín completo

- **Dado** el PDF de una solicitud
- **Cuando** se lee el cajetín
- **Entonces** muestra material, masa, fecha e id de solicitud.

### AC3 — Escala declarada

- **Dado** el PDF de una pieza del corpus dorado
- **Cuando** se mide en unidades de página la longitud dibujada de una cota general y se
  compara con su valor en `caja_mm`
- **Entonces** la relación coincide con la escala declarada en el cajetín dentro de la
  tolerancia declarada.

La medición con regla sobre el plano impreso es **verificación manual**, fuera de CI.

## Riesgo declarado

Comparte la mayor incógnita técnica del backlog con SPEC-043 (§9): depende de la
proyección 2D y las cotas que exponga `constraint-kit`. El **spike de medio día** sobre
`constraint-kit` se hace antes de comprometer 043 y 044; si 043 cambia de alcance, esta
spec se revisa antes de redactar `plan.md`.

## Fuera de alcance

- Generación de las vistas y cotas (SPEC-043).
- Tolerancias de fabricación y BOM con costos (SPEC-049).
- Plantillas de cajetín personalizables.

## Métricas de éxito

- PDF imprimible en A4 y A3 para todas las piezas del corpus dorado.
- Cajetín completo en el 100 % de los PDF generados.
