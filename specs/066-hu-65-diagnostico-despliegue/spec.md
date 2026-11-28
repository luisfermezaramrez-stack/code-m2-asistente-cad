# SPEC-066 · HU-65 — El despliegue se diagnostica: readiness con datos y motivo público

- **ID**: SPEC-066
- **Historia**: #174 (HU-65) · 3 SP · Etiquetas: Backend, infra
- **Responsable**: Luis Meza
- **Rama**: `fix/hu-65-diagnostico-despliegue`
- **Estado**: Parte A implementada en local (pendiente de PR); **parte B spec-first**, requiere
  un despliegue supervisado para validarse.
- **Resuelve**: la falla de producción del 2026-11-28 — `ErrorMateriales: no existe la tabla de
  materiales: /app/data/materiales.toml` en toda generación.

## Problema y contexto

En el droplet de producción cada solicitud terminaba en «No fue posible completar la
generación.» mientras `/v1/health` y `/v1/ready` respondían `ok`. Tres defectos se sumaron:

1. **El dato no estaba en el contenedor.** El job `deploy` monta el volumen con nombre
   `m2-cad-data` sobre `/app/data`, y Docker sólo siembra un volumen con el contenido de la
   imagen cuando lo crea vacío. Ese volumen venía de despliegues anteriores, así que
   `materiales.toml` (HU-48) y `plantillas.toml` (HU-49) nunca llegaron.
2. **El readiness mentía.** `/v1/ready` sólo evaluaba `_modelo_configurado()`: con el modelo
   configurado decía `ok` aunque faltaran los datos.
3. **El error se aplanaba.** `worker.py` y `trabajos.py` convertían cualquier `ErrorPipeline`
   en el mensaje genérico, así que el traceback con la causa real quedaba sólo en los logs del
   droplet.

## Historia de usuario

**Como** operador del servicio, **quiero** que el readiness y los mensajes de error digan qué
dato falta, **para** enterarme del problema antes que un usuario y no tener que leer logs del
droplet para descubrir que faltaba un archivo.

## Requisitos

### Parte A — implementada en esta HU

- **RF-1**: `/v1/ready` informa una dependencia `datos` (`ok` / `no_disponible`) que verifica la
  tabla de materiales y el catálogo de plantillas, sin crear ni modificar archivos.
- **RF-2**: `/v1/health` sigue informando sólo la vida del proceso (contrato del HEALTHCHECK).
- **RF-3**: un `ErrorMateriales` produce el motivo público «Faltan los datos del despliegue: no
  se encontró la tabla de materiales.», sin la ruta interna del contenedor.
- **RF-4**: `ModeloNoDisponible` y `ErrorGeneracion` conservan su mensaje; cualquier otro fallo
  sigue respondiendo el mensaje genérico (no se exponen detalles internos).
- **RF-5**: el mismo mapeo lo usan el seguimiento SSE (`trabajos.py`) y el worker de la cola
  (`worker.py`), para que un fallo se explique igual por los dos caminos.

### Parte B — spec-first, pendiente de despliegue supervisado

- **RF-6**: `/app/data` deja de estar tapado por un volumen: los datos versionados viajan en la
  imagen y son de sólo lectura.
- **RF-7**: el estado mutable (cola y registro) vive en `/app/estado`, con su propio volumen.
- **RF-8**: migración idempotente y de una sola vez: si `/app/estado` no tiene `cola.json` o
  `registro.csv`, se copian desde el volumen anterior; el volumen viejo **no** se borra.
- **RF-9**: el job `deploy` verifica al final que `/v1/ready` responde 200 con `datos: ok`; si no,
  el despliegue falla en vez de dar por buena una imagen inservible.

### No funcionales

- **RNF-1**: ninguna comprobación de readiness escribe en disco.
- **RNF-2**: los mensajes públicos no incluyen rutas absolutas, trazas ni credenciales.

## Criterios de aceptación

### AC1 — Ready con datos

- **Dado** un despliegue con `materiales.toml` y `plantillas.toml` presentes
- **Cuando** se consulta `/v1/ready`
- **Entonces** responde 200 con `dependencias.datos: "ok"`.

### AC2 — Ready sin datos

- **Dado** un despliegue al que le falta la tabla de materiales
- **Cuando** se consulta `/v1/ready`
- **Entonces** responde 503 con `datos: "no_disponible"`, y `/v1/health` sigue en 200.

### AC3 — Motivo público accionable

- **Dado** una generación que falla por `ErrorMateriales`
- **Cuando** el usuario recibe el terminal del trabajo
- **Entonces** el motivo es el de datos faltantes y no contiene rutas internas.

### AC4 — Lo desconocido sigue genérico

- **Dado** un fallo no clasificado
- **Cuando** el usuario recibe el terminal
- **Entonces** el motivo sigue siendo «No fue posible completar la generación.».

### AC5 — El deploy no publica una imagen inservible

- **Dado** el job `deploy` con la parte B aplicada
- **Cuando** el servicio arranca sin los datos versionados
- **Entonces** el job falla mostrando `/v1/ready` en `no_disponible`.

## Fuera de alcance

- Cambiar el esquema del registro o de la cola.
- Reintentos, caché o degradación del pipeline ante datos faltantes.
- Borrar el volumen `m2-cad-data` (se conserva como respaldo tras la migración).

## Métricas de éxito

- Un despliegue roto por datos faltantes se detecta en `/v1/ready`, no en el primer usuario.
- Cero motivos genéricos para fallos de datos.
