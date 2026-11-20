# SPEC-044 · HU-43 — Exportación PDF de planos con cotas

- **ID**: SPEC-044
- **Historia**: issue por crear · Ola 2 · Tamaño M · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: [SPEC-043](../043-hu-42-exportacion-dxf/spec.md)
- **Rama**: `feature/hu-43-exportacion-pdf`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

No existe exportación PDF. `pypdf` aparece en `uv.lock` sólo como dependencia del extra
`service` de `constraint-kit` (`uv.lock:735`), y la descarga está limitada a STEP, GLB
y CSV (`src/m2_cad/api.py:530`).

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
- **RNF-3**: Supuesto: la descarga usa el mismo canal de artefactos que el DXF
  (SPEC-037).

## Criterios de aceptación

### AC1 — Imprimible A4/A3

- **Dado** una pieza construida
- **Cuando** se genera el PDF en A4 y en A3
- **Entonces** ambos se imprimen sin recortes y con escala legible.

### AC2 — Cajetín completo

- **Dado** el PDF de una solicitud
- **Cuando** se lee el cajetín
- **Entonces** muestra material, masa, fecha e id de solicitud.

### AC3 — Escala declarada

- **Dado** el PDF impreso a su tamaño
- **Cuando** se mide una cota con regla
- **Entonces** corresponde a la escala declarada en el cajetín.

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
