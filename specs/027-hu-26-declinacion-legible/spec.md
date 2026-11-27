# SPEC-027 · HU-26 — Motivo de declinación legible y etiquetado por causa

- **ID**: SPEC-027
- **Historia**: #86 (HU-26) · 2 SP · Etiquetas: ML, Backend · Hito: M4
- **Planificación**: Ola 0 · Tamaño S · Épica: Pipeline
- **Responsable**: Luis Fernando Meza
- **Depende de**: —
- **Rama**: `feature/hu-26-declinacion-legible`
- **Estado**: Spec-first · implementada; `plan.md` y `tasks.md` en esta carpeta
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3

## Problema y contexto

`ErrorVerificacion` y `PiezaDeclinada` existen (`src/m2_cad/pipeline.py:115-127`), pero el
motivo que ve el usuario es técnico o poco accionable:

1. `verificar_programa` (`src/m2_cad/pipeline.py:200-219`) arma la declinación con la razón
   cruda del modelo (`«{detalle}»`) y, ante errores, une los mensajes de diagnóstico de
   `constraint-kit` tal como vienen.
2. `ErrorVerificacion` llega al usuario como 422 con `str(exc)`
   (`src/m2_cad/api.py:130-134` y `api.py:173-175`).
3. `_declinar` (`src/m2_cad/pipeline.py:130-136`) explica qué está fuera del catálogo pero
   no qué haría falta para aceptar la solicitud.
4. No hay etiqueta de causa estructurada: el registro (`src/m2_cad/registro.py:18-27`) y
   MLflow guardan texto libre, que no sirve como dimensión de métricas.

## Historia de usuario

**Como** usuario del asistente, **quiero** que una declinación me explique en español claro
por qué no se construyó la pieza y qué tendría que cambiar, **para** reformular la
solicitud sin conocer el DSL ni el verificador.

## Requisitos

### Funcionales

- **RF-1**: un catálogo cerrado de causas de declinación, que incluye al menos
  `familia_no_soportada`, `dimension_incoherente`, `verificacion_fallida`,
  `fuera_de_tolerancia` y `texto_ambiguo`.
- **RF-2**: cada declinación tiene exactamente una causa del catálogo.
- **RF-3**: el mensaje al usuario está en español, sin términos internos del DSL ni del
  verificador, e indica qué haría falta para aceptar la solicitud.
- **RF-4**: la etiqueta de causa se persiste de forma estructurada junto al resultado
  (registro y seguimiento), separada del texto del mensaje.
- **RF-5**: el detalle técnico se conserva para diagnóstico, pero no se muestra como
  mensaje principal.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU.
- **RNF-2**: se conservan los códigos HTTP actuales (422 para declinación).

> **Supuesto**: la lista de causas puede crecer al etiquetar el corpus de
> [SPEC-024](../024-hu-23-corpus-dorado-nucleo/spec.md); toda causa nueva entra al catálogo,
> nunca como texto libre.

> **Supuesto**: agregar la columna de causa al registro se coordina con la persistencia de
> [SPEC-031](../031-hu-30-persistencia-registro/spec.md) para no migrar dos veces.

## Criterios de aceptación

### AC1 — Causa en cada declinación del corpus

- **Dado** el corpus dorado de [SPEC-024](../024-hu-23-corpus-dorado-nucleo/spec.md)
- **Cuando** se procesan sus casos esperados como declinación
- **Entonces** cada uno tiene una causa del catálogo asignada.

### AC2 — Mensaje no técnico

- **Dado** cualquier declinación del corpus
- **Cuando** se lee el mensaje que recibe el usuario
- **Entonces** está en español, no contiene identificadores del DSL ni mensajes crudos del
  verificador, e indica qué haría falta para aceptarla.

### AC3 — Etiqueta como fuente de métricas

- **Dado** una declinación registrada
- **Cuando** se consulta el registro o la corrida de MLflow
- **Entonces** la causa aparece como campo o etiqueta estructurada, utilizable por las
  alertas de regresión ([SPEC-047](../047-hu-46-alertas-regresion/spec.md)) y por el
  panorama de métricas ([SPEC-052](../052-hu-51-panorama-metricas/spec.md)).

## Fuera de alcance

- Ampliar el catálogo de piezas o cambiar el criterio de declinación.
- Sugerir automáticamente una solicitud corregida.
- Construir las alertas o el panorama de métricas.

## Métricas de éxito

- Declinaciones del corpus con causa asignada: 100 %.
- Mensajes con términos técnicos del DSL o del verificador: 0.
