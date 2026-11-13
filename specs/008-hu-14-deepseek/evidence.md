# HU-14 — Evidencia: modelo DeepSeek por API sin traducción ES→EN

- **Issue**: #37
- **Rama**: `feature/hu-14-deepseek`
- **Modelo**: `deepseek-v4-pro` (`https://api.deepseek.com`, modo JSON, sin razonamiento)
- **Fecha de la corrida**: 2026-11-13 (UTC)

## AC6 — 5 solicitudes en español (una por familia)

`make bench IDS=HU02-P01,HU02-P06,HU02-P11,HU02-P21,HU02-P26`

| Métrica | Valor |
| --- | --- |
| Pasan `/dsl/check` | 5/5 (meta ≥ 4/5) |
| Latencia media | 2,18 s |
| Tokens (entrada / salida) | 3 319 / 435 |

La única geometría marcada como incorrecta (HU02-P11, adaptador) tenía el programa y
el volumen exactos; la caja salía en 42,74 × 42,74 × 32,74 mm por un defecto previo
de HU-04, corregido en esta rama (ver abajo).

## AC7 — Banco completo (40 solicitudes)

`make bench` → `banco-deepseek-v4-pro.csv` (por caso) y `banco-deepseek-v4-pro.json` (resumen).

| Métrica | DeepSeek `deepseek-v4-pro` |
| --- | --- |
| Acierto (positivas dentro de ±2 % y negativas declinadas) | 40/40 (100 %) |
| Pasan `/dsl/check` | 40/40 (100 %) |
| Positivas construidas dentro de ±2 % | 30/30 |
| Negativas declinadas | 10/10 |
| Latencia media de extremo a extremo | 2,20 s |
| Tokens (entrada / salida) | 26 280 / 2 723 |
| Costo | Ver panel de DeepSeek; el runner lo calcula con `--precio-entrada/--precio-salida` |

**Línea base Gemma (pendiente)**: la comparación directa necesita la GPU de la línea
base heredada (`docker compose -f docker-compose.yml -f docker-compose.gemma.yml up`
y `LLM_BASE_URL=http://localhost:8080 make bench`). La única medición previa con Gemma
es el AC4 de HU-01: 5/5 programas pasan `/dsl/check`, con traducción ES→EN.

## Defecto previo corregido: caja envolvente inflada tras exportar (HU-04, AC3)

`builder.export` triangula la pieza para el GLB y la caja de OpenCascade que se medía
después sumaba el margen de la malla (+2,74 mm por eje en el adaptador por loft).
Reproducido en la base sin cambios de HU-14. `construir_pieza` ahora mide la caja antes
de exportar; prueba de regresión `adaptador-loft-caja-antes-de-teselar`.
