# SPEC-024 · HU-23 — Corpus dorado del núcleo determinista en CI

- **ID**: SPEC-024
- **Historia**: #83 (HU-23) · 3 SP · Etiquetas: Testing, ML · Hito: M4
- **Planificación**: Ola 0 · Tamaño M · Épica: Calidad
- **Responsable**: Luis Fernando Meza
- **Depende de**: —
- **Rama**: `feature/hu-23-corpus-dorado-nucleo`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

El núcleo determinista (DSL → verificación → STEP) es la parte del sistema que más
justifica la etiqueta "profesional". CI ya construye piezas reales, pero sólo las compara
contra tolerancias amplias y no contra resultados congelados:

1. `make kernel-test` corre las 113 pruebas de `constraint-kit` sólo dentro del
   contenedor del autor `cadkit:0.1` (`Makefile:29-33`); ningún workflow lo invoca.
2. `tests/test_pipeline.py` construye piezas reales en CI y compara volumen y caja
   envolvente contra el valor esperado con tolerancia ±2 %
   (`tests/test_pipeline.py:106-130,219-227`), y el smoke de `.github/workflows/ci.yml:55`
   arranca el servicio con CAD real. Ninguno compara la geometría producida contra
   resultados congelados por hash.
3. `pipeline.verificar_programa` (`src/m2_cad/pipeline.py:200-219`) y
   `pipeline.construir_pieza` (`src/m2_cad/pipeline.py:281-311`) dependen de
   `dsl.check` y de `builder` del `constraint-kit` vendoreado y parcheado
   (`make vendor`). Un cambio en el parche o en la versión fijada que altere una pieza
   por debajo del 2 % de volumen o caja pasa inadvertido.

El hueco real es, por tanto, la ausencia de resultados congelados por hash: una
divergencia geométrica inferior a la tolerancia actual no se detecta.

## Historia de usuario

**Como** responsable del núcleo, **quiero** un corpus dorado de programas DSL con su
resultado esperado congelado y verificado en cada PR, **para** que cualquier divergencia
geométrica del núcleo se detecte en CI y no en una pieza entregada.

## Requisitos

### Funcionales

- **RF-1**: un corpus versionado de pares *programa DSL → resultado esperado*, donde el
  resultado es `acepta` con el hash del STEP o `declina`.
- **RF-2**: el corpus declara de forma explícita qué casos se esperan como declinación;
  un caso sin resultado declarado es un error del corpus, no un caso aceptado.
- **RF-3**: un runner recorre el corpus a través de `verificar_programa` y
  `construir_pieza`, y compara cada resultado con el congelado.
- **RF-4**: un job de CI ejecuta el runner en cada PR y falla ante cualquier divergencia
  (aceptación ↔ declinación, o hash distinto), indicando el caso y la diferencia.
- **RF-5**: un procedimiento documentado regenera el corpus cuando un cambio geométrico es
  intencional, de modo que la actualización quede visible en el diff de la PR.

### No funcionales

- **RNF-1**: el runner no usa GPU, red ni API key: el corpus parte de programas DSL, no de
  texto, y no invoca al modelo.
- **RNF-2**: el resultado es reproducible entre ejecuciones y máquinas de CI.
- **RNF-3**: no cambia el comportamiento de `make check` ni del smoke existentes.

> **Supuesto**: el STEP exportado incluye en su cabecera datos variables (por ejemplo la
> fecha en `FILE_NAME`); el hash se calcula sobre un contenido normalizado que excluye esos
> campos. El método exacto se fija en `plan.md`.

> **Supuesto**: el job de CI usa el mismo entorno de `uv sync --locked` y el
> `constraint-kit` vendoreado que ya prepara `ci.yml`, sin el contenedor del autor.

## Criterios de aceptación

### AC1 — Divergencia de hash rompe CI

- **Dado** el corpus dorado congelado y un caso aceptado cuyo hash esperado se altera a
  propósito en la definición del corpus
- **Cuando** se ejecuta el job de CI del corpus
- **Entonces** el job falla y nombra el caso cuyo hash del STEP divergió, con el hash
  esperado y el obtenido.

### AC2 — Divergencia de aceptación rompe CI

- **Dado** el corpus dorado congelado y un caso cuyo resultado esperado se invierte a
  propósito (de `acepta` a `declina`, o a la inversa)
- **Cuando** se ejecuta el job de CI del corpus
- **Entonces** el job falla e indica el caso, el resultado esperado y el obtenido.

> **Supuesto**: la alteración deliberada de AC1 y AC2 se prueba con un corpus de prueba
> o una copia temporal, sin modificar `constraint-kit` ni `dsl.check` dentro de la PR.

### AC3 — Declinaciones explícitas

- **Dado** el corpus dorado
- **Cuando** se inspecciona su definición
- **Entonces** cada caso esperado como declinación está marcado explícitamente como tal, y
  el runner rechaza casos sin resultado esperado declarado.

### AC4 — Sin GPU ni red

- **Dado** un runner de CI sin GPU, sin red hacia el proveedor y sin API key
- **Cuando** se ejecuta el job del corpus
- **Entonces** termina con código 0 sobre el corpus sin cambios.

## Fuera de alcance

- Correr las 113 pruebas internas de `constraint-kit` en CI (siguen en `make kernel-test`).
- Evaluar al modelo o al prompt: eso es el banco (SPEC-016) y su versión en CI,
  [SPEC-045](../045-hu-44-banco-ci-replay/spec.md).
- Ampliar el catálogo de familias o tocar tolerancias
  ([SPEC-049](../049-hu-48-materiales-tolerancias-bom/spec.md)).

## Métricas de éxito

- Divergencias geométricas no intencionales detectadas en CI antes de fusionar: 100 %.
- Falsos positivos del job (fallos sin cambio geométrico real): 0.
- Duración del job compatible con correr en cada PR.
