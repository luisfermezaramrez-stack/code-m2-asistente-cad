# HU-28 · Escaneo de dependencias y secretos en CI

Issue #88 · SPEC-029 · 1 SP · Ola 0 · Hito M4 · Etiquetas: infra, Testing · 1 SP = 1 día.

Rama `feature/hu-28-escaneo-seguridad`. Specs y criterios: `specs/029-hu-28-escaneo-seguridad/spec.md`.

## Specs

S1 — RF-1: «un job de CI con `pip-audit` sobre las dependencias Python bloqueadas en
`uv.lock`.»

S2 — RF-2: «un job de CI con `gitleaks` sobre los cambios de la PR.»

S3 — RF-3: «ambos jobs fallan ante un hallazgo de severidad alta (CVE) o un secreto, y el
mensaje indica el paso exacto a seguir (actualizar la dependencia, rotar y retirar la
clave, o registrar una excepción).»

S4 — RF-4: «una política de excepciones documentada: dónde se declaran, quién las aprueba,
justificación obligatoria y fecha de revisión.»

S5 — RNF-1: «los jobs no requieren secretos del repositorio para ejecutarse.»

S6 — RNF-2: «las versiones de las herramientas quedan fijadas.»

S7 — RNF-3: «la gestión de dependencias Python sigue pasando por `uv` (sin `pip` ni
`requirements.txt` versionado).»

S8 — AC1: «**Dado** una PR que agrega una cadena con forma de API key / **Cuando** corre CI
/ **Entonces** el job de secretos falla, señala archivo y línea, e indica el paso exacto:
rotar la clave, retirarla del historial o declarar una excepción justificada.»

S9 — AC2: «**Dado** una PR que fija una dependencia Python con un CVE de severidad alta /
**Cuando** corre CI / **Entonces** el job de dependencias falla, nombra el paquete, el CVE
y la versión corregida, e indica el comando para actualizarla.»

S10 — AC3: «**Dado** un hallazgo aceptado conforme a la política / **Cuando** se registra
como excepción con justificación y fecha de revisión / **Entonces** el job pasa y la
excepción queda visible en el repositorio.»

S11 — Fuera de alcance: «Análisis estático de código (SAST) o escaneo de imágenes Docker.»
y el endurecimiento de descargas y artefactos (SPEC-037).

S12 — Métricas de éxito: «Secretos y CVE altos fusionados en `develop`: 0.» y «Excepciones
sin justificación o vencidas: 0.»

S13 — Supuestos: «`pip-audit` recibe la lista exportada desde `uv.lock` en el propio job,
sin versionar ningún `requirements.txt`.» y «el escaneo de dependencias npm queda fuera».

## Tasks

- [x] T1 — S1, S3, S9, S13 · módulo `seguridad_ci.py`: clasifica la auditoría de
      dependencias, arma el mensaje con paquete, CVE, versión corregida y comando de
      actualización.
- [x] T2 — S2, S3, S8 · escaneo de secretos con gitleaks fijado y mensaje con archivo,
      línea y los tres pasos permitidos.
- [x] T3 — S4, S10, S12 · política de excepciones documentada y validada (justificación,
      aprobador y fecha de revisión vigente); excepciones visibles en el repositorio.
- [x] T4 — S1, S2, S5, S6, S7 · jobs en GitHub Actions y en el pipeline espejo de GitLab,
      con versiones exactas y todo lo de Python por `uv`; paridad vigilada por prueba.
- [x] T5 — S11 · evidencia local de los dos casos (falla y pasa) registrada en el Log, sin
      silenciar hallazgos reales de `main`.

## Log

