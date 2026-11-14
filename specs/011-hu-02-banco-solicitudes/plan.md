# SPEC-011 · HU-02 — Plan técnico del banco de solicitudes

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #33). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-011
- **Historia**: HU-02 (issue #2)
- **Responsable**: Carlos Eduardo Trujillo (`cetrujillo`)
- **Rama**: `feature/hu-02-banco-solicitudes`
- **PR**: #33 (fusionado el 2026-11-12, commit `e41c250`)
- **Estado**: Implementada y fusionada
- **Documentos**: [`spec.md`](./spec.md) · [`tasks.md`](./tasks.md)

## Diseño técnico

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Banco | `data/test_cases.csv` | 40 filas: 30 positivas y 10 negativas |
| Documentación | `data/README.md` | Esquema, familias, unidades, motivos y limitaciones |
| Validador | `src/m2_cad/dataset.py` | Contrato del banco con biblioteca estándar |
| Generador | `scripts/generate_hu02_dataset.py` | Especificaciones fuente y medición con el motor fijado |
| Verificación preliminar | `scripts/verify_hu02_geometry.py` | Medición de un caso por familia (`all` o familia) |
| Pruebas | `tests/test_dataset.py` | Contrato y casos de rechazo |

Flujo de generación (fuera de CI, requiere el motor CAD):

1. `specifications()` define los 40 casos fuente en el script.
2. `check_environment()` exige Python 3.12, la revisión `2ed27db` de
   `vendor/constraint-kit` y versiones exactas de `cadquery`, `build123d`, etc.
3. `measure()` construye cada positivo con `constraint_kit.parts` / `parts_bd`, exige
   un único sólido válido y mide volumen y caja con 9 decimales.
4. `validate_dataset()` corre antes de escribir; solo `--write` reemplaza el CSV. Sin
   flags (o con `--check`) compara contra el CSV guardado.

Flujo de validación (CI): `read_dataset()` → `validate_dataset()`, sin motor CAD.

## Decisiones

- **6 familias de 5 casos**: el issue no enumera las familias; se eligieron `plate`,
  `sheet_bracket`, `adapter`, `flange`, `spacer` y `tornillería`. *Porqué*: son las que
  el motor genera con parámetros explícitos y verificables; `extrusion` y `pipe` siguen
  en alcance y no se usan como negativos.
- **JSON dentro de celdas CSV**: se conservan las cinco columnas del issue y `medidas` /
  `resultado_esperado` llevan objetos JSON. *Porqué*: evita columnas por familia.
- **Referencias medidas, no estimadas**: volumen y caja salen del motor determinista sin
  LLM. *Porqué*: el banco mide al asistente contra la geometría real.
- **Contrastes analíticos independientes** para `plate`, `sheet_bracket` y `spacer`
  (`analytical_reference`). *Porqué*: detectar una referencia mal medida sin el motor.
- **Negativos sin dimensiones**: `no_aplica: true` y `motivo_esperado`. *Porqué*: no
  inventar medidas para algo que debe declinarse.
- **Validador sin dependencias**: solo biblioteca estándar. *Porqué*: corre en CI sin
  CAD ni GPU; lo prueba `test_validacion_sin_site_packages_ni_motor` con `python -S`.

## Contratos

CSV (`COLUMNS`, `src/m2_cad/dataset.py:10`):

| Columna | Positivo | Negativo |
|---|---|---|
| `id` | `HU02-P01..P30` | `HU02-N01..N10` |
| `familia` | una de `FAMILIES` | `fuera_alcance` |
| `solicitud` | texto en español, único | texto en español, único |
| `medidas` | `{"unidad":"mm","tipo_motor":…,"parametros":{…}}` | `{"unidad":"mm","no_aplica":true,"motivo_esperado":…}` |
| `resultado_esperado` | `{"volumen_mm3":…,"caja_xyz_mm":[x,y,z]}` | `declinar` |

Funciones públicas:

```python
read_dataset(path=DEFAULT_PATH) -> list[dict[str, str]]   # exige cabecera exacta
validate_row(row) -> tuple[dict, dict | None]             # ValueError con motivo
validate_dataset(rows) -> None                            # 40 filas, 30/10, 5 por familia
analytical_reference(engine_type, p) -> tuple | None
compare_reference(actual, expected) -> None               # rel_tol 1e-8
```

Consumidor posterior: `src/m2_cad/banco.py` importa `DEFAULT_PATH` y `read_dataset`.

## Riesgos

- **Familias sin cubrir**: `extrusion` y `pipe` no tienen casos; la revisión del PR
  pidió ratificarlo con el responsable de la historia.
- **Reproducibilidad del generador**: depende de versiones exactas y de `vendor/`
  (gitignored); en un checkout limpio `check_environment()` falla hasta `make vendor`.
- **Script no autocontenido**: `generate_hu02_dataset.py` importa `m2_cad` sin ajustar
  `sys.path` (observación no bloqueante de la revisión).
- **Referencias del motor**: no son auditoría normativa; tornillos sin hélice de rosca.
- **AC5 en `main`**: sin protección de rama (ver `spec.md`).

## Alternativas descartadas

- Columnas separadas por parámetro: el esquema varía por familia y rompería AC3.
- Referencias calculadas solo por fórmula: no existe fórmula exacta para `adapter`,
  `flange` ni `tornillería`.
- Regenerar el CSV dentro de las pruebas: haría que las pruebas validaran su propia salida.

## Estrategia de pruebas

- `tests/test_dataset.py`: 102 casos (parametrizados) que cubren el contrato completo y
  mutaciones de una fila: celdas vacías, número de filas, IDs, parámetros repetidos,
  reparto, JSON inválido o con claves duplicadas, unidades, booleanos, NaN/inf, caja,
  referencia analítica, negativos y cabecera.
- Aislamiento: `test_validacion_sin_site_packages_ni_motor` comprueba que el validador
  no carga el motor CAD.
- Geometría: `generate_hu02_dataset.py --check` y `verify_hu02_geometry.py` fuera de
  CI, en el entorno del motor (resultados reproducidos en la revisión del PR #33).
