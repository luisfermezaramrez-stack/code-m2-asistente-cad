# HU-49 · Plantillas parametrizadas de piezas (issue #109) — SPEC-050

Objetivo: catálogo de plantillas, instanciación sin LLM, guardar como plantilla y vista en la SPA.
Rama `feature/hu-49-plantillas-parametrizadas` (desde `origin/main` 55db05d). Entrega: un PR,
como #160 y #161. Runner: `make check` (pytest, Vitest) con `M2_DOWNLOAD_SECRET` ≥ 32 bytes.

## Specs

Fuente: `specs/050-hu-49-plantillas-parametrizadas/spec.md` y `plan.md` (decisiones aprobadas).

- S1 (RF-1): «catálogo de plantillas, cada una con tipo de pieza, parámetros con nombre, unidad, valor por defecto y rango válido».
- S2 (RF-2 / AC1): «Dado la plantilla de placa con agujeros / Cuando se instancia con ancho 60 mm, fondo 50 mm y espesor 6 mm / Entonces se entrega la pieza (STEP, GLB y CSV) sin llamar al LLM».
- S3 (RF-4 / AC2): «parámetros fuera de rango se rechazan con un mensaje que nombra el parámetro y el rango permitido, antes de construir».
- S4 (RF-3 / AC3): «una pieza generada (por texto o por plantilla) puede guardarse como plantilla reutilizando su programa DSL» y «al instanciarla con sus valores reproduce la misma firma geométrica».
- S5 (RF-5): «la UI permite elegir una plantilla y editar sus parámetros».
- S6 (RNF-1..3): sin LLM ni tokens al instanciar; pruebas sin red, API key ni GPU; plantillas versionadas como datos.
- S7 (decisión aprobada b): una plantilla guardada es del usuario; ajena = 404.

## Tasks

- [x] T0 · S1-S7 · plan y decisiones aprobados · delegado (w6:p5) · 668fed6
- [ ] T1 · S1, S3, S6 · catálogo, cargador, `make plantillas-check` · delegado (w6:p5, sin commitear) → inline
- [ ] T2 · S2, S4, S7 · API `/v1/plantillas` y contrato regenerado · inline
- [ ] T3 · S5 · vista `/plantillas` en la SPA, Vitest · inline
- [ ] T4 · docs, índice de specs, evidencia y `make check` · inline

## Log

- L1 (2026-11-28, usuario): «Continúa con la historia de usuario número 49. Actúa como orquestador como en la anterior y envíaselo al otro agente.»
- L2: el plan (a)-(d) se aprobó tal cual.
- L3: w6:p5 se detuvo por falta de cuota de DeepSeek (402) con T1 sin commitear. Usuario: «Sigo yo inline». Ruta de T1-T4: inline, porque no hay razón de delegar un writer.
