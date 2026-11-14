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
| [006](006-prueba-usuarios/) | HU-11 · Prueba con usuarios externos | #11 | — | Spec Kit | Pendiente |
| [007](007-hu-08-interfaz-gradio/) | HU-08 · Interfaz web con Gradio | #8 | #34 | Spec Kit | Fusionada; reemplazada por HU-15 |
| [008](008-hu-14-deepseek/) | HU-14 · DeepSeek por API sin traducción | #37 | #43 | Retroactiva | Fusionada |
| [009](009-hu-16-mlflow/) | HU-16 · Seguimiento con MLflow | #45 | #47 | Spec Kit | Fusionada |
| [010](010-hu-10-despliegue-local/) | HU-10 · Despliegue local con Docker Compose | #10 | — | Spec-first | Pendiente |
| [011](011-hu-02-banco-solicitudes/) | HU-02 · Banco de 40 solicitudes | #2 | #33 | Retroactiva | Fusionada |
| [012](012-hu-03-traduccion-es-en/) | HU-03 · Traducción ES→EN | #3 | #27 | Retroactiva | Fusionada; retirada por HU-14 |
| [013](013-hu-06-api-fastapi/) | HU-06 · API FastAPI (parte J. C. Pérez) | #6 | #16 | Retroactiva | Fusionada |
| [014](014-hu-12-manuales/) | HU-12 · Manuales y README | #12 | #41 | Retroactiva | Fusionada |
| [015](015-hu-15-vue-sse/) | HU-15 · Interfaz Vue con SSE | #39 | #46 | Retroactiva | Fusionada |
| [016](016-hu-07-corrida-banco/) | HU-07 · Corrida del banco con reporte por familia | #7 | — | Spec-first | Pendiente |
| [017](017-hu-13-informe-final/) | HU-13 · Informe final | #13 | — | Spec-first | Pendiente |
| [018](018-model-card/) | HU-17 · Model Card del modelo servido | #59 | #60 | Spec-first | Fusionada |
| [019](019-visor-3d-contraste/) | HU-18 · Contraste del fondo del visor 3D (refactor) | #63 | — | Spec-first | En revisión |
