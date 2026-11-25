# HU-24 — Seguimiento de tareas

## Fase 1 — Análisis y planificación
- [x] Revisar SPEC-025 y los criterios AC1–AC3, RF-1–RF-5 y RNF-1–RNF-3.
- [x] Localizar los loggers sueltos en `trabajos.py`, `seguimiento.py` y `api.py`.
- [x] Definir el formato JSON y las claves obligatorias.
- [x] Decidir la propagación de `request_id`/`job_id` con `contextvars` y `copy_context`.
- [x] Redactar `plan.md`.

## Fase 2 — Implementación
- [x] Crear `src/m2_cad/observabilidad.py` con `configurar_logging`, `JsonFormatter`,
  `ContextoFilter`, `contexto_solicitud` y `redactar`.
- [x] Redactar claves API, tokens Bearer, cabeceras `Authorization`, valores sensibles y PII.
- [x] Configurar el logger `m2_cad` vía `dictConfig` con nivel desde `M2_LOG_LEVEL`.
- [x] Fijar `request_id` en `POST /generar` (RF-5) y conservarlo en las rutas SSE y JSON.
- [x] Copiar el contexto al hilo del trabajo SSE y añadir `job_id`.
- [x] Emitir eventos de entrada, etapas y resultado en `api.py` y `pipeline.py`.
- [x] Registrar el motivo de error del proveedor ya redactado en `pipeline.py`.
- [x] Emitir el evento de cierre del seguimiento desde `medir_solicitud()` en `api.py`.
- [x] Añadir `request_id`/`job_id` como etiquetas de MLflow.
- [x] Documentar `M2_LOG_LEVEL` en README y `.env.example`.

## Fase 3 — Pruebas automatizadas
- [x] AC1: reconstrucción por `request_id` con eventos ordenados y etiqueta en MLflow.
- [x] AC2: cada línea es JSON válido con las claves obligatorias.
- [x] AC3: error del proveedor con `Authorization` no filtra la clave.
- [x] RF-5: `X-Request-ID` válido reutilizado; inválido o ausente se regenera.
- [x] RF-2: contexto del hilo SSE con `request_id` y `job_id`.
- [x] RNF-3: nivel configurable por `M2_LOG_LEVEL`, con valor inválido seguro.
- [x] Regresión de API, SSE y seguimiento sin cambios de contrato.
- [x] Ruff, formato, suite completa y cobertura ≥ 70 %.

## Fase 4 — Entrega
- [x] Crear `evidence.md` con resultados verificables y limitaciones.
- [x] Actualizar `specs/README.md` y `CONSTITUTION.md`.
- [x] Revisar el diff, hacer commit y publicar la rama.
- [x] Abrir Pull Request hacia `main` y solicitar revisión.

## Criterios de cierre
- AC1: una sola búsqueda por `request_id` reconstruye la solicitud y liga la corrida.
- AC2: 100 % de las líneas emitidas por `m2_cad` son JSON válido con las claves mínimas.
- AC3: 0 secretos detectados en los logs de prueba.
- No se alteran el contrato HTTP, los eventos SSE ni la lógica CAD.
