# SPEC-008 · HU-14 — Plan técnico: DeepSeek por API

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #43). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-008
- **Historia**: HU-14 · issue #37
- **Responsable**: Luis Meza
- **Rama**: `feature/hu-14-deepseek`
- **PR**: #43 (fusionado 2026-11-13)
- **Estado**: Implementada; AC7 parcial
- **Archivos**: [`spec.md`](./spec.md) · [`tasks.md`](./tasks.md) · [`evidence.md`](./evidence.md)

## Diseño técnico

Flujo de una solicitud tras HU-14:

1. `POST /generar` recibe el texto en español (`src/m2_cad/api.py`).
2. `pipeline.generar_pieza` llama a `planificar_con_llm` sin traducir.
3. `_respuesta_modelo` (`pipeline.py:351-378`) arma el cuerpo OpenAI con `PROMPT_SISTEMA`
   (especificación del DSL y catálogo de 8 tipos), `temperature=0.1` y
   `response_format={"type":"json_object"}`, y llama a `constraint_kit.llm.chat`.
4. `llm.chat` (vendoreado) añade `Authorization: Bearer <clave>` y adapta el cuerpo a DeepSeek.
5. El programa se verifica con el DSL y se construye la pieza (STEP, GLB, CSV) como antes.

| Componente | Archivo | Cambio |
| --- | --- | --- |
| Cliente LLM | `src/m2_cad/pipeline.py` | DeepSeek por defecto, errores HTTP en español, sin `traducir` |
| Transporte | `vendor/constraint-kit/constraint_kit/llm.py` | `DEFAULT_BASE_URL`, `DEFAULT_PLANNER_MODEL`, cabecera Bearer (sin cambios propios) |
| API | `src/m2_cad/api.py` | 503 para `ModeloNoDisponible`; detección de clave sin exigir URL |
| Registro | `src/m2_cad/registro.py` | `SIN_TRADUCCION = "no aplica"` |
| Banco | `src/m2_cad/banco.py`, `Makefile` (`bench`) | Runner HU-02 con CSV por caso y resumen JSON |
| Despliegue | `docker-compose.yml`, `docker-compose.gemma.yml` | Gemma/llama.cpp pasa a overlay opcional |
| Retirado | `src/m2_cad/traduccion.py`, `tests/test_translate.py` | Eliminados |

`src/m2_cad/control.py` no pertenece a HU-14: se creó en HU-15 (PR #46) para progreso y cancelación.

## Decisiones

- **DeepSeek sin traducción.** El modelo entiende español; quitar la traducción elimina un
  proveedor (Gemini), una etapa de latencia y una fuente de error.
- **Modelo por defecto `deepseek-v4-pro`.** Es el valor de `DEFAULT_PLANNER_MODEL` en
  constraint-kit y el que se midió en el banco. Contradice el `deepseek-chat` del AC1;
  la decisión se dejó al revisor en el PR #43, que lo aprobó sin cambio.
- **Modo JSON.** `response_format=json_object` reduce salidas con prosa;
  `extraer_programa` sigue tolerando razonamiento previo.
- **Mensajes por código HTTP.** 401, 402 y 429 tienen texto propio; otros códigos dan un
  mensaje genérico con el número. Ningún mensaje interpola la clave.
- **Gemma como overlay.** Se conserva la línea base para la comparación AC7 sin que `make up` necesite GPU.
- **Corrección de HU-04 en commit aparte** (`a93039f`): la caja envolvente se mide antes de
  exportar porque la teselación del GLB inflaba la caja (+2,74 mm por eje en el adaptador).

## Contratos

| Variable | Uso | Valor por defecto |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | Clave del proveedor; obligatoria con el endpoint de DeepSeek | — |
| `LLM_API_KEY` | Clave alternativa; tiene prioridad sobre `DEEPSEEK_API_KEY` | — |
| `LLM_BASE_URL` | Endpoint compatible con OpenAI (p. ej., llama.cpp en `:8080`) | `https://api.deepseek.com` |
| `LLM_MODEL` | Modelo planificador (`MODEL_PLANNER` lo sobrescribe) | `deepseek-v4-pro` |

- `POST /generar` con el modelo no disponible → HTTP 503, `detail` en español, tipo `ModeloNoDisponible`.
- Sin clave y endpoint de DeepSeek: `"El modelo no está configurado: falta DEEPSEEK_API_KEY."`
- `make bench [IDS=...]` → `uv run python -m m2_cad.banco [--ids ...]`; opcionales
  `--precio-entrada/--precio-salida` (USD por millón de tokens) para `costo_usd`.
- Resumen del banco: `casos`, `acierto`, `tasa_dsl_check`, `latencia_media_s`,
  `tokens_entrada`, `tokens_salida`, `costo_usd`, `modelo`.

## Riesgos

| Riesgo | Mitigación / estado |
| --- | --- |
| DeepSeek no está afinado para el DSL | Prompt con catálogo y regla de honestidad; AC6 5/5 y banco 40/40 |
| Dependencia de un proveedor externo y saldo | Errores 402/429 explícitos; overlay Gemma heredado |
| Filtración de la clave | Mensajes fijos; `.env` ignorado; pruebas con claves falsas |
| Coste no medido | `costo_usd=0.0` en la corrida publicada: no se pasaron precios |
| Comparación con Gemma pendiente | Requiere GPU; documentado como brecha de AC7 |

## Alternativas descartadas

- **Mantener Gemma en GPU alquilada**: coste y preparación de instancia que la historia busca eliminar.
- **Conservar la traducción ES→EN con DeepSeek**: redundante; añade latencia y otro proveedor.
- **Borrar los scripts de Vast.ai/GGUF**: se prefirió marcarlos como heredados para poder
  reproducir la línea base (AC8 admite ambas opciones).

## Estrategia de pruebas

- Unitarias del cliente: `llm.chat` sustituido por monkeypatch; claves falsas; sin red
  (`tests/test_pipeline.py`, pruebas `test_hu14_*` y `test_planificar_con_llm_*`).
- API: 503 y registro `no aplica` (`tests/test_api.py`).
- Banco: `evaluar_caso`, `resumir`, `main` con modelo simulado y sin clave (`tests/test_banco.py`).
- Evaluación real (con clave, fuera de CI): `make bench` y el subconjunto de 5 IDs;
  resultados en [`evidence.md`](./evidence.md).
- Hueco conocido: ninguna prueba del repositorio afirma la cabecera `Authorization`.
