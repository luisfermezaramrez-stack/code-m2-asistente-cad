# HU-33 · Prompts versionados como artefactos

Issue #93 · SPEC-034 · 2 SP · Ola 1 · Hito M4 · Etiquetas: ML · 1 SP = 1 día.

Rama `feature/hu-33-prompts-versionados`. Specs y criterios: `specs/034-hu-33-prompts-versionados/spec.md`.

## Specs

S1 — RF-1: «los prompts se guardan como archivos versionados con id y hash de contenido.»

S2 — RF-2: «el pipeline carga el prompt desde esos archivos, no desde una cadena inline.»

S3 — RF-3: «cada solicitud registra la versión de prompt usada en el registro y en MLflow.»

S4 — RF-4: «tests del prompt versionado: el pipeline carga el prompt por id, su hash coincide
con el contenido del archivo y la versión queda en el registro.»

S5 — RF-5: «CI falla si el contenido de un prompt cambia sin cambiar su versión.»

S6 — RNF-1: «las pruebas no usan red, API key ni GPU: las respuestas del modelo se simulan.»

S7 — RNF-2: «la migración no cambia el texto del prompt actual; su primera versión es
idéntica a `PROMPT_SISTEMA`.»

S8 — RNF-3: «el registro sigue sin campos vacíos (SPEC-004, AC3).»

S9 — AC1: «**Dado** una solicitud procesada / **Cuando** se consulta su fila del registro /
**Entonces** contiene el id y el hash de la versión de prompt usada, y la corrida de MLflow
registra el mismo valor.»

S10 — AC2: «**Dado** un prompt versionado / **Cuando** se modifica su contenido sin subir su
versión / **Entonces** la verificación de CI falla.»

S11 — AC3: «**Dado** el prompt vigente guardado como archivo versionado y respuestas
simuladas del modelo / **Cuando** corren los tests de prompt / **Entonces** verifican que el
pipeline carga el prompt por su id, que el hash registrado coincide con el contenido del
archivo y que la fila del registro lleva ese id y hash.»

S12 — No regresión: «Formato JSON, familias de `CATALOGO` y rechazo fuera de catálogo ya
están cubiertos sobre el texto inline (`tests/test_pipeline.py:486-493` y `:631-638`); esas
pruebas se conservan como no regresión.»

S13 — Fuera de alcance: «Mejorar o reescribir el prompt.» / «Comparación A/B de prompts y
modelos (SPEC-053).» / «Evaluación del banco en CI (SPEC-045).»

S14 — Métricas de éxito: «100 % de las filas nuevas del registro con versión de prompt.» y
«0 cambios de prompt fusionados sin nueva versión.»

## Tasks

- [x] T1 — S1, S2, S7 · prompt vigente como archivo versionado + manifiesto con id, versión y
      sha256, y cargador único que el pipeline usa en lugar de la cadena inline.
- [x] T2 — S3, S8, S9 · columnas `prompt` y `prompt_hash` en el registro (aditivas, migradas
      como `usuario` y `causa`) y los mismos valores como params de la corrida de MLflow.
- [x] T3 — S5, S10 · chequeo de CI que falla si el contenido cambia sin subir la versión,
      enlazado en `make check` y en el pipeline espejo, con paridad vigilada.
- [x] T4 — S4, S6, S11, S12 · pruebas AAA sin red: carga por id, hash contra el archivo,
      fila del registro con id y hash, mutación en copia temporal que debe fallar.
- [x] T5 — S13, S14 · contrato del prompt estable para HU-35 documentado en `plan.md`.

## Log

