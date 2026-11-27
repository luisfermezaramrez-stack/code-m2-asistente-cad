# SPEC-053 · HU-52 — Comparación A/B de prompts y modelos

- **ID**: SPEC-053
- **Historia**: #112 (HU-52) · 3 SP · Etiquetas: ML · Hito: M4
- **Planificación**: Ola 3 (opcional) · Tamaño M · Épica: MLOps
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-034](../034-hu-33-prompts-versionados/spec.md),
  [SPEC-045](../045-hu-44-banco-ci-replay/spec.md)
- **Rama**: `feature/hu-52-ab-prompts-modelos`
- **Estado**: Implementado en `feature/hu-52-ab-prompts-modelos`, PR #154 en revisión; evidencia en [evidence.md](./evidence.md)
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6

## Problema y contexto

El prompt del planificador es una constante en código (`PROMPT_SISTEMA`,
`src/m2_cad/pipeline.py:61-93`) y el modelo se elige por entorno
(`src/m2_cad/pipeline.py:377`, `llm.planner_model()`). MLflow registra la versión del
modelo servido (`src/m2_cad/seguimiento.py:61-68`), pero no existe un artefacto de prompt
versionado, de modo que dos corridas no pueden atribuirse a una variante concreta de
prompt.

El ítem 42 del borrador ("Comparación en MLflow") se reformuló porque hoy no existe
artefacto de prompt: depende de SPEC-034 (prompts versionados) y de SPEC-045 (banco en
modo replay y corrida real registrada) (`docs/backlog-v2.md` §7).

## Historia de usuario

**Como** responsable de MLOps, **quiero** comparar dos variantes de prompt o de modelo
sobre el mismo banco, **para** decidir con evidencia cuál promover.

## Requisitos

### Funcionales

- **RF-1**: un comando ejecuta el banco con dos variantes (A y B), cada una identificada
  por la versión de prompt (SPEC-034) y el modelo.
- **RF-2**: cada variante queda registrada en MLflow con su versión de prompt y de modelo
  como parámetros o etiquetas, agrupadas en una comparación.
- **RF-3**: el reporte compara por familia: piezas conformes, declinaciones correctas,
  errores silenciosos, latencia, tokens y costo.
- **RF-4**: el reporte marca las diferencias por caso (casos que cambian de resultado).
- **RF-5**: la comparación real gasta tokens y se ejecuta fuera de CI; Supuesto: la
  comparación de variantes ya grabadas puede correr en replay.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU; el modelo se simula.
- **RNF-2**: ambas variantes usan el mismo banco y la misma temperatura para que la
  comparación sea justa.
- **RNF-3**: promover una variante es una decisión explícita, no automática.

## Criterios de aceptación

### AC1 — Corrida A/B

- **Dado** dos versiones de prompt registradas y una API key válida
- **Cuando** se ejecuta la comparación sobre el banco
- **Entonces** se registran dos corridas en MLflow identificadas por variante.

### AC2 — Reporte comparativo

- **Dado** una comparación terminada
- **Cuando** se abre el reporte
- **Entonces** muestra las métricas por familia de ambas variantes y los casos que
  cambiaron de resultado.

### AC3 — Trazabilidad

- **Dado** una corrida de la comparación en MLflow
- **Cuando** se inspecciona
- **Entonces** indica la versión exacta de prompt y de modelo usadas.

## Fuera de alcance

- Versionar los prompts (SPEC-034) o grabar respuestas (SPEC-045).
- Tráfico A/B en producción con usuarios reales.
- Selección automática de la variante ganadora.

## Métricas de éxito

- Diferencia de tasa de aceptación entre variantes, por familia y total.
- Costo y latencia por variante sobre el mismo banco.
