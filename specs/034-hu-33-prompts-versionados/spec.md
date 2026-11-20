# SPEC-034 · HU-33 — Prompts versionados como artefactos

- **ID**: SPEC-034
- **Historia**: #93 (HU-33) · 2 SP · Etiquetas: ML · Hito: M4
- **Planificación**: Ola 1 · Tamaño M · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: —
- **Rama**: `feature/hu-33-prompts-versionados`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §4
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

El prompt es la pieza que más influye en la calidad del pipeline de HU-14
([SPEC-008](../008-hu-14-deepseek/spec.md)), y hoy no tiene identidad:

1. El catálogo de familias vive en `CATALOGO` (`src/m2_cad/pipeline.py:44-54`) y el prompt
   de sistema (formato DSL, material, parámetros por familia) es una cadena inline,
   `PROMPT_SISTEMA` (`src/m2_cad/pipeline.py:57-93`).
2. El registro guarda la versión del **modelo** (`src/m2_cad/registro.py:26,82`), pero no
   la del prompt; MLflow tampoco la recibe.
3. Cambiar el prompt no deja rastro: dos filas del registro producidas con prompts
   distintos son indistinguibles.

Esta spec habilita la edición iterativa
([SPEC-036](../036-hu-35-edicion-iterativa/spec.md)) y la comparación A/B
([SPEC-053](../053-hu-52-ab-prompts-modelos/spec.md)).

## Historia de usuario

**Como** responsable de calidad del pipeline, **quiero** que cada prompt sea un archivo
versionado con id y hash, registrado en cada solicitud, **para** atribuir cada resultado
a la versión de prompt que lo produjo.

## Requisitos

### Funcionales

- **RF-1**: los prompts se guardan como archivos versionados con id y hash de contenido.
- **RF-2**: el pipeline carga el prompt desde esos archivos, no desde una cadena inline.
- **RF-3**: cada solicitud registra la versión de prompt usada en el registro y en MLflow.
- **RF-4**: tests del prompt versionado: el pipeline carga el prompt por id, su hash coincide
  con el contenido del archivo y la versión queda en el registro.
- **RF-5**: CI falla si el contenido de un prompt cambia sin cambiar su versión.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: las respuestas del modelo se simulan.
- **RNF-2**: la migración no cambia el texto del prompt actual; su primera versión es
  idéntica a `PROMPT_SISTEMA`.
- **RNF-3**: el registro sigue sin campos vacíos (SPEC-004, AC3).

## Criterios de aceptación

### AC1 — Trazabilidad por fila

- **Dado** una solicitud procesada
- **Cuando** se consulta su fila del registro
- **Entonces** contiene el id y el hash de la versión de prompt usada, y la corrida de
  MLflow registra el mismo valor.

### AC2 — Cambio sin versión rompe CI

- **Dado** un prompt versionado
- **Cuando** se modifica su contenido sin subir su versión
- **Entonces** la verificación de CI falla.

### AC3 — Tests del prompt versionado

- **Dado** el prompt vigente guardado como archivo versionado y respuestas simuladas del
  modelo
- **Cuando** corren los tests de prompt
- **Entonces** verifican que el pipeline carga el prompt por su id, que el hash registrado
  coincide con el contenido del archivo y que la fila del registro lleva ese id y hash.

> Formato JSON, familias de `CATALOGO` y rechazo fuera de catálogo ya están cubiertos sobre
> el texto inline (`tests/test_pipeline.py:486-493` y `:631-638`); esas pruebas se
> conservan como no regresión.

## Fuera de alcance

- Mejorar o reescribir el prompt.
- Comparación A/B de prompts y modelos (SPEC-053).
- Evaluación del banco en CI ([SPEC-045](../045-hu-44-banco-ci-replay/spec.md)).

## Métricas de éxito

- 100 % de las filas nuevas del registro con versión de prompt.
- 0 cambios de prompt fusionados sin nueva versión.
