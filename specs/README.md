# Especificaciones SDD

Una carpeta por especificación, con `spec.md` (problema, requisitos y criterios
Given-When-Then), `plan.md` (diseño y decisiones) y `tasks.md` (tareas verificables).
Cada spec se vincula a su historia del tablero y a la PR que la implementa.

## Tipos

- **Spec Kit**: especificación original del proyecto, creada con Spec Kit.
- **Retroactiva**: redactada el 2026-11-13 **después** de fusionar la historia, para
  trazabilidad. Lo declara en su encabezado; no se presenta como especificación previa al
  código.
- **Spec-first**: redactada antes de implementar; la PR que la implemente aún está
  pendiente.

## Índice

| Spec | Historia | Issue | PR | Tipo | Estado |
| --- | --- | --- | --- | --- | --- |
| [001](001-gemma-constraintkit-serve/) | HU-01 · Gemma 4 12B ConstraintKit servido | #1 | #17 | Spec Kit | Fusionada; modelo heredado tras HU-14 |
| [002](002-step-verificado/) | HU-04 · Pieza STEP verificada | #4 | #32 | Spec Kit | Fusionada |
| [003](003-declinacion-preliminar/) | HU-05 · Declinación y marca preliminar | #5 | #36 | Spec Kit | Fusionada |
| [004](004-registro-solicitudes/) | HU-06 · Registro de solicitudes (parte L. Meza) | #6 | #29 | Spec Kit | Fusionada |
| [005](005-ci-github-actions/) | HU-09 · CI con GitHub Actions y pre-commit | #9 | #14 | Spec Kit | Fusionada |
| [006](006-prueba-usuarios/) | HU-11 · Prueba de uso simulada | #11 | #71 | Spec Kit | Fusionada |
| [007](007-hu-08-interfaz-gradio/) | HU-08 · Interfaz web con Gradio | #8 | #34 | Spec Kit | Fusionada; reemplazada por HU-15 |
| [008](008-hu-14-deepseek/) | HU-14 · DeepSeek por API sin traducción | #37 | #43 | Retroactiva | Fusionada |
| [009](009-hu-16-mlflow/) | HU-16 · Seguimiento con MLflow | #45 | #47 | Spec Kit | Fusionada |
| [010](010-hu-10-despliegue-local/) | HU-10 · Despliegue local con Docker Compose | #10 | #66 | Spec-first | Fusionada |
| [011](011-hu-02-banco-solicitudes/) | HU-02 · Banco de 40 solicitudes | #2 | #33 | Retroactiva | Fusionada |
| [012](012-hu-03-traduccion-es-en/) | HU-03 · Traducción ES→EN | #3 | #27 | Retroactiva | Fusionada; retirada por HU-14 |
| [013](013-hu-06-api-fastapi/) | HU-06 · API FastAPI (parte J. C. Pérez) | #6 | #16 | Retroactiva | Fusionada |
| [014](014-hu-12-manuales/) | HU-12 · Manuales y README | #12 | #41 | Retroactiva | Fusionada |
| [015](015-hu-15-vue-sse/) | HU-15 · Interfaz Vue con SSE | #39 | #46 | Retroactiva | Fusionada |
| [016](016-hu-07-corrida-banco/) | HU-07 · Corrida del banco con reporte por familia | #7 | #65 | Spec-first | Fusionada |
| [017](017-hu-13-informe-final/) | HU-13 · Informe final | #13 | #70 | Spec-first | Fusionada; actualizada por 022; `v1.0` en 021 |
| [018](018-model-card/) | HU-17 · Model Card del modelo servido | #59 | #60 | Spec-first | Fusionada |
| [019](019-visor-3d-contraste/) | HU-18 · Contraste del fondo del visor 3D (refactor) | #63 | #64 | Spec-first | Fusionada |
| [020](020-diagrama-arquitectura/) | HU-19 · Diagrama de arquitectura actualizado y enlace al tablero (refactor) | #68 | #69 | Spec-first | Fusionada |
| [021](021-hu-20-cierre-entrega/) | HU-20 · Publicación de la entrega en `main` con `v1.0` | #72 | #75 | Spec-first | Fusionada; `v1.0` publicada |
| [022](022-hu-21-informe-final-refactor/) | HU-21 · Refactor del informe final y la trazabilidad de la HU-13 (refactor) | #73 | #74 | Spec-first | Fusionada |
| [023](023-hu-22-constitution-refactor/) | HU-22 · Refactor de CONSTITUTION.md al estado real de la entrega (refactor) | #77 | #78 | Spec-first | Fusionada |
| [057](057-hu-56-constitucion-speckit/) | HU-56 · Constitución de Spec Kit apuntando a `CONSTITUTION.md` (refactor) | #117 | #116 | Spec-first | En revisión |

## Backlog v2 — Profesionalización

Specs redactadas desde [`docs/backlog-v2.md`](../docs/backlog-v2.md). El ID sigue el orden de
ejecución por olas (0 → 3); sólo tienen `spec.md`: `plan.md` y `tasks.md` se redactan al
tomar la HU. Issue y PR se registran al abrirse.

