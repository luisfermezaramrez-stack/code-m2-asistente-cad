# SPEC-026 — HU-25 · Tareas

## Fase 1 — Especificación
- [x] Revisar SPEC-026 y llamadas actuales al LLM.
- [x] Decidir 429 no transitorio y caché local con TTL.
- [x] Redactar `plan.md` y `tasks.md`.

## Fase 2 — Implementación
- [x] Implementar reintentos 500/502/503/504, timeout y conexión, con backoff exponencial y jitter.
- [x] Aplicar un plazo total compartido por todos los intentos (el timeout no se multiplica).
- [x] Implementar caché por hash de endpoint, prompt, modelo, parámetros y huella de credencial.
- [x] Excluir secretos de la caché y evitar imputar usage duplicado.
- [x] Cachear sólo respuestas cuyo programa se extrae correctamente.
- [x] Integrar `pipeline.py` sin tocar constraint-kit vendoreado.
- [x] Publicar métricas `llm_reintentos`, `llm_cache_hit`, `llm_cache_miss` en seguimiento.
- [x] Propagar la cancelación SSE hasta el bucle de reintentos.
- [x] Traducir configuración inválida a `ModeloNoDisponible` (503).

## Fase 3 — Calidad
- [x] AC1: 503→200 con un reintento.
- [x] AC2: misma solicitud dentro del TTL sin segunda llamada pagada.
- [x] AC3: 401 y 402 sin reintentos y mensajes en español intactos.
- [x] Probar timeout, conexión, cambios de parámetros y TTL expirado.
- [x] AC4: cancelación antes y durante el backoff sin llamadas pagas adicionales.
- [x] AC5: configuración inválida informada como 503, no como 500.
- [x] AC6: respuesta inválida no almacenada en caché.
- [x] Verificar pytest, Ruff, formato y pruebas de regresión del proyecto.
- [x] Comprobar registro de métricas y cobertura (96,11 % total; 92 % en `llm_resiliente.py`).

## Fase 4 — Entrega
- [x] Crear `evidence.md` con resultados verificables y limitaciones.
- [x] Revisar diff, commit y publicar rama.
- [x] Abrir Pull Request hacia `main` y solicitar code review a Luis.

## Fase 5 — Correcciones de la revisión (PR #126)
- [x] Revisión 1: plazo total en lugar de timeout por intento; mensaje actualizado.
- [x] Revisión 2: caché sólo tras validar la extracción del programa.
- [x] Revisión 3: cancelación cooperativa dentro del bucle de reintentos.
- [x] Revisión 4: configuración inválida → `ModeloNoDisponible` (503).
- [x] Revisión 5: en error sólo se registran métricas `llm_*` (sin tokens/costo en 0).
- [x] Revisión 6: reintentar sólo 500, 502, 503 y 504.
- [x] Revisión 7: huella de credencial en la clave de caché.
- [x] Revisión 8: `spec.md`, `plan.md`, `tasks.md` y `evidence.md` consistentes (todos los
  4xx y 501/505 sin reintento; regresión y métricas verificadas).

## Pendiente fuera de esta rama
- [ ] Validar la ejecución integral en Docker (`make up` + generación real).
- [ ] Verificar las métricas en una ejecución real con servidor MLflow (no sólo file store).
