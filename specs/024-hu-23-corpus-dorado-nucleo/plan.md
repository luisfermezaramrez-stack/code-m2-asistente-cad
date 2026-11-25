# SPEC-024 — Plan del corpus dorado del núcleo determinista

- **ID**: SPEC-024 · **Tipo**: spec-first · **Historia**: HU-23 (#83) · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

| Archivo | Cambio | AC |
| --- | --- | --- |
| `src/m2_cad/corpus_dorado.py` | Nuevo: normalización del STEP, huella sha256, esquema del corpus y comparación | RF-1..RF-4, AC1–AC3 |
| `data/corpus_dorado.json` | Nuevo: corpus congelado (pares programa → resultado) | RF-1, RF-2 |
| `scripts/verify_corpus_dorado.py` | Nuevo: runner CLI: verifica por defecto y `--write` regenera | RF-3, RF-5, AC4 |
| `tests/test_corpus_dorado.py` | Nuevo: normalización, esquema, divergencias y corpus real en verde | AC1–AC4 |
| `.github/workflows/ci.yml` | Paso nuevo después de `make check`, antes del arranque HU-15 | RF-4, AC4 |
| `Makefile` | Objetivo `corpus-dorado`; el script nuevo entra en la lista de `lint` | RF-4, RNF-3 |
| `data/README.md`, `specs/README.md` | Contrato del corpus y estado de la spec | RF-5 |

### 1.1 Normalización del STEP: lo que se midió, no lo que se supuso

La spec deja como supuesto que el STEP lleva campos variables y que el método se fija
aquí. Se midió construyendo el mismo programa dos veces en procesos separados
(`spacer` y `plate`): el STEP difiere **sólo** en tres tokens, seis líneas en total.

| Variación entre corridas | Corrida A | Corrida B | Normalización |
| --- | --- | --- | --- |
| Marca de tiempo de `FILE_NAME` | `'2026-11-24T23:09:10'` | otra hora | `<marca-tiempo>` |
| GUID del `PRODUCT` de cada parte | `f79bcf46-e885-11f1-…` | `f7a2cda1-e885-11f1-…` | `<guid>` |
| Primer argumento de `NEXT_ASSEMBLY_USAGE_OCCURRENCE` | `'1'` | `'2'` | `'<ocurrencia>'` |

El tercero es un contador que avanza por cada ensamblaje construido en el mismo proceso:
depende del orden de la corrida, no del programa. El resto del archivo —coordenadas,
tolerancias, número y tipo de entidades— fue idéntico byte a byte, así que **la
normalización es mínima a propósito**: cualquier divergencia geométrica, incluso por debajo
de la tolerancia de ±2 % del test actual, sigue cambiando el hash.

La huella es `sha256` sobre el texto normalizado, con saltos de línea normalizados a `\n`.

### 1.2 Esquema del corpus

`data/corpus_dorado.json`:

```json
{
  "version": 1,
  "casos": [
    {"id": "acepta-plate-40-30-5", "fuente": "HU02-P01", "resultado": "acepta", "sha256": "…"},
    {"id": "declina-fuera-catalogo", "programa": {"unsupported": "…"}, "resultado": "declina"}
  ]
}
```

Reglas, aplicadas por `corpus_dorado.cargar_corpus` y probadas una por una:

- `resultado` es obligatorio y sólo admite `acepta` o `declina`; **un caso sin resultado
  declarado es un error del corpus, no un caso aceptado** (RF-2, AC3).
- Un caso tiene `fuente` (fila del banco HU-02, de donde se deriva el programa) **o**
  `programa` explícito, nunca ambos ni ninguno. Una fila negativa del banco no tiene
  programa: citarla sin `programa` es un error con mensaje propio. Las declinaciones del
  corpus versionado usan `programa` explícito (D4), pero el esquema no prohíbe declarar
  `declina` sobre un caso con `fuente`: AC2 invierte el resultado de casos existentes.
- `sha256` es obligatorio y hexadecimal de 64 caracteres cuando `resultado` es `acepta`;
  prohibido cuando es `declina`. En modo de regeneración (`--write`) basta el resultado
  declarado: un caso nuevo se agrega sin huella y se congela después (RF-5).
- `id` único; claves desconocidas rechazadas; `version` obligatorio igual a `1`.

### 1.3 Runner

`scripts/verify_corpus_dorado.py` recorre los casos con `pipeline.construir_pieza` (que ya
llama a `verificar_programa`) en un directorio temporal por caso:

- `PiezaDeclinada` en un caso `acepta`, o una pieza construida en un caso `declina`, es
  divergencia de aceptación (AC2).
- Una huella distinta es divergencia de hash; el mensaje nombra el caso y da esperado y
  obtenido (AC1).
- `ErrorVerificacion` es un error del corpus, no una divergencia: un programa inválido no
  puede congelarse (RF-2).
- Sale 0 sin divergencias y 1 con cualquier divergencia; `--write` regenera el corpus.

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| D1: los casos aceptados derivan su programa de una fila del banco (`fuente`) en vez de repetir literales | La forma válida de cada familia (sobre todo `flange`, con `nps`/`flange_class`/`kind`) y sus parámetros ya viven auditados en `data/test_cases.csv`; duplicar 12 literales abriría una deriva silenciosa entre banco y corpus. Costo aceptado: cambiar una fila del banco obliga a regenerar el corpus, y esa regeneración queda visible en el diff (RF-5). |
| D2: normalizar sólo los tres tokens medidos | Menos normalización es más detección: los supuestos de la spec sobre campos variables quedaron medidos, no adivinados. |
| D3: la lógica vive en `src/m2_cad/corpus_dorado.py` y el CLI en `scripts/` | El runner queda cubierto por pytest y Ruff sin invocar el script; el CLI aporta el `--write` documentado. |
| D4: el corpus vive en `data/` y las declinaciones llevan `programa` explícito | `data/` es donde el proyecto versiona artefactos con contrato propio; las filas negativas del banco no tienen parámetros de los que derivar un programa. |
| D5: `make check` no toca el corpus; el corpus corre en un paso propio del job | RNF-3. El paso también existe como objetivo `make corpus-dorado` para reproducirlo en local. |
| D6: el script nuevo entra en la lista del objetivo `lint` | Un script nuevo sin lint es una excepción silenciosa al estándar; la lista de `lint` es aditiva y no cambia lo que ya verificaba. |
| D7: el paso equivalente en `.gitlab-ci.yml` se agrega cuando la PR #125 entre en `main` | El pipeline del espejo GitLab todavía no está en `main`; replicarlo aquí lo duplicaría en otra rama. Queda registrado en `tasks.md` como tarea abierta del espejo. |

## 3. Comandos

```bash
# Verificar el corpus (lo que corre CI)
make corpus-dorado

# Regenerar tras un cambio geométrico intencional (queda visible en el diff)
uv run --no-sync python -B scripts/verify_corpus_dorado.py --write

# Verificación completa de la historia
make check
```

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Regenerar el corpus para "arreglar" CI tras una divergencia real | `--write` exige que cada caso aceptado vuelva a construirse; el diff muestra el hash viejo y el nuevo, y la revisión de la PR debe justificar el cambio geométrico. |
| El corpus se acopla al banco y una fila nueva rompe CI | Decisión D1 explícita: la regeneración es parte del procedimiento, y el caso roto nombra la fila del banco. |
| Costo del paso en CI | Se midió: piezas del catálogo entre 0,05 s y 0,12 s; 15 casos ≈ 2 s. |
| Un caso de declinación que `validar_catalogo` declinaría pero `verificar_programa` acepta | El corpus usa formas `{"unsupported": …}`, que el verificador declina; un ensamblaje de varias piezas no se usa como caso de declinación. |

## 5. Verificación

| AC | Prueba |
| --- | --- |
| AC1 | Corpus temporal con un hash alterado → el runner nombra el caso con esperado y obtenido |
| AC2 | Corpus temporal con un resultado invertido → el runner nombra el caso, esperado y obtenido |
| AC3 | Caso sin `resultado`, `resultado` desconocido y `sha256` ausente → rechazados por `cargar_corpus` |
| AC4 | `make corpus-dorado` sobre el corpus versionado sale 0 sin GPU, red ni API key |
| RNF-2 | Dos corridas del mismo programa en procesos distintos dan la misma huella |
| RNF-3 | `make check` en verde con las mismas verificaciones de antes |
