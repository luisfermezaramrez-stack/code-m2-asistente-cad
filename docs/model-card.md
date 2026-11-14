# Model Card — Asistente CAD M2

- **Especificación**: [SPEC-018](../specs/018-model-card/spec.md)
- **Última revisión**: 2026-11-13

## 1. Resumen

El asistente convierte una solicitud en español en un **programa DSL de constraint-kit**
que el motor geométrico verifica y construye como pieza B-rep (STEP, GLB y CSV). El
modelo de lenguaje solo **propone** el programa: la aceptación de la pieza la decide la
verificación geométrica determinista (HU-04), no el modelo. Toda salida se entrega como
**diseño preliminar**.

El modelo no se entrena ni se ajusta en este proyecto: se consume como servicio
(*Model as a Service*).

## 2. Modelo base

### Modelo servido (por defecto)

| Campo | Valor |
| --- | --- |
| Modelo | `deepseek-v4-pro` (DeepSeek) |
| Acceso | API compatible con OpenAI en `https://api.deepseek.com`, con `DEEPSEEK_API_KEY` |
| Tarea | Generación de texto: solicitud en español → programa DSL en JSON |
| Parámetros de generación | `temperature=0.1`, `response_format={"type": "json_object"}` |
| Configuración | `LLM_BASE_URL`, `LLM_MODEL` (por defecto `deepseek-v4-pro`), `LLM_MODEL_VERSION` |
| Arquitectura | No publicada por el proveedor para esta versión de la API |
| Fuente en el código | `vendor/constraint-kit/constraint_kit/llm.py:16`, `src/m2_cad/pipeline.py:42` y `:365` |
| Historia | HU-14 ([SPEC-008](../specs/008-hu-14-deepseek/)) |

### Línea base heredada (Hugging Face Hub)

