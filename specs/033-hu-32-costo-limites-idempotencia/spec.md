# SPEC-033 · HU-32 — Control de costo, límites de uso e idempotencia

- **ID**: SPEC-033
- **Historia**: issue por crear · Ola 1 · Tamaño M · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-026](../026-hu-25-reintentos-cache-llm/spec.md)
- **Rama**: `feature/hu-32-costo-limites-idempotencia`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §4
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

Cada solicitud a `/generar` consume tokens pagados de DeepSeek, pero el servicio no
pone ningún límite:

1. Los tokens y el costo **ya se calculan**: `seguimiento.costo_usd`
   (`src/m2_cad/seguimiento.py:71-81`) con precios leídos del entorno
   (`seguimiento.py:106-107`); la API anota los tokens del `usage`
   (`src/m2_cad/api.py:97-109`) y registra el costo en MLflow (`api.py:302-311`).
2. Ese costo sólo se observa por corrida: no hay gasto acumulado consultable ni tope por
   ventana, por sesión o diario.
3. No hay rate limit: no hay `slowapi` ni middleware de límites. El único límite actual es
   de capacidad, no de uso: `GestorTrabajos` retiene hasta 128 trabajos y, si ninguno es
   terminal, rechaza con 503 (`src/m2_cad/trabajos.py:144-161`). El servicio corre con
   `--workers 1` (`Dockerfile:55`).
4. `/generar` no acepta clave de idempotencia (`api.py:397-414`): reenviar la misma
   solicitud repite la llamada al modelo y el gasto.

SPEC-026 aporta la caché de respuestas del LLM; esta spec se apoya en ella para no
repetir llamadas pagadas.

## Historia de usuario

**Como** responsable del presupuesto del servicio, **quiero** topes de uso, un
presupuesto diario y una clave de idempotencia en `/generar`, **para** que ningún uso
excesivo o reintento del cliente genere gasto no previsto.

## Requisitos

### Funcionales

- **RF-1**: tope de solicitudes por ventana de tiempo y por sesión.
- **RF-2**: presupuesto diario configurable en USD.
- **RF-3**: al excederse un tope o el presupuesto, la solicitud se rechaza de forma
  explícita con un error tipado, **antes** de llamar al modelo.
- **RF-4**: `/generar` acepta la cabecera `Idempotency-Key`; el mismo valor devuelve la
  generación ya existente sin crear otra.
- **RF-5**: se publica el gasto acumulado como artefacto nuevo (endpoint o KPI agregado);
  hoy sólo existe `costo_usd` por corrida en MLflow (`api.py:302-311`).

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: el modelo y el `usage` se simulan.
- **RNF-2**: sin `Idempotency-Key` ni topes configurados, el comportamiento actual de
  `/generar` (JSON y SSE) no cambia.
- **RNF-3**: el tope por ventana convive con el tope de capacidad de 128 trabajos, que se
  conserva con su 503 actual; ambos se distinguen por su error tipado.
- **Supuesto**: el tope por ventana se evalúa antes de crear el trabajo, de modo que una
  solicitud rechazada por límite no ocupa capacidad del `GestorTrabajos`.
- **Supuesto**: con `--workers 1` los contadores de ventana y presupuesto pueden vivir en
  el proceso; si se escala a varios workers, el almacenamiento compartido se decide en
  `plan.md`.
- **Supuesto**: la definición de "sesión" (cabecera, IP u otro identificador) se decide
  en `plan.md`; la autenticación queda fuera (SPEC-054).

## Criterios de aceptación

### AC1 — Presupuesto excedido

- **Dado** un presupuesto diario ya consumido
- **Cuando** llega una nueva solicitud a `/generar`
- **Entonces** el servicio devuelve un error tipado y no se realiza ninguna llamada
  pagada al modelo.

### AC2 — Idempotencia

- **Dado** una generación creada con un `Idempotency-Key`
- **Cuando** se reenvía la misma solicitud con el mismo `Idempotency-Key`
- **Entonces** no se crea una segunda generación ni se suma costo, y se devuelve la
  generación original.

### AC3 — Límite por ventana

- **Dado** un tope de K solicitudes por ventana
- **Cuando** una sesión envía K + 1 solicitudes dentro de la ventana
- **Entonces** la solicitud K + 1 se rechaza con el error tipado de límite.

### AC4 — Gasto acumulado

- **Dado** varias generaciones con `usage` simulado
- **Cuando** se consulta el endpoint o KPI de gasto acumulado (artefacto nuevo)
- **Entonces** devuelve la suma de `costo_usd` de esas generaciones.

> El `costo_usd` por corrida ya se registra (`api.py:302-311`); este AC falla hoy porque no
> existe el agregado consultable.

## Fuera de alcance

- Autenticación y cuentas de usuario ([SPEC-054](../054-hu-53-autenticacion/spec.md)).
- Facturación o cobro a usuarios.
- Reintentos y caché del LLM (SPEC-026).

## Métricas de éxito

- 0 llamadas pagadas tras exceder el presupuesto.
- 0 generaciones duplicadas por reenvío con la misma `Idempotency-Key`.
