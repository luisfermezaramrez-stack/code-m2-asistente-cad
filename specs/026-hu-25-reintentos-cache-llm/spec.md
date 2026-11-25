# SPEC-026 · HU-25 — Reintentos con backoff y caché de respuestas del LLM

- **ID**: SPEC-026
- **Historia**: #85 (HU-25) · 2 SP · Etiquetas: Backend, ML · Hito: M4
- **Planificación**: Ola 0 · Tamaño S · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: —
- **Rama**: `feature/hu-25-reintentos-cache-llm`
- **Estado**: Implementada y corregida tras la revisión del PR #126; `plan.md`, `tasks.md`
  y `evidence.md` actualizados
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

1. `_respuesta_modelo` hace una única llamada al modelo (`src/m2_cad/pipeline.py:386`,
   `llm.chat`), que a su vez hace un solo `httpx.post` sin reintento
   (`vendor/constraint-kit/constraint_kit/llm.py:68`). `vendor/` está gitignored: se
   restaura con `make vendor` en la revisión fijada por `CK_REV` en
   `scripts/vendor-constraint-kit.sh:10`, de modo que la cita resiste un clone limpio.
2. Cualquier fallo se convierte de inmediato en `ModeloNoDisponible`
   (`src/m2_cad/pipeline.py:387-396`), incluso un 5xx transitorio o un corte de conexión;
   la API lo devuelve como 503 en la ruta JSON (`src/m2_cad/api.py:137-139`) y en el
   adaptador SSE (`src/m2_cad/api.py:176-180`).
3. `_REINTENTOS_HTTP = "0"` (`src/m2_cad/seguimiento.py:32`) pertenece al cliente MLflow,
   no al LLM.
4. No hay caché: repetir la misma solicitud vuelve a pagar tokens.

Esta spec habilita la evaluación del banco con respuestas grabadas
([SPEC-045](../045-hu-44-banco-ci-replay/spec.md)) y el control de costo
([SPEC-033](../033-hu-32-costo-limites-idempotencia/spec.md)).

## Historia de usuario

**Como** usuario del asistente, **quiero** que un fallo pasajero del proveedor se reintente
solo y que una solicitud idéntica no se vuelva a cobrar, **para** no recibir un error por
una falla momentánea ni pagar dos veces la misma respuesta.

## Requisitos

### Funcionales

- **RF-1**: hasta N reintentos con backoff exponencial y jitter, sólo ante errores
  transitorios (**HTTP 500, 502, 503 y 504**, timeout y fallo de conexión). El `timeout`
  es un **plazo total** compartido por todos los intentos, no uno por intento.
- **RF-2**: los errores no transitorios (todos los 4xx, incluidos 401, 402 y 429, y los
  5xx permanentes como 501 y 505) no se reintentan y conservan sus mensajes actuales
  (`MENSAJES_HTTP`, `src/m2_cad/pipeline.py:96-100`).
- **RF-3**: agotados los reintentos o el plazo total, el error final se informa como hoy
  (`ModeloNoDisponible`) y el mensaje refleja el plazo global.
- **RF-4**: caché de respuestas indexada por hash(endpoint + prompt + modelo + parámetros
  + huella no reversible de la credencial activa) con TTL configurable.
- **RF-5**: métricas de número de reintentos y de aciertos/fallos de caché, registradas en
  el seguimiento existente. En una corrida fallida sólo se registran las claves `llm_*`:
  no se inventan tokens ni costo en 0.
- **RF-6**: si el trabajo SSE se cancela, el bucle de reintentos se detiene antes de
  iniciar otra llamada paga al proveedor.
- **RF-7**: una configuración inválida (`LLM_MAX_RETRIES=abc`, fuera de rango, etc.) se
  informa como `ModeloNoDisponible` (HTTP 503) con un mensaje claro, no como un 500 opaco.
- **RF-8**: sólo se guardan en caché respuestas cuyo programa se extrae correctamente; una
  salida JSON truncada o inválida no se reutiliza durante el TTL.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: el proveedor se simula.
- **RNF-2**: N, el backoff y el TTL se configuran por variable de entorno con valores por
  defecto seguros.
- **RNF-3**: la caché no almacena la API key ni cabeceras; la credencial sólo participa
  como huella SHA-256 dentro de la clave, nunca en claro.

> **Decisión**: 429 no es transitorio: conserva su mensaje de `MENSAJES_HTTP` y no se
> reintenta. Tampoco se reintentan 501 ni 505 (ver `plan.md`).

> **Supuesto**: el reintento se implementa en `m2_cad` alrededor de `llm.chat`, sin
> modificar el `constraint-kit` vendoreado.

## Criterios de aceptación

### AC1 — 5xx transitorio

- **Dado** un proveedor simulado que responde 503 en el primer intento y 200 en el segundo
- **Cuando** se procesa una solicitud
- **Entonces** el usuario recibe la pieza, no `ModeloNoDisponible`, y la métrica de
  reintentos registra 1.

### AC2 — Sin doble cobro

- **Dado** una solicitud ya respondida y dentro del TTL de caché
- **Cuando** se repite con el mismo prompt, modelo y parámetros
- **Entonces** no se llama al proveedor, no se pagan tokens y se registra un acierto de
  caché.

### AC3 — Errores no transitorios (AC de no regresión)

- **Dado** un proveedor simulado que responde 401 o 402
- **Cuando** se procesa una solicitud
- **Entonces** no hay reintentos y el mensaje en español es el actual.

> Este AC pasa hoy sin código nuevo: una sola llamada y mensajes de `MENSAJES_HTTP`
> (`src/m2_cad/pipeline.py:96-100,391-394`). Se conserva como prueba de no regresión del
> mecanismo de reintentos, no como trabajo nuevo.

### AC4 — Cancelación

- **Dado** un trabajo SSE cancelado antes o durante el backoff
- **Cuando** el bucle intenta continuar
- **Entonces** no se inicia otra llamada al proveedor y el trabajo termina como
  `cancelado` por un punto seguro.

### AC5 — Configuración inválida

- **Dado** `LLM_MAX_RETRIES=abc` o un valor fuera de rango
- **Cuando** se procesa una solicitud
- **Entonces** la API responde 503 con `ModeloNoDisponible` y un mensaje que nombra la
  variable, en lugar de un 500 genérico.

### AC6 — Respuesta inválida no cacheada

- **Dado** un proveedor que devuelve una sola vez JSON truncado o inválido
- **Cuando** se repite la misma descripción
- **Entonces** se vuelve a consultar al proveedor (no hay acierto de caché) y la primera
  respuesta inválida no queda almacenada.

## Fuera de alcance

- Topes de costo, límites de uso e idempotencia por cliente
  ([SPEC-033](../033-hu-32-costo-limites-idempotencia/spec.md)).
- Grabación y reproducción del banco en CI ([SPEC-045](../045-hu-44-banco-ci-replay/spec.md)).
- Caché distribuida o compartida entre instancias.

## Métricas de éxito

- Solicitudes con 5xx transitorio que llegan al usuario como error: 0 en pruebas.
- Tokens pagados por solicitudes repetidas dentro del TTL: 0.
- Llamadas pagas iniciadas después de cancelar el trabajo SSE: 0.
- Respuestas inválidas reutilizadas desde la caché: 0.
