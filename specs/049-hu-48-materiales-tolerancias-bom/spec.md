# SPEC-049 · HU-48 — Materiales, tolerancias y BOM con costos

- **ID**: SPEC-049
- **Historia**: #108 (HU-48) · 5 SP · Etiquetas: Backend, spike · Hito: M4
- **Planificación**: Ola 3 (opcional) · Tamaño L · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: [SPEC-024](../024-hu-23-corpus-dorado-nucleo/spec.md)
- **Rama**: `feature/hu-48-materiales-tolerancias-bom`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

Hoy el material sólo vive en el prompt del planificador: el LLM elige entre `steel`,
`stainless`, `aluminum`, `brass`, `copper`, `abs`, `pla` y `nylon`
(`src/m2_cad/pipeline.py:68-69`). El CSV de la pieza se genera con
`bom.bom_document` (`src/m2_cad/pipeline.py:294-297`) y sólo trae tipo, cantidad y masa
(`vendor/constraint-kit/constraint_kit/bom.py:31`: `part_type,qty,total_mass_g,unit_mass_g`);
no hay costos. El BOM agrupa por `part_type`, no por material: el resumen que lo alimenta
se arma por tipo en `_resumen_materiales` (`src/m2_cad/pipeline.py:268-278`).

No hay guard de material: `DENSITY_G_MM3` admite además `iron`, `al` y `petg`, que el prompt
no ofrece, y un material desconocido cae a la densidad del acero sin diagnóstico
(`constraint_kit/builder.py:320`).

La tolerancia de ±2 % del banco (`src/m2_cad/banco.py:28`, `TOLERANCIA = 0.02`) es de
**medición** del resultado contra la referencia, no una tolerancia de fabricación.

Revisión del `constraint-kit` vendoreado (`vendor/`, restaurado con `make vendor`):

- Densidades por material: `DENSITY_G_MM3` (`constraint_kit/parts.py:18-22`).
- Resistencia por material: `MATERIAL_STRENGTH` (`constraint_kit/rules.py:49`).
- Ajustes ISO 286 (`constraint_kit/iso286.py:94,122,130`) y cadena de tolerancias
  peor caso/RSS (`constraint_kit/tolerance.py:25`).
- Propiedades de masa ponderadas por densidad: `constraint_kit/massprops.py`.
- Reglas de fabricabilidad FDM (voladizo, pared, canal, volumen):
  `constraint_kit/manufacture.py`, sin costos y sin endpoint en la API de M2. Se declaran
  para no duplicar trabajo.
- No se encontraron precios ni costos por material en el BOM.
- **El DSL no admite tolerancias por cota**: el programa es `parts{id,type,params,material}`
  más `mates` (`constraint_kit/dsl.py:10`) y `_check_part` sólo valida `id`, `type` y
  `params` (`constraint_kit/dsl.py:128-140`). Las tolerancias viven en el kit **fuera** del
  programa (`iso286.py`, `tolerance.py`, `POST /tolerance/stackup`,
  `POST /synthesize/tolerance` en `constraint_kit/api.py:431,678`).

Corresponde al ítem 31 del borrador, mantenido y ampliado con BOM con costos.

## Riesgo declarado

- **Research-first**: el alcance depende de lo que `constraint-kit` exponga. El DSL **no**
  soporta tolerancias por cota (ver contexto), así que RF-4 exige parchear el repositorio
  externo en una revisión fija (`scripts/vendor-constraint-kit.sh`): es el mayor riesgo
  del backlog, no una incógnita menor. El spike de RF-1 se cierra **antes** de comprometer
  la HU; si descarta el parche, la spec cambia de alcance (backlog §9) y se limita a
  material explícito y BOM con costos.
- No confundir la tolerancia de ±2 % de `banco.py` (medición) con tolerancias de
  fabricación.
- Toca el DSL y la verificación: exige el corpus dorado de SPEC-024 en CI antes de
  cambiar el núcleo.

## Historia de usuario

**Como** diseñador de componentes, **quiero** indicar el material y las tolerancias de la
pieza y obtener un BOM con costo estimado, **para** valorar la fabricación desde el diseño
preliminar.

## Requisitos

### Funcionales

- **RF-1**: spike documentado (medio día, Supuesto) de qué soporta `constraint-kit` en
  materiales y tolerancias, con decisión de alcance antes de implementar.
- **RF-2**: el material pedido en la descripción llega explícito al programa DSL y al BOM.
- **RF-3**: el BOM CSV agrega material, masa y costo estimado por línea y total, con
  precios por material configurables (Supuesto: tabla versionada en el repositorio).
- **RF-4**: si el spike lo confirma, la descripción admite tolerancias o ajustes ISO 286
  y la verificación las comprueba de forma determinista.
- **RF-5**: un material o tolerancia no soportado produce declinación con motivo legible.
  Requiere código nuevo: un guard que valide el material del programa contra la lista
  soportada, hoy inexistente.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU; el modelo se simula.
- **RNF-2**: el corpus dorado de SPEC-024 sigue verde tras los cambios.
- **RNF-3**: el formato actual del CSV se extiende sin romper a sus consumidores.

## Criterios de aceptación

### AC1 — Spike

- **Dado** el `constraint-kit` vendoreado
- **Cuando** se cierra el spike
- **Entonces** queda documentado qué soporta y el alcance final aprobado.

### AC2 — Material en el BOM

- **Dado** un programa DSL con una `plate` de `material: "aluminum"` de 100 × 50 × 5 mm
  (Supuesto de ejemplo; el LLM se simula)
- **Cuando** se construye la pieza
- **Entonces** el CSV tiene una columna `material` con `aluminum`, la masa con la densidad
  de `DENSITY_G_MM3["aluminum"]` y el costo estimado por línea y total.
- **Decisión para `plan.md`**: agrupar por material exige pre-agrupar en
  `_resumen_materiales` (`src/m2_cad/pipeline.py:268-278`) y escribir el CSV en M2, o
  parchear `bom.py` en el kit vendoreado. Hoy este AC falla: el CSV no tiene material.

### AC3 — Material no soportado

- **Dado** un programa DSL cuyo `material` está fuera de la lista soportada del prompt
  (`src/m2_cad/pipeline.py:68-69`), por ejemplo `"titanium"` o `"iron"` (Supuesto)
- **Cuando** se verifica el programa
- **Entonces** el sistema declina con un motivo que nombra el material, en lugar de construir
  con la densidad del acero como hoy (`constraint_kit/builder.py:320`).

### AC4 — Tolerancias (condicionado al spike)

- **Dado** una cota con ajuste ISO 286 soportado
- **Cuando** se verifica la pieza
- **Entonces** el reporte incluye la desviación aplicada y el resultado de la verificación.

## Fuera de alcance

- Cotización real con proveedores o precios en línea.
- Cambiar la tolerancia de medición del banco.
- Análisis por elementos finitos.

## Métricas de éxito

- 100 % de las piezas construidas con material y costo en el BOM.
- Corpus dorado de SPEC-024 sin regresiones.
