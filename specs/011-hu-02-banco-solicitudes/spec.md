# SPEC-011 · HU-02 — Banco versionado de 40 solicitudes

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #33). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-011
- **Historia**: HU-02 (issue #2, cerrado)
- **Responsable**: Carlos Eduardo Trujillo (`cetrujillo`)
- **Rama**: `feature/hu-02-banco-solicitudes` → `develop`
- **PR**: #33, fusionado el 2026-11-12 (commit `e41c250`); aprobado por `luisfermezaramrez-stack`
- **Estado**: Implementada y fusionada
- **Documentos**: [`plan.md`](./plan.md) · [`tasks.md`](./tasks.md)

## Problema y contexto

Sin un conjunto fijo de casos, cada medición de construcción o declinación del
asistente usaba solicitudes distintas y no era comparable entre versiones del modelo.
HU-02 entrega un banco versionado en `data/test_cases.csv` y un validador de su
contrato (`src/m2_cad/dataset.py`). El banco lo consume después el runner
`m2_cad.banco` (`src/m2_cad/banco.py:26`, `read_dataset`).

## Historia de usuario

Texto literal de `reference/HU-Carlos-Eduardo-Trujillo.md`:

> **Como** responsable de calidad, **quiero** un banco de 40 solicitudes en español en un CSV versionado (30 del catálogo y 10 fuera de él, con medidas y resultado esperado), **para** medir la construcción y la declinación siempre contra los mismos casos.
>
> - **AC1**: 40 filas, 30 del catálogo y 10 fuera.
> - **AC2**: al menos 4 casos por cada una de las 6 familias.
> - **AC3**: 0 celdas vacías en id, familia, solicitud, medidas y resultado esperado.
> - **AC4**: `test_dataset.py` valida IDs únicos, tipos y unidades.
> - **AC5**: cambios solo por pull request.

## Requisitos funcionales

- **RF-1**: `data/test_cases.csv` con las columnas `id, familia, solicitud, medidas, resultado_esperado`.
- **RF-2**: 30 filas positivas (`HU02-P01..P30`) y 10 negativas (`HU02-N01..N10`, familia `fuera_alcance`, resultado `declinar`).
- **RF-3**: cinco positivos por familia: `plate`, `sheet_bracket`, `adapter`, `flange`, `spacer`, `tornillería`.
- **RF-4**: `medidas` en JSON con `unidad: "mm"`; los positivos incluyen `tipo_motor` y `parametros`; los negativos, `no_aplica: true` y `motivo_esperado`, sin dimensiones inventadas.
- **RF-5**: `resultado_esperado` de un positivo es JSON con `volumen_mm3` y `caja_xyz_mm` medidos con el motor CAD determinista.
- **RF-6**: `validate_dataset` rechaza filas incompletas, IDs o solicitudes duplicadas, parámetros positivos repetidos, unidades distintas de mm, números no finitos o booleanos, y referencias analíticas incoherentes.
- **RF-7**: `scripts/generate_hu02_dataset.py` remide los positivos; por defecto solo compara y únicamente `--write` reescribe el CSV.

## Requisitos no funcionales

- **RNF-1**: el validador usa solo la biblioteca estándar (sin motor CAD, LLM, GPU ni red).
- **RNF-2**: las pruebas nunca regeneran ni sobrescriben las referencias del CSV.
- **RNF-3**: esquema, unidades, motivos negativos y limitaciones documentados en `data/README.md`.

## Criterios de aceptación

**AC1 — 40 filas, 30 del catálogo y 10 fuera.** Verificado.
- Dado `data/test_cases.csv`, cuando se ejecuta `validate_dataset(read_dataset())`,
  entonces hay exactamente 40 filas, 30 positivas y 10 negativas.
- Evidencia: `tests/test_dataset.py::test_banco_cumple_contrato`,
  `test_rechaza_numero_de_filas` (0, 39, 41), `test_rechaza_reparto_positivo_negativo_incorrecto`;
  `src/m2_cad/dataset.py:223` y `:243`.

**AC2 — al menos 4 casos por cada una de las 6 familias.** Verificado (con decisión de alcance).
- Dado el banco, cuando se cuentan los positivos por familia, entonces cada una de las
  6 familias elegidas tiene 5 casos.
- Evidencia: `test_reparto_y_catalogo`, `test_rechaza_distribucion_por_familia_incorrecta`;
  `src/m2_cad/dataset.py:11` y `:244`.
- Nota: el issue no enumera las 6 familias. El catálogo del producto tiene 8;
  `extrusion` y `pipe` quedan sin casos (decisión en `data/README.md`, señalada en la
  revisión del PR #33 como pendiente de ratificar).

**AC3 — 0 celdas vacías.** Verificado.
- Dada cualquier fila, cuando una de las cinco columnas está vacía, en blanco o ausente,
  entonces la validación falla.
- Evidencia: `test_rechaza_celdas_incompletas` (5 columnas × `""`, `"   "`, `None`),
  `test_fila_completa_tipos_unidades_y_referencia` (40 filas); `src/m2_cad/dataset.py:160`.

**AC4 — `test_dataset.py` valida IDs únicos, tipos y unidades.** Verificado.
- Dado `tests/test_dataset.py`, cuando se ejecuta, entonces cubre IDs duplicados, tipos
  y unidades, y pasa en verde.
- Evidencia: `test_rechaza_ids_duplicados`, `test_rechaza_unidades_incorrectas`,
  `test_rechaza_confusion_entre_booleanos_y_numeros`; ejecución local del 2026-11-13:
  `102 passed`. CI `test` en verde en el PR #33.

**AC5 — cambios solo por pull request.** Parcialmente verificado.
- Dado el CSV en `data/`, cuando alguien intenta cambiarlo en `develop`, entonces debe
  pasar por un PR con 1 aprobación y el check `test` (protección con `enforce_admins`).
- Evidencia: API de GitHub `branches/develop/protection` (consultada el 2026-11-13).
- Brecha: `main` no tiene protección de rama (`Branch not protected`), así que la regla
  no está impuesta técnicamente allí. No existe `CODEOWNERS` para `data/`.

## Fuera de alcance

- Evaluar el LLM contra el banco (HU-07); los 30 éxitos son del motor con parámetros explícitos.
- Casos de `extrusion` y `pipe`.
- Auditoría normativa de bridas ASME B16.5 y tornillos ISO 4762 (representación simplificada sin hélice).

## Métricas de éxito

| Métrica | Valor observado | Fuente |
|---|---|---|
| Pruebas del banco | 102 en verde | ejecución local 2026-11-13 |
| Sólidos B-rep válidos | 30/30 | PR #33, reproducido en la revisión |
| Contrastes analíticos | 15/15 | PR #33, reproducido en la revisión |
| Cobertura de `dataset.py` | 100 % (global 95,51 % en el PR) | PR #33 |
