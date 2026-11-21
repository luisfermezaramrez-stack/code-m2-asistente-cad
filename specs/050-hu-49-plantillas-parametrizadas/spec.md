# SPEC-050 · HU-49 — Plantillas parametrizadas de piezas

- **ID**: SPEC-050
- **Historia**: #109 (HU-49) · 3 SP · Etiquetas: Backend, ML · Hito: M4
- **Planificación**: Ola 3 (opcional) · Tamaño M · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: [SPEC-036](../036-hu-35-edicion-iterativa/spec.md)
- **Rama**: `feature/hu-49-plantillas-parametrizadas`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

Cada pieza se genera desde cero a partir de una descripción libre: el LLM traduce el texto
a un programa DSL con los tipos y parámetros que enumera el prompt
(`src/m2_cad/pipeline.py:70-93`). El `constraint-kit` vendoreado sí trae bibliotecas de
dominio: `library.py` carga definiciones de ensamble versionadas como JSON
(`vendor/constraint-kit/libraries/`) y la API propia del kit las expone con
`GET /libraries` y `POST /assembly/from_library` (`constraint_kit/api.py:684,690`); M2 no
las expone. El hueco es más fino: hay librerías, pero no **plantillas de pieza con
parámetros de rango validado y unidades declaradas** que el usuario pueda elegir y
ajustar, aunque el banco ya agrupa las solicitudes en familias (`plate`, `flange`,
`adapter`, `sheet_bracket`, `spacer`, `tornillería`; `data/test_cases.csv`).

Corresponde al ítem 30 del borrador ("Catálogo de plantillas"), mantenido y dependiente de
SPEC-036 para reutilizar el programa DSL de una pieza ya generada (`docs/backlog-v2.md`
§7).

## Historia de usuario

**Como** diseñador de componentes, **quiero** partir de una plantilla de pieza frecuente y
ajustar sus parámetros, **para** obtener variantes sin redactar cada vez la descripción
completa.

## Requisitos

### Funcionales

- **RF-1**: catálogo de plantillas, cada una con tipo de pieza, parámetros con nombre,
  unidad, valor por defecto y rango válido. Supuesto: una plantilla por familia del banco.
- **RF-2**: instanciar una plantilla con parámetros produce un programa DSL que pasa por la
  misma verificación determinista que el flujo por texto.
- **RF-3**: una pieza generada (por texto o por plantilla) puede guardarse como plantilla
  reutilizando su programa DSL (mecanismo de SPEC-036).
- **RF-4**: parámetros fuera de rango se rechazan con un mensaje que nombra el parámetro
  y el rango permitido, antes de construir.
- **RF-5**: la UI permite elegir una plantilla y editar sus parámetros. Supuesto: vista
  dentro del app shell de SPEC-039.

### No funcionales

- **RNF-1**: instanciar una plantilla no llama al LLM: no gasta tokens.
- **RNF-2**: las pruebas no usan red, API key ni GPU.
- **RNF-3**: las plantillas se versionan como datos, no como código.

## Criterios de aceptación

### AC1 — Instanciar plantilla

- **Dado** la plantilla de placa con agujeros
- **Cuando** se instancia con ancho 60 mm, fondo 50 mm y espesor 6 mm
- **Entonces** se entrega la pieza (STEP, GLB y CSV) sin llamar al LLM.

### AC2 — Parámetro inválido

- **Dado** una plantilla con espesor mínimo definido
- **Cuando** se envía un espesor por debajo del mínimo
- **Entonces** se rechaza con un mensaje que nombra el parámetro y su rango.

### AC3 — Guardar como plantilla

- **Dado** una pieza generada por texto
- **Cuando** el usuario la guarda como plantilla
- **Entonces** aparece en el catálogo y al instanciarla con sus valores reproduce la
  misma firma geométrica.

## Fuera de alcance

- Edición iterativa por lenguaje natural (SPEC-036).
- Plantillas de ensambles de varias piezas.
- Compartir plantillas entre usuarios (requiere SPEC-054).

## Métricas de éxito

- Una plantilla por familia del banco disponible en el catálogo.
- Tiempo de generación por plantilla sin latencia del LLM.
