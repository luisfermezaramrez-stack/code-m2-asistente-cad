# SPEC-036 · HU-35 — Edición iterativa de la pieza

- **ID**: SPEC-036
- **Historia**: issue por crear · Ola 1 · Tamaño L · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: [SPEC-034](../034-hu-33-prompts-versionados/spec.md)
- **Rama**: `feature/hu-35-edicion-iterativa`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §4

## Problema y contexto

El pipeline traduce una descripción a un programa DSL verificable, pero cada solicitud
empieza de cero:

1. `/generar` solo acepta `texto` (`src/m2_cad/api.py:35-51`, `api.py:397-414`).
2. No existe un endpoint que reciba el programa o la pieza anterior: para corregir un
   espesor el usuario debe reescribir la descripción completa y el modelo regenera todo.
3. Cada generación escribe en un directorio nuevo de `outputs/`
   (`src/m2_cad/pipeline.py:434-435`) sin relación con versiones previas.

Editar sobre el programa DSL es el diferenciador principal del pipeline: la verificación
determinista se puede repetir sobre un cambio acotado. La spec depende de SPEC-034 para
que cada versión sea trazable a su prompt, y usa la causa de declinación de
[SPEC-027](../027-hu-26-declinacion-legible/spec.md).

## Historia de usuario

**Como** diseñador que ya obtuvo una pieza, **quiero** pedir un cambio en lenguaje natural
sobre esa pieza, **para** obtener una nueva versión verificada sin perder la anterior ni
volver a describirla entera.

## Requisitos

### Funcionales

- **RF-1**: un endpoint recibe la pieza previa y una instrucción de cambio en español.
- **RF-2**: el resultado incluye el diff entre el programa DSL previo y el nuevo.
- **RF-3**: el programa nuevo pasa por la misma verificación determinista que una
  generación inicial.
- **RF-4**: una edición verificada produce una nueva versión de la pieza y conserva la
  anterior.
- **RF-5**: cada solicitud mantiene un historial de versiones consultable.
- **RF-6**: si la edición rompe la verificación, se declina con la causa etiquetada de
  SPEC-027 y la versión anterior queda intacta.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU: el modelo se simula.
- **RNF-2**: `/generar` conserva su contrato actual.
- **RNF-3**: cada versión registra la versión de prompt usada (SPEC-034).
- **Supuesto**: la forma de identificar la pieza previa (id de solicitud o programa
  enviado por el cliente) se decide en `plan.md`.

## Criterios de aceptación

### AC1 — Edición verificada

- **Dado** una pieza generada y verificada
- **Cuando** se envía la instrucción "hazla 5 mm más gruesa"
- **Entonces** se entrega una pieza nueva verificada, con el diff del programa DSL, y la
  versión anterior se conserva.

### AC2 — Edición que rompe la verificación

- **Dado** una pieza generada y verificada
- **Cuando** se pide un cambio que hace fallar la verificación
- **Entonces** el servicio declina con la causa etiquetada de SPEC-027 y no reemplaza la
  versión anterior.

### AC3 — Historial de versiones

- **Dado** una solicitud con dos ediciones
- **Cuando** se consulta su historial
- **Entonces** lista las tres versiones en orden, cada una con su programa y sus
  artefactos.

## Fuera de alcance

- Historial de solicitudes en la UI ([SPEC-038](../038-hu-37-historial-ui/spec.md)).
- Plantillas parametrizadas ([SPEC-050](../050-hu-49-plantillas-parametrizadas/spec.md)).
- Edición directa del programa DSL por el usuario.

## Métricas de éxito

- Proporción de ediciones que producen una pieza verificada.
- 0 versiones anteriores perdidas o sobrescritas.
