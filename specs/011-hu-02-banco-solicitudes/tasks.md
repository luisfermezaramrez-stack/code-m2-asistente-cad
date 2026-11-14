# SPEC-011 · HU-02 — Tareas del banco de solicitudes

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #33). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-011
- **Historia**: HU-02 (issue #2)
- **Responsable**: Carlos Eduardo Trujillo (`cetrujillo`)
- **Rama**: `feature/hu-02-banco-solicitudes`
- **PR**: #33 (fusionado el 2026-11-12, commit `e41c250`)
- **Estado**: Implementada y fusionada; una brecha abierta (T13)
- **Documentos**: [`spec.md`](./spec.md) · [`plan.md`](./plan.md)

Todas las tareas `[x]` se verificaron sobre el commit `e41c250` y el estado actual del
repositorio. Las dependencias se indican con «Depende de».

## Contrato y datos

- [x] T01 — Definir las 6 familias del banco y la regla 5 por familia · Responsable: C. E. Trujillo · Hecho cuando: la decisión está escrita · Evidencia: `data/README.md` («Decisión de cobertura»), `src/m2_cad/dataset.py:11`
- [x] T02 — Implementar `read_dataset` con cabecera exacta y `json_object` sin claves duplicadas ni NaN/inf · Responsable: C. E. Trujillo · Depende de: T01 · Hecho cuando: una cabecera distinta o JSON inválido lanza `ValueError` · Evidencia: `test_rechaza_cabecera_incompatible`, `test_rechaza_json_incorrecto`
- [x] T03 — Implementar `validate_parameters` por tipo de motor · Responsable: C. E. Trujillo · Depende de: T02 · Hecho cuando: parámetros degenerados, booleanos o incompletos se rechazan · Evidencia: `test_rechaza_parametros_no_numericos_o_degenerados`, `test_rechaza_confusion_entre_booleanos_y_numeros`
- [x] T04 — Implementar `analytical_reference` y `compare_reference` para placa, escuadra y separador · Responsable: C. E. Trujillo · Depende de: T03 · Hecho cuando: una referencia alterada falla · Evidencia: `test_detecta_referencia_analitica_incorrecta`
- [x] T05 — Implementar `validate_row` y `validate_dataset` (40 filas, 30/10, unicidad) · Responsable: C. E. Trujillo · Depende de: T04 · Hecho cuando: el banco real valida y cada mutación falla · Evidencia: `test_banco_cumple_contrato`, `test_rechaza_numero_de_filas`, `test_rechaza_ids_duplicados`, `test_rechaza_parametros_repetidos`

## Generación y medición

- [x] T06 — Escribir las 40 especificaciones fuente (30 positivas, 10 negativas con motivo) · Responsable: C. E. Trujillo · Depende de: T01 · Hecho cuando: `specifications()` produce las 40 filas · Evidencia: `scripts/generate_hu02_dataset.py` (`NEGATIVES`, `specifications`)
- [x] T07 — Medir los positivos con el motor fijado y escribir solo con `--write` · Responsable: C. E. Trujillo · Depende de: T05, T06 · Hecho cuando: el modo por defecto no modifica el CSV · Evidencia: `scripts/generate_hu02_dataset.py:283-334`; revisión del PR #33 (sha256 del CSV sin cambios, 30/30 sólidos, 15/15 contrastes)
- [x] T08 — Generar `data/test_cases.csv` · Responsable: C. E. Trujillo · Depende de: T07 · Hecho cuando: el CSV valida con `validate_dataset` · Evidencia: `data/test_cases.csv` (40 filas + cabecera)
- [x] T09 — Añadir `scripts/verify_hu02_geometry.py` como comprobación preliminar · Responsable: C. E. Trujillo · Depende de: T07 · Hecho cuando: mide un caso por familia · Evidencia: revisión del PR #33 (5/5 familias válidas)

## Pruebas, documentación y gobierno

- [x] T10 — Escribir `tests/test_dataset.py` y prueba de aislamiento con `python -S` · Responsable: C. E. Trujillo · Depende de: T05, T08 · Hecho cuando: la suite pasa en verde · Evidencia: `102 passed` (ejecución local 2026-11-13); CI `test` en verde en el PR #33
- [x] T11 — Documentar esquema, unidades, motivos y limitaciones · Responsable: C. E. Trujillo · Depende de: T08 · Hecho cuando: `data/README.md` existe · Evidencia: `data/README.md`
- [x] T12 — Proteger `develop` (1 aprobación, check `test`, `enforce_admins`) · Responsable: propietario del repositorio (`luisfermezaramrez-stack`) · Hecho cuando: los cambios al CSV en `develop` exigen PR · Evidencia: API `branches/develop/protection`
- [ ] T13 — Imponer AC5 también en `main` (protección de rama o `CODEOWNERS` para `data/`) · Responsable: sin asignar · Hecho cuando: un push directo a `main` que toque `data/` es rechazado · Evidencia: brecha; `main` devuelve `Branch not protected`

## Seguimiento abierto (observaciones de la revisión, no AC)

- [ ] T14 — Ratificar con el responsable de la historia la exclusión de `extrusion` y `pipe` · Responsable: C. E. Trujillo · Hecho cuando: la decisión queda registrada en el issue o en una HU posterior · Evidencia: no encontrada
- [ ] T15 — Hacer `generate_hu02_dataset.py` autocontenido (`sys.path` hacia `src/`) · Responsable: sin asignar · Hecho cuando: el comando del README funciona sin `uv sync` previo · Evidencia: no implementado (el script importa `m2_cad` directamente)