L1 — Pedido original: «Nueva tarea: implementar HU-28 (issue #88) 'Escaneo de dependencias
y secretos en CI'. HU-26 ya está en el PR #139; no toques esa rama. Fuente de requisitos:
specs/029-hu-28-escaneo-seguridad/spec.md (AC1 secreto commiteado, AC2 CVE alto, AC3
excepción documentada); léela completa junto con CONSTITUTION.md y AGENTS.md. Pasos: (1)
git fetch origin && git switch -c feature/hu-28-escaneo-seguridad origin/main. (2) Crea
odd/tasks/hu-28-escaneo-seguridad.md (Specs S# citando los AC literalmente, Tasks, Log con
este pedido como L1) y redacta plan.md y tasks.md en specs/029-hu-28-escaneo-seguridad/.
(3) Es un cambio de CI (riesgo alto, item 5): el workflow de GitHub Actions y el pipeline
espejo de GitLab (.gitlab-ci.yml, PR #134) deben quedar coherentes; fija versiones exactas
de acciones y herramientas, todo lo de Python pasa por uv (prohibido pip), y no metas
secretos reales en el repo: para probar AC1 usa fixtures con secretos falsos excluidos del
escaneo de forma explícita y documentada. (4) Demuestra cada AC con evidencia observable:
corre localmente los escáneres sobre un caso que debe fallar (secreto falso / dependencia
con CVE alto) y otro que debe pasar, y registra la salida en el Log. Verifica que el estado
actual de main pase el escaneo; si aparecen hallazgos reales en main, NO los silencies sin
más: documéntalos y detente a preguntarme. (5) make check debe pasar. Actualiza
CONSTITUTION.md si cambia el proceso de CI. (6) Commits Conventional en español tipo
ci(hu-28): ... o feat(hu-28): ..., SIN Co-Authored-By ni atribución a IA. NO hagas push ni
abras PR. Al terminar responde con: commits (hash + mensaje), resultado de make check,
evidencia de cada AC, archivos tocados y dudas abiertas. Si te bloquea una decisión de
producto, detente y descríbela.»

L2 — Herramientas fijadas y alcance decidido: gitleaks `8.30.1` (asset linux_x64 y su
sha256 fijados en `src/m2_cad/seguridad_ci.py`) y `pip-audit 2.10.1` (`uvx --from
pip-audit==2.10.1`); uv sigue en `0.13.5`. El escaneo es un objetivo propio (`make
security`) fuera de `make check` porque necesita red, igual que `make corpus-dorado`. El
escaneo de npm y el hook de pre-commit quedan fuera (S11): la especificación pide jobs de CI.

L3 — Estado de `main` medido el 27/11 sobre `4f689ed` con las herramientas fijadas.
Secretos: gitleaks sobre 189 commits → **0 hallazgos**, `main` pasa AC1. Dependencias:
`pip-audit` sobre el export de `uv.lock` (148 paquetes) → 46 advisories en 3 paquetes, y
`main` **no pasa**: `pillow 12.3.0` (42 advisories, varias de severidad **crítica**,
corrección `13.0.0`), `vtk 9.3.1` (3 advisories críticos, corrección `9.5.1`) y `diskcache
5.6.3` (`CVE-2025-69872`, sin corrección y sin severidad publicada). No se aprueba ninguna
excepción: `security/excepciones-*.toml` se entregan vacíos y la decisión queda para quien
aprueba excepciones según la política. `uv lock --upgrade-package pillow --dry-run`
resuelve `12.3.0 → 13.0.0` sin conflicto.

L4 — Evidencia de AC1 (secreto). Caso que falla: commit temporal con el fixture en
`docs/prueba-secreto-falso.env` → `make security-secretos` sale con 1 y el mensaje dice
`docs/prueba-secreto-falso.env:2 · regla generic-api-key · BLOQUEANTE`, el commit, y los
tres pasos permitidos (rotar, retirar del historial con `git filter-repo`, declarar
excepción justificada). Commit temporal revertido con `git reset --mixed` y archivo
borrado. Caso que pasa: mismo comando sobre el repositorio → «no leaks found», `RESULTADO:
escaneo de secretos superado`. El fixture se detecta con las reglas por defecto
(`gitleaks dir tests/fixtures/seguridad`) y sólo se excluye por la allowlist documentada de
`.gitleaks.toml`.

L5 — Evidencia de AC2 (dependencia con CVE alto). Fixture
`tests/fixtures/seguridad/dependencias-vulnerables.txt` (`jinja2==2.11.2`):
`- jinja2 2.11.2 · CVE-2024-56326 (PYSEC-2026-1475) · severidad alta · corrección: 3.1.5`
y `Acción: uv lock --upgrade-package jinja2 && uv add "jinja2>=3.1.5"`, `RESULTADO: 5
hallazgos bloqueantes — el job falla (RF-3)`, exit 1. Caso que pasa: el repositorio sin
excepciones no pasa (L3); con una excepción vigente el mismo comando sobre un fixture de un
solo advisory pasa (L6).

L6 — Evidencia de AC3 (excepción documentada), con `pyyaml==5.3.1`
(`CVE-2020-14343`, corrección 5.4). Sin excepción: exit 1, 1 hallazgo bloqueante. Con una
excepción de revisión vigente (2026-12-31), aprobador y justificación: `validar` → OK y el
escaneo → exit 0 con la línea `excepción vigente: revisión 2026-12-31 · aprobada por … ·
justificación: …` y `RESULTADO: auditoría de dependencias superada`. Con la revisión puesta
en el pasado (2025-01-01): `validar` falla con «`revision` vencida» y el escaneo vuelve a
bloquear nombrando la excepción vencida. La excepción de prueba se retiró de
`security/excepciones-dependencias.toml` (queda con 0 entradas).

L7 — Corrección detectada en la integración: `uv export --locked` exige la fuente local del
kernel (`vendor/constraint-kit`) para generar metadatos, así que los jobs `dependencias` de
GitHub y del espejo hacen el vendor antes de auditar; el job de secretos no lo necesita.

L8 — Corte de entrega: un solo work unit de ~2.240 líneas autoradas porque las dos puertas,
su política, los fixtures y las pruebas comparten interfaz y viajan juntas; se entrega como
una PR de la HU, no encadenada. `make check` en verde con 567 pruebas y cobertura 91,79 %;
`make security` queda fuera de `make check` por necesitar red.

L9 — Nota de entorno: la corrida de `make check` heredó un `data/registro.csv` local de la
sesión de HU-26 (10 columnas con `causa`, gitignored) que este árbol no entiende y rompía
`tests/test_web.py`. No era un defecto del cambio: se movió a `/tmp/hu28-registro-local.csv`
como respaldo y la suite volvió a verde.

L10 — 2026-11-26, decisión del usuario sobre el estado de `main` (respondida en el agente):
subir `pillow` a 13.0.0 y exceptuar `vtk` 9.3.1 (fijado por `cadquery-ocp 7.8.1.1.post1`,
`Requires-Dist: vtk==9.3.1`) y `diskcache` 5.6.3 (sin corrección publicada). Corpus dorado
con `pillow` 13: 16/16.

L11 — Verificación independiente (orquestador, solo lectura). Bloqueos encontrados y
corregidos en una tanda, con RED observado (4 fallos) → GREEN:
B1, el job `secretos` del espejo GitLab no instalaba `git` y `gitleaks git` fallaba siempre,
cortando las etapas posteriores → instala `make git`; B2, ningún pipeline corría la
validación de la política, así que una excepción incompleta desbloqueaba un hallazgo →
`security-secretos` y `security-dependencias` dependen de `security-excepciones-validar`;
B3, gitleaks sale con 1 aunque una excepción vigente cubra el hallazgo y el script lo
convertía en exit 2 (y escribía «superado» ante un fallo de la herramienta) → 0/1 se
interpretan y el fallo nunca se declara superado; B4, las pruebas exigían archivos vacíos,
la política decía «sin excepciones» y la justificación de `diskcache` la atribuía a mlflow:
llega por `llama-cpp-python`, que solo la usa en `LlamaDiskCache`, no habilitada en `src/`.
Quedan como notas: gitleaks escanea todas las ramas descargadas (N1) y no hay disparador
programado para CVE publicados después del merge (N5).

L12 — 2026-11-26, decisión del usuario sobre quién firma, literal: «todos podemos firmar
con una firma puede ser suficiente y sera elmismo que apruebe el PR». La política (§2) pasa
a una sola firma de cualquier integrante, que es quien aprueba el PR; `aprobado_por` remite
a esa aprobación. Cierre: `make check` 572 pruebas, cobertura 92,07 %; `make security` en
verde (sin secretos; dependencias sin hallazgos bloqueantes).

L13 — 2026-11-26, el push fue rechazado por la protección de push de GitHub: el fixture
`secreto-falso.env` usaba un valor con forma de clave de DeepSeek (`sk-` + 32). Decisión del
usuario, literal: «2» (reescribir el fixture en vez de desbloquearlo en GitHub). Se reemplazó
por `M2_FIXTURE_API_KEY` con 40 caracteres alfanuméricos aleatorios, sin prefijo de
proveedor; `gitleaks 8.30.1 dir` con reglas por defecto lo detecta como `generic-api-key` en
la línea 2 (exit 1). Se ajustó `gitleaks-hallazgo.json` y se reescribió la historia local
no publicada para que ningún commit contenga el valor anterior.
