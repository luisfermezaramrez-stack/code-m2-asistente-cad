# SPEC-045 · HU-44 — Evaluación continua del banco con respuestas grabadas

- **ID**: SPEC-045
- **Historia**: issue por crear · Ola 2 · Tamaño M · Épica: MLOps
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-026](../026-hu-25-reintentos-cache-llm/spec.md),
  [SPEC-034](../034-hu-33-prompts-versionados/spec.md)
- **Rama**: `feature/hu-44-banco-ci-replay`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

1. El banco gasta tokens del modelo real en cada corrida
   (`src/m2_cad/banco.py:1-12`, "Uso (gasta tokens del modelo real)").
2. El banco no corre en CI: `.github/workflows/ci.yml` no lo invoca.
3. El reporte de evaluación declara que la herramienta "no ajusta prompts ni reintenta
   automáticamente" (`src/m2_cad/evaluacion.py:246`).

Sin una corrida reproducible y gratuita, una caída de la tasa de aceptación sólo se ve
cuando alguien ejecuta el banco a mano. La caché de respuestas de SPEC-026 y los prompts
versionados de SPEC-034 permiten grabar respuestas y reproducirlas (borrador 41,
repriorizado tras 026 y 034).

## Historia de usuario

**Como** equipo de MLOps, **quiero** evaluar el banco en CI con respuestas grabadas y
mantener una corrida real programada fuera de CI, **para** detectar regresiones de
aceptación sin gastar tokens y conservar un baseline real.

## Requisitos

### Funcionales

- **RF-1**: modo replay del banco que usa respuestas grabadas y versionadas en lugar de
  llamar al modelo.
- **RF-2**: las respuestas grabadas se apoyan en la caché de SPEC-026 y se asocian a la
  versión de prompt de SPEC-034.
- **RF-3**: corrida en CI en modo replay con un umbral de aceptación que hace fallar el
  job si no se alcanza.
- **RF-4**: corrida real programada fuera de CI que registra su resultado en MLflow
  como baseline.

### No funcionales

- **RNF-1**: el job de CI no usa red, API key ni GPU.
- **RNF-2**: no cambia el comportamiento actual de `make bench` para quien no pide
  replay.
- **RNF-3**: Supuesto: una respuesta grabada inexistente para un caso falla de forma
  explícita, no llama al modelo.

## Criterios de aceptación

### AC1 — Caída detectada sin tokens

- **Dado** un cambio que reduce la tasa de aceptación por debajo del umbral
- **Cuando** corre CI en modo replay
- **Entonces** el job falla y no se gasta ningún token.

### AC2 — Baseline real en MLflow

- **Dado** la corrida real programada fuera de CI
- **Cuando** termina
- **Entonces** queda registrada en MLflow como baseline.

### AC3 — Respuestas versionadas

- **Dado** las respuestas grabadas del banco
- **Cuando** cambia la versión de prompt
- **Entonces** las respuestas grabadas identifican la versión con la que se obtuvieron.

## Fuera de alcance

- Alertas automáticas de regresión sobre el histórico (SPEC-047).
- Comparación A/B de prompts o modelos (SPEC-053).
- Cambiar prompts o tolerancias para pasar el umbral.

## Métricas de éxito

- Tasa de aceptación en replay medida en cada PR, con costo cero en tokens.
- Un baseline real en MLflow por corrida programada.
