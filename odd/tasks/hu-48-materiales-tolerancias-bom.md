# HU-48 · Materiales, tolerancias y BOM con costos (issue #108) — alcance B

Fuente: `specs/049-hu-48-materiales-tolerancias-bom/spec.md` y
`specs/049-hu-48-materiales-tolerancias-bom/spike.md` (commit `7761e3b`). Alcance aprobado
por el humano: **opción B** (RF-2, RF-3, RF-5; RF-4/AC4 fuera). Rama
`feature/hu-48-materiales-tolerancias-bom`, worktree
`../code-m2-asistente-cad-worktrees/hu-48-materiales-tolerancias-bom`, base `main` `6dc06f5`.

## Specs

- **S1** — «Alcance aprobado por el humano para HU-48: opción B (reducido). Implementa RF-2
  (material explícito), RF-3 (BOM con costos) y RF-5 (guard de material); RF-4/AC4 quedan
  fuera, y debes dejarlo registrado en spec.md/plan.md como decisión del spike (AC1).»
- **S2** — «Para AC2 usa la ruta que recomendaste: pre-agrupar en M2 y escribir el CSV en M2,
  sin parchear bom.py.»
- **S3** — «Guard: la lista canónica son los 8 materiales del prompt; 'al' se acepta como
  alias y se normaliza a 'aluminum'; iron, petg, titanium y cualquier otro declinan con un
  motivo que nombra el material.»
- **S4** — «Sigue la FASE 2 del encargo original: plan.md + tasks.md, test-first con RED
  observado, RNF-1/2/3, tabla de precios versionada, docs y specs/README.md,
  M2_DOWNLOAD_SECRET exportado antes de make check, Conventional Commits hu-48 sin
  atribución, sin push ni PR.»
- **S5** — Del encargo original: «Cubre AC2 (columna material, masa con DENSITY_G_MM3, costo
  por línea y total), AC3 (declinar "titanium"/"iron" con un motivo que nombre el material) y
  AC4 solo si el alcance aprobado lo incluye.» / «RNF-3: extiende el CSV sin romper a sus
  consumidores. Busca quién lo lee (API, frontend, banco, tests) y añade una prueba que fije
  el comportamiento previo.» / «RNF-2: el corpus dorado de SPEC-024 debe seguir verde.» /
  «La tabla de precios por material es un archivo versionado en el repo y configurable.»
- **S6** — Del encargo original: «Las pruebas no usan red, API key ni GPU; el LLM se simula
  (RNF-1).»
- **S7** — Del encargo original: «Si necesitas un paquete que no esté en uv.lock, detente y
  avisa.»

## Tasks

- **T1** — Recon de los puntos de integración (guard, declinación, CSV, consumidores) y
  `plan.md` + `tasks.md`. (commit: docs)
- **T2** — Tabla de precios versionada + módulo `precios.py` (recarga determinista, sin red),
  con su prueba en RED primero. (commit 1)
- **T3** — Guard de material con alias `al`→`aluminum` y declinación que nombra el material,
  RED primero. (commit 1)
- **T4** — CSV extendido (material, costo por línea y total) pre-agregado en M2, con prueba
  que fija el comportamiento previo de las cuatro columnas. (commit 2)
- **T5** — Corpus dorado y suite completa verdes; `make check`.
- **T6** — Documentación: `spec.md` (decisión del spike), `plan.md`, `tasks.md`,
  `specs/README.md`, `CONSTITUTION.md` si cambia algo y `evidence.md`. (commit 3)

## Log