| Spec | Historia | Ola | Responsable | Issue | PR | Tipo | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [024](024-hu-23-corpus-dorado-nucleo/) | HU-23 · Corpus dorado del núcleo determinista en CI | 0 | Luis Meza | #83 | — | Spec-first | Propuesta |
| [025](025-hu-24-logging-estructurado/) | HU-24 · Logging estructurado y trazas correlacionadas | 0 | Juan Camilo | #84 | — | Spec-first | Propuesta |
| [026](026-hu-25-reintentos-cache-llm/) | HU-25 · Reintentos con backoff y caché de respuestas del LLM | 0 | Juan Camilo | #85 | — | Spec-first | Propuesta |
| [027](027-hu-26-declinacion-legible/) | HU-26 · Motivo de declinación legible y etiquetado por causa | 0 | Luis Meza | #86 | — | Spec-first | Propuesta |
| [028](028-hu-27-tipos-openapi/) | HU-27 · Tipos del frontend generados desde OpenAPI | 0 | Carlos | #87 | — | Spec-first | Propuesta |
| [029](029-hu-28-escaneo-seguridad/) | HU-28 · Escaneo de dependencias y secretos en CI | 0 | Carlos | #88 | — | Spec-first | Propuesta |
| [030](030-hu-29-runbook-operativo/) | HU-29 · Runbook operativo | 0 | Carlos | #89 | — | Spec-first | Propuesta |
| [031](031-hu-30-persistencia-registro/) | HU-30 · Persistencia transaccional, retención y backup del registro | 1 | Juan Camilo | #90 | — | Spec-first | Propuesta |
| [032](032-hu-31-api-v1/) | HU-31 · API `/v1` versionada con contrato congelado | 1 | Juan Camilo | #91 | — | Spec-first | Propuesta |
| [033](033-hu-32-costo-limites-idempotencia/) | HU-32 · Control de costo, límites de uso e idempotencia | 1 | Juan Camilo | #92 | — | Spec-first | Propuesta |
| [034](034-hu-33-prompts-versionados/) | HU-33 · Prompts versionados como artefactos | 1 | Luis Meza | #93 | — | Spec-first | Propuesta |
| [035](035-hu-34-sistema-diseno-v2/) | HU-34 · Sistema de diseño v2: tokens, tipografía y modo oscuro | 1 | Carlos | #94 | — | Spec-first | Propuesta |
| [036](036-hu-35-edicion-iterativa/) | HU-35 · Edición iterativa de la pieza | 1 | Luis Meza | #95 | — | Spec-first | Propuesta |
| [037](037-hu-36-endurecimiento-descargas/) | HU-36 · Endurecimiento de artefactos y descargas | 1 | Juan Camilo | #96 | — | Spec-first | Propuesta |
| [038](038-hu-37-historial-ui/) | HU-37 · Historial de solicitudes en la UI | 2 | Carlos | #97 | — | Spec-first | Propuesta |
| [039](039-hu-38-app-shell/) | HU-38 · App shell y navegación por vistas | 2 | Carlos | #98 | — | Spec-first | Propuesta |
| [040](040-hu-39-visor-ortogonal-medidas/) | HU-39 · Visor 3D: vistas ortogonales, medidas y captura | 2 | Carlos | #99 | — | Spec-first | Propuesta |
| [041](041-hu-40-wcag-aa/) | HU-40 · Cierre de brechas WCAG 2.1 AA | 2 | Carlos | #100 | — | Spec-first | Propuesta |
| [042](042-hu-41-e2e-playwright/) | HU-41 · E2E del frontend con Playwright en CI | 2 | Carlos | #101 | — | Spec-first | Propuesta |
| [043](043-hu-42-exportacion-dxf/) | HU-42 · Exportación DXF de planos 2D | 2 | Luis Meza | #102 | — | Spec-first | Propuesta |
| [044](044-hu-43-exportacion-pdf/) | HU-43 · Exportación PDF de planos con cotas | 2 | Luis Meza | #103 | — | Spec-first | Propuesta |
| [045](045-hu-44-banco-ci-replay/) | HU-44 · Evaluación continua del banco con respuestas grabadas | 2 | Juan Camilo | #104 | — | Spec-first | Propuesta |
| [046](046-hu-45-cola-persistente/) | HU-45 · Cola persistente de trabajos y worker | 2 | Juan Camilo | #105 | — | Spec-first | Propuesta |
| [047](047-hu-46-alertas-regresion/) | HU-46 · Alertas de regresión de calidad | 3 | Juan Camilo | #106 | — | Spec-first | Propuesta (opcional) |
| [048](048-hu-47-despliegue-nube/) | HU-47 · Despliegue en la nube | 3 | Carlos | #107 | — | Spec-first | Propuesta (opcional) |
| [049](049-hu-48-materiales-tolerancias-bom/) | HU-48 · Materiales, tolerancias y BOM con costos | 3 | Luis Meza | #108 | — | Spec-first | Propuesta (opcional) |
| [050](050-hu-49-plantillas-parametrizadas/) | HU-49 · Plantillas parametrizadas de piezas | 3 | Luis Meza | #109 | — | Spec-first | Propuesta (opcional) |
| [051](051-hu-50-cortes-visor-3d/) | HU-50 · Cortes y secciones en el visor 3D | 3 | Carlos | #110 | — | Spec-first | Propuesta (opcional) |
| [052](052-hu-51-panorama-metricas/) | HU-51 · Panorama de métricas sobre MLflow | 3 | Juan Camilo | #111 | — | Spec-first | Propuesta (opcional) |
| [053](053-hu-52-ab-prompts-modelos/) | HU-52 · Comparación A/B de prompts y modelos | 3 | Juan Camilo | #112 | — | Spec-first | Propuesta (opcional) |
| [054](054-hu-53-autenticacion/) | HU-53 · Autenticación y usuarios | 3 | Juan Camilo | #113 | — | Spec-first | Propuesta (opcional) |
| [055](055-hu-54-sitio-documentacion/) | HU-54 · Sitio de documentación publicado | 3 | Carlos | #114 | — | Spec-first | Propuesta (opcional) |
| [056](056-hu-55-releases-automaticos/) | HU-55 · Releases automáticos con changelog | 3 | Carlos | #115 | — | Spec-first | Propuesta (opcional) |
