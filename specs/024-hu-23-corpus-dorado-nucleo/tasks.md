# SPEC-024 — Tareas del corpus dorado del núcleo determinista

- **ID**: SPEC-024 · **Tipo**: spec-first · **Historia**: HU-23 (#83) · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

Cada tarea se marca `[x]` al cerrarse, con su evidencia.

- [x] T01 — Redactar `plan.md` y `tasks.md` de la spec, con la normalización del STEP
      medida. · Depende de: —
      · Evidencia: `plan.md` §1.1, con el diff medido de dos corridas del mismo programa.
- [x] T02 — Módulo `src/m2_cad/corpus_dorado.py`: normalización, huella sha256 y esquema
      con resultado declarado obligatorio (RF-1, RF-2, AC3). · Depende de: T01
      · Evidencia: `05249b8`; esquema y normalización probados en `tests/test_corpus_dorado.py`.
- [x] T03 — Corpus versionado `data/corpus_dorado.json` con las seis familias del catálogo
      y declinaciones explícitas (RF-1, RF-2). · Depende de: T02
      · Evidencia: `cbd2b75`; 15 casos (12 aceptados, 3 declinados).
- [x] T04 — Runner `scripts/verify_corpus_dorado.py` con `--check` y `--write` (RF-3,
      RF-5). · Depende de: T03
      · Evidencia: `05249b8`; `make corpus-dorado` sale 0 con 15 casos sin divergencias.
- [x] T05 — Pruebas AC1, AC2 y AC4 sobre corpus temporales y sobre el corpus real, más
      reproducibilidad entre procesos (RNF-2). · Depende de: T04
      · Evidencia: `cbd2b75`; 15 pruebas; dos procesos distintos dan la misma huella
      (la verificación de AC4 corre el script en un proceso nuevo).
- [x] T06 — Paso de CI en cada PR, objetivo `make corpus-dorado` y script nuevo en el
      lint (RF-4, AC4). · Depende de: T05
      · Evidencia: `ab4ce3e`; `make help` sólo suma la línea del objetivo nuevo frente a
      `origin/main`, y `make lint` cubre el script nuevo.
- [x] T07 — Procedimiento de regeneración en `data/README.md`, fila de estado en
      `specs/README.md` y referencia en `CONSTITUTION.md` si cambia el proceso de
      verificación (RF-5). · Depende de: T06
      · Evidencia: sección «Corpus dorado del núcleo» en `data/README.md`, fila en §6 y
      decisión en §9 de `CONSTITUTION.md`, fila 024 de `specs/README.md`.
- [ ] T08 — Réplica del paso en `.gitlab-ci.yml` cuando la PR #125 del espejo entre en
      `main` (D7). · Depende de: PR #125 fusionada (el pipeline GitLab aún no está en `main`)
- [ ] T09 — `make check` en verde y PR hacia `main` con `Closes #83`. · Depende de: T07
      · Evidencia parcial: `make check` 428 passed, cobertura 92,71 %, con
      `M2_DOWNLOAD_SECRET` (precondición de HU-36 que CI genera). La PR queda pendiente
      de decisión: push y PR no se abren sin pedido explícito.
