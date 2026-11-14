# SPEC-008 · HU-14 — DeepSeek por API sin traducción ES→EN

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #43). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-008
- **Historia**: HU-14 · issue #37 (el issue #38 es una tarjeta duplicada)
- **Responsable**: Luis Meza
- **Rama**: `feature/hu-14-deepseek`
- **PR**: #43, fusionado en `develop` el 2026-11-13 05:32 UTC; aprobado por `JuanC0319`
- **Estado**: Implementada. AC7 parcial (falta la comparación con Gemma); ver brechas.
- **Archivos**: [`plan.md`](./plan.md) · [`tasks.md`](./tasks.md) · [`evidence.md`](./evidence.md) · [`banco-deepseek-v4-pro.csv`](./banco-deepseek-v4-pro.csv) · [`banco-deepseek-v4-pro.json`](./banco-deepseek-v4-pro.json)

## Problema y contexto

El pipeline servía Gemma 4 12B ConstraintKit (GGUF) con llama.cpp en una GPU alquilada
(Vast.ai) y traducía cada solicitud de español a inglés antes de planificar. Eso exigía
preparar la instancia, pagar GPU y mantener un segundo proveedor (Gemini) para la
traducción. DeepSeek entiende español y expone una API compatible con OpenAI, de modo
que el asistente puede ejecutarse sin GPU.

## Historia de usuario

> **Como** desarrollador del equipo, **quiero** que el pipeline use la API de DeepSeek con una API key, en lugar de servir Gemma 4 12B ConstraintKit (GGUF de Hugging Face) con llama.cpp en una GPU de Vast.ai, y sin el paso de traducción ES→EN, **para** eliminar el coste y la preparación de la instancia y ejecutar el asistente sin GPU, aprovechando que DeepSeek entiende las solicitudes en español.

Criterios originales (verbatim, `reference/HU-Luis-Fernando-Meza.md`):

- **AC1**: el cliente LLM envía `Authorization: Bearer <DEEPSEEK_API_KEY>` a un endpoint compatible con OpenAI configurable por entorno (`LLM_BASE_URL`, por defecto `https://api.deepseek.com`; `LLM_MODEL`, por defecto `deepseek-chat`).
- **AC2**: la API key se lee solo del entorno o de `.env` (ignorado por git) y no aparece en logs, respuestas ni en el registro de solicitudes.
- **AC3**: sin API key, o ante 401, 429 o timeout de DeepSeek, el pipeline lanza `ModeloNoDisponible` con un mensaje en español, y la API y la interfaz Gradio lo muestran sin romperse.
- **AC4**: el pipeline envía la solicitud en español directamente a DeepSeek; se retira la traducción ES→EN (`traduccion.py`, `ErrorTraduccion` y la dependencia de Gemini) junto con sus pruebas.
- **AC5**: el registro de HU-06 guarda "no aplica" en el campo de traducción, de modo que se mantienen 0 campos vacíos.
- **AC6**: el prompt de sistema incluye la especificación del DSL de constraint-kit; al menos 4 de 5 solicitudes de prueba en español devuelven un programa que pasa `/dsl/check`.
- **AC7**: se ejecuta el banco de 40 solicitudes (HU-02) con DeepSeek y se comparan la tasa de `/dsl/check`, la latencia y el coste frente a la línea base de Gemma con traducción.
- **AC8**: los scripts de Vast.ai y la descarga del GGUF (`scripts/cloud/*`, `scripts/fetch-model.sh`) se retiran o se marcan como opción heredada, y el README documenta la nueva configuración.
- **AC9**: las pruebas simulan la API de DeepSeek (sin red ni API key real en CI) y la cobertura no baja.

## Requisitos funcionales

- **RF-1**: El planificador llama a un endpoint compatible con OpenAI definido por `LLM_BASE_URL` (por defecto `https://api.deepseek.com`) con el modelo `LLM_MODEL`.
- **RF-2**: La clave se toma de `DEEPSEEK_API_KEY` o `LLM_API_KEY` y se envía como `Authorization: Bearer`.
- **RF-3**: Clave ausente, HTTP 401/402/429, timeout o fallo de conexión se convierten en `ModeloNoDisponible` con mensaje en español; la API responde 503.
- **RF-4**: El texto en español llega intacto al modelo; no existe etapa de traducción.
- **RF-5**: El registro de solicitudes escribe `no aplica` en la columna de traducción.
- **RF-6**: `make bench` ejecuta el banco HU-02 y deja CSV por caso y resumen JSON.

## Requisitos no funcionales

- **RNF-1**: La clave nunca aparece en mensajes de error, respuestas ni registro.
- **RNF-2**: Las pruebas no usan red ni clave real.
- **RNF-3**: La línea base Gemma/llama.cpp se conserva como opción heredada, no por defecto.

## Criterios de aceptación (Dado / Cuando / Entonces)

**AC1 — Endpoint configurable y Bearer.** *Cumplido con desviación.*
Dado `DEEPSEEK_API_KEY` definido y sin `LLM_BASE_URL`, cuando el pipeline planifica,
entonces llama a `https://api.deepseek.com` con el modelo por defecto y la cabecera Bearer.
Desviación: el modelo por defecto es `deepseek-v4-pro`, no `deepseek-chat`; se planteó al
revisor en el PR #43 y el valor medido en el banco es `deepseek-v4-pro`.
Evidencia: `test_hu14_por_defecto_usa_deepseek_con_el_texto_en_espanol` (asserta URL y
modelo); cabecera Bearer en `vendor/constraint-kit/constraint_kit/llm.py:63-65`. Ninguna
prueba del repositorio afirma la cabecera (la prueba sustituye `llm.chat`): verificado solo por lectura de código.

