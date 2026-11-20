# SPEC-026 · HU-25 — Reintentos con backoff y caché de respuestas del LLM

- **ID**: SPEC-026
- **Historia**: issue por crear · Ola 0 · Tamaño S · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: —
- **Rama**: `feature/hu-25-reintentos-cache-llm`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3

## Problema y contexto

1. `_respuesta_modelo` hace una única llamada al modelo (`src/m2_cad/pipeline.py:386`,
   `llm.chat`), que a su vez hace un solo `httpx.post` sin reintento
   (`vendor/constraint-kit/constraint_kit/llm.py:68`).
2. Cualquier fallo se convierte de inmediato en `ModeloNoDisponible`
   (`src/m2_cad/pipeline.py:387-396`), incluso un 5xx transitorio o un corte de conexión;
   la API lo devuelve como 503 (`src/m2_cad/api.py:176-180`).
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
  transitorios (5xx, timeout y fallo de conexión).
- **RF-2**: los errores no transitorios (401, 402 y demás 4xx) no se reintentan y conservan
  sus mensajes actuales (`MENSAJES_HTTP`, `src/m2_cad/pipeline.py:96-100`).
- **RF-3**: agotados los reintentos, el error final se informa como hoy
  (`ModeloNoDisponible`).
- **RF-4**: caché de respuestas indexada por hash(prompt + modelo + parámetros) con TTL
  configurable.
- **RF-5**: métricas de número de reintentos y de aciertos/fallos de caché, registradas en
  el seguimiento existente.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: el proveedor se simula.
- **RNF-2**: N, el backoff y el TTL se configuran por variable de entorno con valores por
  defecto seguros.
- **RNF-3**: la caché no almacena la API key ni cabeceras.

> **Supuesto**: si 429 se trata como transitorio (excepción a RF-2) se decide en `plan.md`;
> hoy tiene mensaje propio en `MENSAJES_HTTP`.

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

### AC3 — Errores no transitorios

- **Dado** un proveedor simulado que responde 401 o 402
- **Cuando** se procesa una solicitud
- **Entonces** no hay reintentos y el mensaje en español es el actual.

## Fuera de alcance

- Topes de costo, límites de uso e idempotencia por cliente
  ([SPEC-033](../033-hu-32-costo-limites-idempotencia/spec.md)).
- Grabación y reproducción del banco en CI ([SPEC-045](../045-hu-44-banco-ci-replay/spec.md)).
- Caché distribuida o compartida entre instancias.

## Métricas de éxito

- Solicitudes con 5xx transitorio que llegan al usuario como error: 0 en pruebas.
- Tokens pagados por solicitudes repetidas dentro del TTL: 0.