- **L1** (petición original, literal): «Nuevo encargo: implementar HU-48 · Materiales,
  tolerancias y BOM con costos (issue #108, SPEC-049). … FASE 1 — Spike (RF-1 / AC1). Es
  obligatoria y va primero: documenta en specs/049-hu-48-materiales-tolerancias-bom/spike.md
  qué soporta el constraint-kit vendoreado en materiales (DENSITY_G_MM3, MATERIAL_STRENGTH),
  BOM (bom.py) y tolerancias (iso286.py, tolerance.py, dsl.py). Responde con evidencia
  (archivo:línea) si RF-4/AC4 (tolerancias por cota) es viable sin parchear el kit, o cuánto
  costaría el parche en scripts/vendor-constraint-kit.sh. Cierra con una recomendación de
  alcance: (A) alcance completo con RF-4, o (B) alcance reducido: material explícito, guard de
  material y BOM con costos (RF-2, RF-3, RF-5). … FASE 2 — Implementación (solo tras la
  aprobación del alcance): redacta plan.md y tasks.md; resuelve la decisión de AC2
  (pre-agrupar en _resumen_materiales y escribir el CSV en M2, o parchear bom.py) y
  justifícala; test-first con RED observado; cubre AC2, AC3 y AC4 solo si el alcance lo
  incluye; RNF-3 extendiendo el CSV sin romper consumidores con prueba que fije el
  comportamiento previo; RNF-2 corpus dorado verde; tabla de precios versionada y
  configurable; actualiza specs/README.md, documentación y CONSTITUTION.md si cambia la
  arquitectura. Reglas: exporta M2_DOWNLOAD_SECRET antes de make check; si necesitas un
  paquete fuera de uv.lock, detente y avisa; Conventional Commits con alcance hu-48 en
  español y sin atribución a IA; commits por unidad de trabajo; NO hagas push ni abras PR; al
  terminar reporta commits, resultado de make check y la línea Risk.»
- **L2** (spike, `7761e3b`): RF-4 exige parche de 130-200 líneas en el kit sin verificación
  de aplicación; el verificador no extrae cotas. Recomendación B.
- **L3** (aprobación humana, literal): «Alcance aprobado por el humano para HU-48: opción B
  (reducido). Implementa RF-2 (material explícito), RF-3 (BOM con costos) y RF-5 (guard de
  material); RF-4/AC4 quedan fuera, y debes dejarlo registrado en spec.md/plan.md como
  decisión del spike (AC1). Para AC2 usa la ruta que recomendaste: pre-agrupar en M2 y
  escribir el CSV en M2, sin parchear bom.py. Guard: la lista canónica son los 8 materiales
  del prompt; 'al' se acepta como alias y se normaliza a 'aluminum'; iron, petg, titanium y
  cualquier otro declinan con un motivo que nombra el material. Sigue la FASE 2 del encargo
  original: plan.md + tasks.md, test-first con RED observado, RNF-1/2/3, tabla de precios
  versionada, docs y specs/README.md, M2_DOWNLOAD_SECRET exportado antes de make check,
  Conventional Commits hu-48 sin atribución, sin push ni PR. Al terminar reporta commits,
  resultado de make check y línea Risk.»
- **L4** (implementación, commits): `0191629` `feat(hu-48)` tabla + módulo + `materiales-check`
  + guarda de paridad (≈498 líneas autoradas; frontera de rebanada tras este commit);
  `17076f9` `feat(hu-48)` guard + CSV con material y costo (≈300 líneas);
  `b206273` `docs(hu-48)` spec/plan/tasks/evidence + README/CONSTITUTION/specs-README.
  Total 1260 líneas autoradas en 4 commits (incluye el spike `7761e3b`).
- **L5** (resultados observados): RED inicial con `ImportError: cannot import name 'materiales'`
  en la colección de las dos suites nuevas; después `pytest tests/test_materiales.py
  tests/test_hu48_materiales_bom.py` → 45 aprobadas; `make materiales-check` → 8 materiales;
  `make corpus-dorado` → «15 casos sin divergencias»; `make check` → 848 pytest aprobadas,
  cobertura 90,97 %, Vitest 117. Trampas encontradas: `M2_DOWNLOAD_SECRET` de prueba demasiado
  corto (<32 bytes) hacía fallar 48 pruebas de descargas, y `mkdocs build --strict` exige que
  exista el `evidence.md` enlazado antes de pasar. No se hizo push ni PR (lo pedía el encargo).