| Campo | Valor |
| --- | --- |
| Modelo | [`jajmangold/gemma-4-12b-constraintkit-GGUF@5c56d681c7972bcb5893e8f8ddcf90a80ebb9410`](https://huggingface.co/jajmangold/gemma-4-12b-constraintkit-GGUF) |
| Modelo base | `google/gemma-4-12B-it` |
| Archivo | `gemma4-12b-constraintkit-grpo-Q6_K.gguf` (cuantización Q6_K, ~9,8 GB) |
| Integridad | SHA-256 `42c5b8ce7d81d060e4fa4b9673786b6e507e96bd84bfde1f24dacc30ebcb7843` ([`scripts/fetch-model.sh`](../scripts/fetch-model.sh)) |
| Ajuste | GRPO sobre el DSL de constraint-kit (según el nombre del archivo publicado) |
| Servicio | llama.cpp con CUDA en `:8080`, solo con `docker-compose.gemma.yml` |
| Historia | HU-01 ([SPEC-001](../specs/001-gemma-constraintkit-serve/)) |

Los pesos nunca se versionan en Git: se descargan con `make model-fetch` y se verifican
con su SHA-256.

## 3. Dataset de origen

- **DeepSeek `deepseek-v4-pro`**: el proveedor no publica el corpus de entrenamiento de
  esta versión de la API. No se puede evaluar su representatividad para el dominio CAD.
- **Gemma ConstraintKit**: modelo base `google/gemma-4-12B-it`, ajustado para el DSL de
  constraint-kit. El dataset de ajuste no se documenta en este repositorio.
- **Evaluación propia (HU-02)**: banco versionado de **40 solicitudes en español**
  ([`data/test_cases.csv`](../data/test_cases.csv), [SPEC-011](../specs/011-hu-02-banco-solicitudes/)):
  30 dentro del catálogo (5 por familia: placa, escuadra de chapa, adaptador, brida,
  espaciador y tornillería) y 10 fuera de alcance que deben declinarse. Las solicitudes
  son sintéticas, redactadas por el equipo, sin datos personales.

## 4. Métricas

### Medidas por el equipo

Corrida del banco HU-02 con `deepseek-v4-pro` el 2026-11-13 (`make bench`). Evidencia:
[`banco-deepseek-v4-pro.csv`](../specs/008-hu-14-deepseek/banco-deepseek-v4-pro.csv),
[`banco-deepseek-v4-pro.json`](../specs/008-hu-14-deepseek/banco-deepseek-v4-pro.json) y
[`evidence.md`](../specs/008-hu-14-deepseek/evidence.md).

| Métrica | Valor | Meta del proyecto |
| --- | --- | --- |
| Acierto global (positivas dentro de ±2 % y negativas declinadas) | 40/40 (100 %) | — |
| Construcción conforme (±2 % volumen / caja) | 30/30 | ≥ 26/30 |
| Declinación correcta | 10/10 | ≥ 8/10 |
| Programas que pasan `/dsl/check` | 40/40 | — |
| Latencia media de extremo a extremo por caso | 2,20 s | — |
| Latencia p50 / p95 / máxima | 2,03 s / 2,85 s / 7,71 s | p90 ≤ 60 s |
| Throughput secuencial (derivado de la latencia media) | ≈ 27 solicitudes/min | — |
| Tokens de entrada / salida (40 casos) | 26 280 / 2 723 | — |
| Costo | No medido: la corrida no recibió `--precio-entrada` ni `--precio-salida` | — |

Acierto por familia: 5/5 en cada una de las seis familias del catálogo y 10/10 en
`fuera_alcance`. Los percentiles se calcularon por rango más cercano sobre `latencia_s`
de los 40 casos. La latencia incluye la llamada a la API, la verificación y la
construcción CAD.

### Línea base Gemma

La única medición disponible es la de HU-01: 5/5 programas pasan `/dsl/check`, con
traducción ES→EN. La comparación directa con el banco completo está **pendiente**,
porque requiere la GPU de la línea base.

### Publicadas por el proveedor

No se usan métricas publicadas por DeepSeek ni por el autor del GGUF: no miden la tarea
de este proyecto.

## 5. Limitaciones y sesgos

- **Alcance cerrado**: solo piezas únicas del catálogo (`src/m2_cad/pipeline.py:45`).
  Los ensamblajes y los tipos fuera del catálogo se declinan con motivo (HU-05). Las
  familias `extrusion` y `pipe` están en el catálogo pero no tienen casos en el banco.
- **Banco pequeño y sintético**: 40 casos redactados por el equipo, con una redacción
  homogénea y medidas explícitas. El 100 % no garantiza el mismo resultado con
  solicitudes ambiguas, coloquiales o con medidas implícitas.
- **Idioma**: evaluado solo en español técnico. Otros idiomas o variantes regionales no
  se probaron.
- **Unidades**: el banco usa milímetros. No se evaluaron pulgadas ni conversiones.
- **Falsos positivos**: el riesgo principal es una pieza construida que no es la pedida
  (*error silencioso*). La verificación determinista acota la geometría inválida, pero no
  la interpretación errónea de una solicitud válida. Lo medirá [SPEC-016](../specs/016-hu-07-corrida-banco/).
- **Falsos negativos**: declinar una pieza válida. En el banco: 0 de 30.
- **Dependencia externa**: requiere red y una API key; sin ellas el pipeline lanza
  `ModeloNoDisponible` («El modelo no está configurado: falta DEEPSEEK_API_KEY.»). La latencia y la disponibilidad dependen del proveedor.
- **No determinismo**: aun con `temperature=0.1`, dos corridas pueden producir programas
  distintos.
- **Uso no previsto**: no es una herramienta de cálculo estructural ni de certificación.
  Las piezas son preliminares y requieren revisión de un profesional antes de fabricarse.

## 6. Licencia y uso

| Componente | Licencia |
| --- | --- |
| Código del proyecto | MIT ([`LICENSE`](../LICENSE)) |
| DeepSeek `deepseek-v4-pro` | Uso por API sujeto a los términos de servicio de DeepSeek. Los pesos no se descargan; su licencia no se verificó para esta versión. |
| `jajmangold/gemma-4-12b-constraintkit-GGUF` | `apache-2.0` según la etiqueta del Hub, y sujeta a las condiciones del modelo base `google/gemma-4-12B-it` |
| constraint-kit, CadQuery, build123d, Z3 | Apache 2.0 / MIT |
| OpenCascade | LGPL 2.1 |
| python-solvespace | GPL-3.0 (obliga solo al distribuir) |

**Datos y privacidad**: las solicitudes se envían al proveedor del modelo. El registro
local y MLflow eliminan correos y nombres antes de guardar (Ley 1581 de 2012, HU-06 y
HU-16). No envíe datos personales ni información confidencial en las solicitudes.

**Atribución**: al redistribuir resultados o derivados, cite el modelo y el motor
constraint-kit según sus licencias.
