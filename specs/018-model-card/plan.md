# SPEC-018 — Plan de la Model Card

- **ID**: SPEC-018 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

Documento Markdown en `docs/model-card.md`, con la estructura de las Model Cards de
Hugging Face adaptada a un modelo consumido por API:

1. Resumen: qué hace el modelo dentro del sistema y qué no.
2. Modelo base: servido y línea base heredada.
3. Dataset de origen: lo publicado por cada proveedor y el banco propio de evaluación.
4. Métricas: medidas por el equipo, con evidencia.
5. Limitaciones y sesgos.
6. Licencia y uso.

## 2. Fuentes

| Dato | Fuente |
| --- | --- |
| Modelo por defecto `deepseek-v4-pro` | `vendor/constraint-kit/constraint_kit/llm.py:16` |
| Temperatura 0.1, respuesta JSON | `src/m2_cad/pipeline.py:42` y `:365` |
| Línea base `jajmangold/gemma-4-12b-constraintkit-GGUF`, base `google/gemma-4-12B-it`, licencia `apache-2.0`, revisión | API pública de Hugging Face (`/api/models/...`) y `scripts/fetch-model.sh` (SHA-256 del GGUF) |
| Métricas del banco | `specs/008-hu-14-deepseek/banco-deepseek-v4-pro.{csv,json}` |
| Catálogo de familias | `src/m2_cad/pipeline.py:45` |

## 3. Decisiones

| Decisión | Porqué |
| --- | --- |
| Documentar el modelo servido y la línea base | El backend usa DeepSeek; Gemma sigue disponible por overlay y es el modelo del Hub de la propuesta del M2. |
| Percentiles calculados del CSV por caso (rango más cercano) | El JSON solo trae la media; el CSV tiene la latencia de cada caso. |
| Declarar «no publicado» lo que DeepSeek no publica | Evita inventar datos de entrenamiento o licencia de pesos. |

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| La Model Card queda desactualizada si cambia el modelo | Se cita la fuente de cada valor; `CONSTITUTION.md` exige actualizar docs en el mismo commit. |
| 40 casos sintéticos no representan solicitudes reales | Se declara como limitación. |

## 5. Verificación

Documento pasivo: verificación estructural (5 secciones, enlaces relativos válidos) y
recálculo de las métricas desde el CSV.