L1 — Pedido original: «Nueva tarea: implementar HU-33 (issue #93) 'Prompts versionados como
artefactos'. HU-26 ya está en main (#139) y HU-28 en el PR #140: no toques esas ramas.
Fuente de requisitos: specs/034-hu-33-prompts-versionados/spec.md (AC1 trazabilidad por
fila, AC2 cambio sin versión rompe CI, AC3 tests del prompt versionado); léela completa
junto con CONSTITUTION.md y AGENTS.md. HU-35 depende de esta spec, así que deja el contrato
del prompt versionado claro y estable. Pasos: (1) git fetch origin && git switch -c
feature/hu-33-prompts-versionados origin/main. (2) Crea
odd/tasks/hu-33-prompts-versionados.md (Specs S# citando los AC literalmente, Tasks, Log con
este pedido como L1) y redacta plan.md y tasks.md en specs/034-hu-33-prompts-versionados/.
(3) Test-first: RED observado por cada AC antes de implementar, luego GREEN; pytest AAA sin
red ni GPU; las pruebas afirman cada efecto observable (salida, código de salida, datos
persistidos). (4) Reutiliza los helpers existentes: registro.py (la columna nueva se agrega
y migra con el mismo mecanismo que y ), seguimiento.py para MLflow y el pipeline actual del
prompt; no dupliques lógica. Si cambias la forma del registro CSV o el contrato /v1, dilo
explícitamente porque son formatos consumidos; si cambias /v1, regenera los tipos del
frontend. (5) Si AC2 agrega un chequeo de CI, mantén coherentes .github/workflows y
.gitlab-ci.yml (hay prueba de paridad en tests/test_ci_parity.py). (6) make check debe
pasar, exportando M2_DOWNLOAD_SECRET con al menos 32 bytes aleatorios. No muevas ni borres
archivos locales gitignored como data/registro.csv: si una prueba los necesita aislados, usa
tmp_path. (7) Commits Conventional en español tipo feat(hu-33): ..., SIN Co-Authored-By ni
atribución a IA. NO hagas push ni abras PR. Al terminar responde con: commits (hash +
mensaje), resultado de make check, evidencia por AC, archivos tocados y dudas abiertas. Si te
bloquea una decisión de producto, detente y descríbela en vez de asumir.»

L2 — Aclaración del humano al mismo pedido: «en el paso 4, la columna nueva del registro se
agrega y migra con el mismo mecanismo que las columnas usuario (HU-53) y causa (HU-26).»

L3 — Estado de partida: `origin/main` en `868d3f8` (merge del PR #139 de HU-26); la rama se
creó desde ahí. HU-28 sigue en el PR #140 y no se toca.

L4 — Contrato del prompt congelado (lo consume HU-35): `src/m2_cad/prompts.py` es el único
cargador y expone `Prompt(id, version, archivo, sha256, texto)`, `Prompt.etiqueta`
(`planner-v1`, lo que se persiste), `cargar(id=PROMPT_VIGENTE, *, raiz=None)`, `listar()`,
`verificar()`, `sha256_texto()` y `ErrorPrompt`. El manifiesto `prompts/manifest.toml`
declara id, versión, archivo, sha256, descripción y un solo `vigente = true` por id; subir
de versión es un archivo nuevo más una entrada nueva, nunca una edición en el lugar.
`prompts/planner-v1.txt` (2086 caracteres, sha256 `b64b187d…b6d3`) es byte a byte igual al
`PROMPT_SISTEMA` anterior: `pipeline.PROMPT_SISTEMA == prompts.cargar().texto` lo prueba.

L5 — Evidencia de AC3 y RNF-2: `pytest tests/test_prompts.py` carga el prompt por id
(`planner-v1`), compara el hash con el contenido del archivo, verifica que
`pipeline.PROMPT_SISTEMA` es exactamente el texto cargado, y corre el pipeline con respuestas
simuladas del modelo (sin red ni API key) afirmando la fila del registro con `planner-v1` y
su hash.

L6 — Evidencia de AC2: en una copia temporal de `prompts/` con una palabra añadida,
`python -B scripts/verify_prompts.py --raiz <copia>` sale con 1 y dice «planner-v1.txt: la
versión 1 declara sha256 b64b187d…b6d3 pero el contenido da 7fa474a8…7420; si cambiaste el
texto, crea un archivo nuevo y sube `version`». En el repositorio,
`make prompts-check` sale con 0 («1 versión(es) verificadas …, todas con su hash»). El
chequeo entra en `make check` y en el job `lint` del espejo, con paridad vigilada en
`tests/test_ci_parity.py`.

L7 — Formatos consumidos: el registro CSV pasó de 10 a 12 columnas (`prompt`, `prompt_hash`)
con migración por el mismo mecanismo que `usuario` y `causa` y valor `no aplica` cuando la
solicitud no llegó al modelo; la corrida de MLflow gana los params `prompt` y `prompt_hash`.
El contrato `/v1` no cambió: `generate_api_types.py --check` y `generate_api_contract.py
--check` pasan sin tocar los artefactos del frontend. La prueba de snapshot anterior de
HU-30 se ajustó a una cabecera prefijo real (`CAMPOS[:10]`), que es lo que siempre fue.

L8 — `make check` en verde (ver reporte del orquestador). La rama queda lista para PR; no se
hizo push ni PR.

L9 — Corte de entrega: dos commits (`403c7f1` comportamiento y pruebas, `3c27447`
documentación), ~1.157 líneas autoradas. El cambio es una sola unidad de comportamiento
—prompt como artefacto, su trazabilidad y su puerta de CI— con las pruebas y la
documentación al lado, así que se entrega como una PR de la HU, no encadenada. Push y PR
quedan a decisión del humano.

L10 — Defecto de integración encontrado al verificar el empaquetado: como el prompt se carga
al importar `m2_cad.pipeline`, la imagen Docker (que copiaba `src`, `data` y el kernel, pero
no `prompts/`) fallaba al arrancar con `ErrorPrompt: No se encontró el manifiesto de prompts`.
Corregido con `COPY prompts ./prompts` y una prueba que compara el `Dockerfile` con los
directorios que el paquete lee en tiempo de import (`tests/test_prompts.py::test_la_imagen_copia_los_artefactos_que_el_pipeline_lee_al_importar`), observada en rojo antes del
arreglo. Después del arreglo: `make check` 574 pruebas, cobertura 92,46 %.
