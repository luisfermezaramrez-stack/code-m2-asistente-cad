# SPEC-047 · HU-46 — Alertas de regresión de calidad

- **ID**: SPEC-047
- **Historia**: #106 (HU-46) · 2 SP · Etiquetas: ML, Testing · Hito: M4
- **Planificación**: Ola 3 (opcional) · Tamaño M · Épica: MLOps
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-045](../045-hu-44-banco-ci-replay/spec.md),
  [SPEC-027](../027-hu-26-declinacion-legible/spec.md) (RF-3 y AC3 agrupan por su etiqueta de
  causa de declinación)
- **Rama**: `feature/hu-46-alertas-regresion`
- **Estado**: Spec-first · en implementación; `plan.md`, `tasks.md` y `evidence.md` acompañan al código
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

Hoy la calidad del pipeline sólo se mide cuando alguien ejecuta el banco a mano: el banco
gasta tokens reales (`src/m2_cad/banco.py:1-12`) y el reporte de evaluación declara que
no reintenta ni ajusta nada automáticamente (`src/m2_cad/evaluacion.py:244-246`). Sí hay
un baseline histórico commiteado: los reportes de corridas reales en
`docs/hu07/banco-real-*/*/reporte.md` traen resumen por familia y causa por caso. Lo que
no existe es la **comparación automática** de una corrida contra ese baseline, de modo que
una caída de la tasa de aceptación pasa desapercibida hasta la siguiente revisión manual.

El backlog fija que esta spec necesita el baseline de SPEC-045 (corrida real registrada
en MLflow y modo replay en CI) y las etiquetas por causa de SPEC-027; sin ellos
"regresión" no es medible. Corresponde al ítem 43 del borrador, repriorizado tras 045 y
027 (`docs/backlog-v2.md` §7).

## Historia de usuario

**Como** responsable de MLOps, **quiero** recibir una alerta cuando una corrida del banco
empeora respecto del baseline, **para** detectar regresiones de calidad antes de fusionar
o publicar un cambio.

## Requisitos

### Funcionales

- **RF-1**: comparar cada corrida del banco (replay en CI o real programada) contra el
  baseline vigente registrado por SPEC-045.
- **RF-2**: declarar regresión cuando la tasa de aceptación, las declinaciones correctas o
  los errores silenciosos empeoran más allá de un umbral configurable.
- **RF-3**: desglosar la regresión por familia y por causa de declinación (etiquetas de
  SPEC-027), indicando qué casos cambiaron de resultado.
- **RF-4**: emitir la alerta en el canal acordado. Supuesto: fallo del job de CI con
  resumen en el log y, para la corrida programada, issue o comentario en GitHub.
- **RF-5**: permitir actualizar el baseline de forma explícita y trazable (nunca de forma
  implícita al pasar una corrida).

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: corridas y baseline se simulan.
- **RNF-2**: la comparación en CI no gasta tokens (usa el replay de SPEC-045).
- **RNF-3**: umbrales y baseline versionados en el repositorio o en MLflow, no en código.

## Criterios de aceptación

### AC1 — Regresión detectada

- **Dado** un baseline registrado y una corrida replay con menor tasa de aceptación que
  el umbral permitido
- **Cuando** se ejecuta la comparación en CI
- **Entonces** el job falla y el resumen lista las métricas degradadas y los casos que
  cambiaron.

### AC2 — Sin regresión

- **Dado** una corrida con métricas dentro del umbral respecto del baseline
- **Cuando** se ejecuta la comparación
- **Entonces** el job termina con código 0 y no se emite alerta.

### AC3 — Desglose por causa

- **Dado** una regresión en declinaciones
- **Cuando** se genera la alerta
- **Entonces** incluye la familia y la etiqueta de causa (SPEC-027) de cada caso afectado.

### AC4 — Baseline explícito

- **Dado** una corrida aceptada como nueva referencia
- **Cuando** se actualiza el baseline mediante el procedimiento documentado
- **Entonces** queda registrado quién, cuándo y desde qué corrida se cambió.

## Fuera de alcance

- Construir el modo replay o el baseline inicial (SPEC-045).
- Ajustar prompts o modelos automáticamente ante una alerta.
- Monitoreo de latencia o disponibilidad del servicio en producción.

## Métricas de éxito

- Toda caída de tasa de aceptación mayor que el umbral se detecta en CI sin gastar tokens.
- Cero falsos positivos por variación del replay (determinista).
