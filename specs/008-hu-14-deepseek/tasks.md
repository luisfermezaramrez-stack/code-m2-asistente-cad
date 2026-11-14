# SPEC-008 · HU-14 — Tareas: DeepSeek por API

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #43). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-008
- **Historia**: HU-14 · issue #37
- **Responsable**: Luis Meza
- **Rama**: `feature/hu-14-deepseek`
- **PR**: #43 (fusionado 2026-11-13)
- **Estado**: 12 de 15 tareas hechas; 3 abiertas (brechas)
- **Archivos**: [`spec.md`](./spec.md) · [`plan.md`](./plan.md) · [`evidence.md`](./evidence.md)

Los identificadores de commit son los de la rama del PR #43.

## Corrección previa (HU-04)

- [x] T01 — Medir la caja envolvente antes de exportar en `construir_pieza` · Responsable: Luis Meza · Hecho cuando: el adaptador por loft mide su caja sin el margen de malla · Evidencia: commit `a93039f`; prueba `adaptador-loft-caja-antes-de-teselar`

## Cliente LLM y retiro de la traducción (AC1–AC5) — depende de T01

- [x] T02 — DeepSeek como endpoint y modelo por defecto vía `LLM_BASE_URL`/`LLM_MODEL` · Responsable: Luis Meza · Hecho cuando: sin URL se consulta `https://api.deepseek.com` con `deepseek-v4-pro` · Evidencia: commit `25d397d`; `test_hu14_por_defecto_usa_deepseek_con_el_texto_en_espanol`
- [x] T03 — `ModeloNoDisponible` en español para clave ausente, 401/402/429, timeout y conexión · Responsable: Luis Meza · Hecho cuando: cada caso produce el mensaje sin la clave · Evidencia: `pipeline.py:96-100`, `:351-378`; `test_hu14_errores_http_de_deepseek_en_espanol_sin_la_clave`, `test_hu14_tiempo_de_espera_en_espanol`, `test_hu14_sin_api_key_de_deepseek_no_llama_al_modelo`
- [x] T04 — API responde 503 con el detalle en español · Responsable: Luis Meza · Hecho cuando: `/generar` sin modelo devuelve 503 · Evidencia: `api.py:130-133`; `test_generar_pipeline_no_disponible`, `test_hu14_con_solo_la_api_key_de_deepseek_usa_el_pipeline`
- [x] T05 — Retirar `traduccion.py`, `ErrorTraduccion`, Gemini y `test_translate.py`; quitar `traducir` de `generar_pieza` · Responsable: Luis Meza · Hecho cuando: el texto en español llega intacto al modelo · Evidencia: commit `25d397d`; `test_hu14_sin_traduccion_el_texto_en_espanol_llega_al_modelo`
- [x] T06 — `SIN_TRADUCCION = "no aplica"` en el registro · Responsable: Luis Meza · Hecho cuando: el CSV no tiene campos vacíos · Evidencia: `registro.py:43`; `tests/test_api.py:309`
- [x] T07 — Prompt de sistema con el DSL y el catálogo, aceptando español · Responsable: Luis Meza · Hecho cuando: el prompt nombra los 8 tipos y la regla de honestidad · Evidencia: `test_hu14_prompt_cubre_el_catalogo_y_acepta_espanol`
- [ ] T08 — Prueba que afirme la cabecera `Authorization: Bearer` · Responsable: Luis Meza · Hecho cuando: una prueba del repositorio la verifica · Evidencia: brecha; solo existe en `vendor/constraint-kit/constraint_kit/llm.py:63-65`

## Banco (AC6, AC7) — depende de T02

- [x] T09 — Runner `m2_cad.banco` y objetivo `make bench` con CSV por caso y resumen JSON · Responsable: Luis Meza · Hecho cuando: `make bench` deja ambos archivos · Evidencia: commit `2c37e61`; `tests/test_banco.py` (6 pruebas)
- [x] T10 — Ejecutar 5 solicitudes en español (una por familia) · Responsable: Luis Meza · Hecho cuando: ≥ 4/5 pasan `/dsl/check` · Evidencia: 5/5 en [`evidence.md`](./evidence.md)
- [x] T11 — Ejecutar el banco de 40 con DeepSeek · Responsable: Luis Meza · Hecho cuando: CSV y JSON versionados · Evidencia: [`banco-deepseek-v4-pro.csv`](./banco-deepseek-v4-pro.csv), [`banco-deepseek-v4-pro.json`](./banco-deepseek-v4-pro.json) (40/40)
- [ ] T12 — Comparar con la línea base Gemma con traducción y medir coste · Responsable: Luis Meza · Hecho cuando: hay tasa, latencia y coste de ambos modelos · Evidencia: brecha; requiere GPU y overlay `docker-compose.gemma.yml`; `costo_usd` publicado vale `0.0`

## Despliegue y documentación (AC8, AC9) — depende de T02

- [x] T13 — Gemma/llama.cpp como overlay opcional y scripts marcados `HEREDADO (HU-01)` · Responsable: Luis Meza · Hecho cuando: `make up` no requiere GPU · Evidencia: commit `71e8f8c`; `docker-compose.gemma.yml`; cabecera de `scripts/fetch-model.sh`
- [x] T14 — README y evidencia con la configuración DeepSeek · Responsable: Luis Meza · Hecho cuando: el README lista `DEEPSEEK_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` · Evidencia: commit `bc87112`; `README.md` (tabla de variables)
- [ ] T15 — Confirmar que la cobertura no baja frente a la base · Responsable: Luis Meza · Hecho cuando: se comparan coberturas antes y después · Evidencia: no verificado; el PR #43 declara no haberla medido; el CI (umbral ≥ 70 %) pasó

## Notas

- Tras el merge de `develop`, un commit alineó la documentación del proyecto con HU-14
  (`docs: align the project docs with HU-14`).
- Pendientes menores que el PR #43 declaró y que no se volvieron a verificar aquí: árbol de
  `tests/` del README sin `test_banco.py` y comentario desactualizado en
  `docker-compose.gpu-remote.yml`.