**AC2 — Clave solo del entorno y sin filtrarse.** *Cumplido.*
Dado un error 401/402/429 con una clave falsa, cuando el pipeline lo traduce, entonces el
mensaje no contiene la clave. Evidencia: `test_hu14_errores_http_de_deepseek_en_espanol_sin_la_clave`;
`.gitignore` cubre `.env` y `.env.*`; `test_hu14_sse_usa_espanol_y_clave_sin_url_y_registra_no_aplica`
(añadida en HU-15) revisa respuesta y registro.

**AC3 — Fallos del modelo en español.** *Cumplido; la interfaz Gradio fue reemplazada.*
Dado que falta la clave o DeepSeek responde 401/429/timeout, cuando se genera, entonces
se lanza `ModeloNoDisponible` en español y `/generar` responde 503 sin romperse.
Evidencia: `src/m2_cad/pipeline.py:96-100`, `pipeline.py:351-378`;
`test_hu14_sin_api_key_de_deepseek_no_llama_al_modelo`, `test_hu14_tiempo_de_espera_en_espanol`,
`test_generar_pipeline_no_disponible`. La parte "interfaz Gradio" se verificó en el PR #43
(`interfaz.py:31-42`), pero Gradio se retiró en HU-15 (SPEC-015): hoy la SPA Vue muestra el mensaje.

**AC4 — Sin traducción.** *Cumplido.*
Dado un texto en español, cuando se planifica, entonces el modelo recibe ese texto sin
traducir. Evidencia: `test_hu14_sin_traduccion_el_texto_en_espanol_llega_al_modelo`;
`src/m2_cad/traduccion.py` y `tests/test_translate.py` eliminados en el PR #43.

**AC5 — Registro "no aplica".** *Cumplido.*
Dada una solicitud registrada, cuando se escribe el CSV de HU-06, entonces la columna de
traducción vale `no aplica`. Evidencia: `src/m2_cad/registro.py:43` (`SIN_TRADUCCION`),
uso en `api.py`; `tests/test_api.py:309` y `:367` afirman `traduccion == "no aplica"`;
`test_generar_20_llamadas_sin_campos_vacios` afirma 0 campos vacíos.

**AC6 — Prompt con el DSL y ≥ 4/5 válidas.** *Cumplido.*
Dadas 5 solicitudes en español (una por familia), cuando se ejecuta el banco con ellas,
entonces al menos 4 pasan `/dsl/check`. Resultado: 5/5. Evidencia: [`evidence.md`](./evidence.md)
(AC6), `PROMPT_SISTEMA` en `pipeline.py:61-92`, `test_hu14_prompt_cubre_el_catalogo_y_acepta_espanol`.

**AC7 — Banco de 40 y comparación con Gemma.** *Parcial — Brecha.*
Dado el banco HU-02, cuando se ejecuta `make bench`, entonces se obtienen tasa de
`/dsl/check`, latencia y coste comparables con Gemma. DeepSeek: 40/40 acierto y
`/dsl/check`, latencia media 2,20 s, 26 280/2 723 tokens ([`banco-deepseek-v4-pro.json`](./banco-deepseek-v4-pro.json)).
La comparación con Gemma no se ejecutó (requiere GPU), y `costo_usd` quedó en `0.0`
porque la corrida no pasó precios por token: el coste no está medido.

**AC8 — Scripts heredados y README.** *Cumplido (marcados, no retirados).*
Dado el repositorio, cuando se revisan `scripts/cloud/*` y `scripts/fetch-model.sh`,
entonces llevan cabecera de opción heredada y el README documenta DeepSeek. Evidencia:
cabeceras en esos scripts, `docker-compose.gemma.yml`, `README.md` (tabla de variables).

**AC9 — Pruebas sin red y cobertura.** *Cumplido en simulación; cobertura no comparada.*
Dado CI sin clave, cuando corre la suite, entonces la API de DeepSeek está simulada.
Evidencia: `llm.chat` sustituido por monkeypatch en `tests/test_pipeline.py` y `tests/test_banco.py`;
PR #43 informa 211 pruebas en verde y el check de CI `test` pasó. El PR declara que no
midió si la cobertura bajó; el CI solo garantiza el umbral ≥ 70 %. No verificado "no baja".

## Fuera de alcance

- Afinar DeepSeek para el DSL de constraint-kit.
- Retirar físicamente la línea base Gemma; queda como overlay opcional.
- La corrección de la caja envolvente (HU-04 AC3) incluida en el PR es un defecto previo, no parte de HU-14.

## Métricas de éxito

| Métrica | Meta | Observado |
| --- | --- | --- |
| Solicitudes en español que pasan `/dsl/check` | ≥ 4/5 | 5/5 |
| Banco HU-02 con DeepSeek, acierto | — (comparar con Gemma) | 40/40 |
| Latencia media de extremo a extremo | — | 2,20 s |
| Comparación con Gemma | Requerida | Pendiente |
