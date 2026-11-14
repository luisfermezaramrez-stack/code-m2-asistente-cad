# SPEC-018 — Model Card del modelo servido

- **ID**: SPEC-018
- **Historia**: #59 (HU-17)
- **Responsable**: Luis Fernando Meza
- **Rama**: `docs/model-card`
- **Estado**: Implementada, PR pendiente
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

El backend genera programas DSL con `deepseek-v4-pro` por API (HU-14) y conserva
Gemma 4 12B ConstraintKit como línea base heredada (HU-01), pero el repositorio no tiene
un documento que declare qué modelo se usa, de dónde sale, qué tan bien funciona, dónde
falla y con qué licencia. La rúbrica del M3 lo exige en `docs/model-card.md`, enlazado
desde el README y consistente con el modelo que carga el backend.

## Historia de usuario

**Como** evaluador del proyecto, **quiero** una Model Card del modelo que usa el backend,
**para** conocer su origen, sus métricas medidas, sus limitaciones y su licencia sin
leer el código.

## Requisitos

### Funcionales

- **RF-1**: `docs/model-card.md` con las secciones: modelo base, dataset de origen,
  métricas, limitaciones y sesgos, licencia y uso.
- **RF-2**: identifica el modelo servido (`deepseek-v4-pro`, endpoint y parámetros de
  generación) y la línea base heredada como `org/modelo@rev`.
- **RF-3**: las métricas medidas por el equipo citan su evidencia versionada.
- **RF-4**: el README enlaza la Model Card.

### No funcionales

- **RNF-1**: ningún dato sin fuente; lo que no publica el proveedor se declara «no publicado».
- **RNF-2**: los valores coinciden con el código (`src/m2_cad/pipeline.py`,
  `vendor/constraint-kit/constraint_kit/llm.py`) y con `CONSTITUTION.md`.

## Criterios de aceptación

### AC1 — Secciones completas

- **Dado** el archivo `docs/model-card.md`
- **Cuando** se revisa su estructura
- **Entonces** contiene modelo base, dataset de origen, métricas, limitaciones y sesgos,
  y licencia y uso.

### AC2 — Modelo consistente con el backend

- **Dado** el código del backend
- **Cuando** se compara con la Model Card
- **Entonces** el modelo por defecto, el endpoint, la temperatura y el formato de
  respuesta coinciden, y la línea base figura como `jajmangold/gemma-4-12b-constraintkit-GGUF@<rev>`.

### AC3 — Métricas con evidencia

- **Dado** la corrida del banco de HU-14
- **Cuando** se leen las métricas de la Model Card
- **Entonces** acierto, `/dsl/check`, latencia media, p50 y p95 y tokens coinciden con
  `specs/008-hu-14-deepseek/banco-deepseek-v4-pro.csv` y su JSON.

### AC4 — Enlace

- **Dado** el README
- **Cuando** se busca la Model Card
- **Entonces** hay un enlace a `docs/model-card.md`.

## Fuera de alcance

- Nuevas mediciones o corridas del banco (las cubren SPEC-016 y HU-16).
- Evaluación de sesgos con usuarios (la cubre HU-11).

## Métricas de éxito

- 5/5 secciones presentes y 0 valores sin fuente.
