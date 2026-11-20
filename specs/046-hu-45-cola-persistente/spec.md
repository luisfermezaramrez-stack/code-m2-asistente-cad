# SPEC-046 · HU-45 — Cola persistente de trabajos y worker

- **ID**: SPEC-046
- **Historia**: issue por crear · Ola 2 · Tamaño L · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-031](../031-hu-30-persistencia-registro/spec.md)
- **Rama**: `feature/hu-45-cola-persistente`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

1. `GestorTrabajos` guarda los trabajos en un diccionario en memoria con capacidad de
   128 (`src/m2_cad/trabajos.py:141-161`); al llenarse expulsa un terminado o responde
   503.
2. El contenedor arranca `uvicorn` con `--workers 1` (`Dockerfile:55`).
3. Un reinicio del proceso pierde todos los trabajos en curso y sus eventos SSE.

Con la persistencia transaccional de SPEC-031 disponible, los trabajos pueden vivir
fuera del proceso de la API y procesarse en un worker separado.

## Historia de usuario

**Como** operador del servicio, **quiero** una cola persistente con un worker separado,
**para** reiniciar o desplegar sin perder las solicitudes en curso.

## Requisitos

### Funcionales

- **RF-1**: los trabajos se encolan en una cola persistente apoyada en SPEC-031.
- **RF-2**: un worker separado del proceso de la API consume la cola.
- **RF-3**: tras un reinicio, los trabajos no terminados se reanudan.
- **RF-4**: el apagado drena de forma ordenada: no toma trabajos nuevos y cierra los
  flujos SSE en un límite de evento.

### No funcionales

- **RNF-1**: se conserva el contrato actual de `/generaciones` y del flujo SSE.
- **RNF-2**: las pruebas no usan red, API key ni GPU: el modelo se simula.
- **RNF-3**: Supuesto: reanudar un trabajo no duplica su fila en el registro.

## Criterios de aceptación

### AC1 — Reinicio sin pérdida

- **Dado** solicitudes en curso
- **Cuando** se reinicia el servicio
- **Entonces** ninguna solicitud se pierde y todas llegan a un estado terminal.

### AC2 — Drenaje sin cortar eventos

- **Dado** un cliente suscrito al SSE de un trabajo
- **Cuando** el servicio se apaga de forma ordenada
- **Entonces** el flujo no se corta a mitad de un evento.

### AC3 — Worker separado

- **Dado** el servicio desplegado
- **Cuando** se envía una solicitud
- **Entonces** la procesa un worker distinto del proceso de la API.

## Fuera de alcance

- Escalado horizontal y despliegue en la nube (SPEC-048).
- Límites de uso e idempotencia (SPEC-033).
- Prioridades o reintentos de trabajos fallidos del modelo (SPEC-026).

## Métricas de éxito

- Cero solicitudes perdidas en reinicios controlados.
- Cero eventos SSE truncados durante el drenaje.
