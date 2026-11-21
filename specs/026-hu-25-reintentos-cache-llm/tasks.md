# SPEC-026 — HU-25 · Tareas

## Fase 1 — Especificación
- [x] Revisar SPEC-026 y llamadas actuales al LLM.
- [x] Decidir 429 no transitorio y caché local con TTL.
- [x] Redactar `plan.md` y `tasks.md`.

## Fase 2 — Implementación
- [X] Implementar reintentos 5xx, timeout, conexión, backoff exponencial y jitter.
- [X] Implementar caché por hash de prompt, modelo y parámetros con TTL/capacidad.
- [X] Excluir secretos de la caché y evitar imputar usage duplicado.
- [X] Integrar `pipeline.py` sin tocar constraint-kit vendoreado.
- [X] Publicar métricas `llm_reintentos`, `llm_cache_hit`, `llm_cache_miss` en seguimiento.

## Fase 3 — Calidad
- [X] AC1: 503→200 con un reintento.
- [X] AC2: misma solicitud dentro del TTL sin segunda llamada pagada.
- [X] AC3: 401 y 402 sin reintentos y mensajes en español intactos.
- [X] Probar timeout, conexión, cambios de parámetros y TTL expirado.
- [X] Verificar pytest, Ruff, formato y pruebas de regresión del proyecto.
- [X] Comprobar registro de métricas y cobertura.

## Fase 4 — Entrega
- [X] Crear `evidence.md` con resultados verificables y limitaciones.
- [X] Revisar diff, commit y publicar rama.
- [X] Abrir Pull Request hacia `main` y solicitar code review a Luis.
