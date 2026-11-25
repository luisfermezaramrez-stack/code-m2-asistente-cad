# HU-23 · Corpus dorado del núcleo determinista en CI

Issue #83 · SPEC-024 · 3 SP · Ola 0 · Hito M4 · Etiquetas: Testing, ML · 1 SP = 1 día.

Rama `feature/hu-23-corpus-dorado-nucleo`. Specs y criterios: `specs/024-hu-23-corpus-dorado-nucleo/spec.md`.

## Specs

S1 — RF-1: «un corpus versionado de pares *programa DSL → resultado esperado*, donde el resultado es `acepta` con el hash del STEP o `declina`.»

S2 — RF-2: «el corpus declara de forma explícita qué casos se esperan como declinación; un caso sin resultado declarado es un error del corpus, no un caso aceptado.»

S3 — RF-3: «un runner recorre el corpus a través de `verificar_programa` y `construir_pieza`, y compara cada resultado con el congelado.»

S4 — RF-4: «un job de CI ejecuta el runner en cada PR y falla ante cualquier divergencia (aceptación ↔ declinación, o hash distinto), indicando el caso y la diferencia.»

S5 — RF-5: «un procedimiento documentado regenera el corpus cuando un cambio geométrico es intencional, de modo que la actualización quede visible en el diff de la PR.»

S6 — RNF-1: «el runner no usa GPU, red ni API key: el corpus parte de programas DSL, no de texto, y no invoca al modelo.»

S7 — RNF-2: «el resultado es reproducible entre ejecuciones y máquinas de CI.»

S8 — RNF-3: «no cambia el comportamiento de `make check` ni del smoke existentes.»

S9 — AC1: «el job falla y nombra el caso cuyo hash del STEP divergió, con el hash esperado y el obtenido.»

S10 — AC2: «el job falla e indica el caso, el resultado esperado y el obtenido.»

S11 — AC3: «cada caso esperado como declinación está marcado explícitamente como tal, y el runner rechaza casos sin resultado esperado declarado.»

S12 — AC4: «termina con código 0 sobre el corpus sin cambios.»

S13 — Fuera de alcance: «correr las 113 pruebas internas de `constraint-kit` en CI (siguen en `make kernel-test`)», y evaluar al modelo o al prompt (SPEC-016, SPEC-045).

## Tasks

- [x] T1 — S1, S2, S11 · corpus versionado + esquema de resultado declarado · `05249b8`, `cbd2b75`
- [x] T2 — S3, S7, S9, S10 · runner que compara con lo congelado y nombra la divergencia · `05249b8`, `cbd2b75`
- [x] T3 — S4, S12 · step de CI que corre el runner en cada PR · `ab4ce3e`
- [x] T4 — S5, S6, S8, S13 · regeneración documentada y no regresión de `make check`/smoke · este commit
- [x] T5 — plan.md y tasks.md de SPEC-024 y estado en el índice de specs · este commit
- [ ] T6 — réplica del step en `.gitlab-ci.yml` cuando la PR #125 del espejo entre en `main`

## Log

L1 — Pedido original: «con que actividad de github proyecto puedo avanzar que tenga yo asignada».

L2 — Decisión del humano: avanzar la **#83 · HU-23 Corpus dorado del núcleo determinista en CI** (SPEC-024, 3 SP), elegida entre las asignadas por ser la de mayor apalancamiento: sin dependencias y desbloquea #102 (DXF) y #108 (BOM).

L3 — Hallazgo de estado: el árbol tenía un work unit de GitLab CI sin commitear sobre la PR #125 abierta. El humano autorizó commitearlo y pushearlo; quedó en `98628fb` con `tests/test_ci_parity.py` en verde y Ruff limpio, antes de ramificar la HU-23.

L4 — `origin/main` está en `80d7850` y el `main` local estaba fósil; la rama de la HU se creó desde `origin/main`.

L5 — Evidencia de la implementación: `make check` 428 passed con cobertura 92,71 % (módulo nuevo 73 %),
`make corpus-dorado` 15 casos sin divergencias, y `make help` sólo suma la línea del objetivo nuevo.
Las pruebas de AC1, AC2 y AC4 construyen piezas reales; las alteraciones deliberadas usan una copia
temporal mínima para no construir 15 piezas por prueba.

L6 — Corte de entrega: los work units quedaron en tres commits (`05249b8` módulo + runner, `cbd2b75`
corpus congelado + suite, `ab4ce3e` wiring de CI) más el de documentación. La historia completa ronda
las 950 líneas autoradas, más del slice de ~400: se entrega como una sola PR de la HU, en commits por
work unit, no como PR encadenadas.

L7 — `make check` local exige `M2_DOWNLOAD_SECRET` (HU-36) y `make frontend-install` antes; sin eso
44 pruebas fallan por entorno, no por el cambio.
