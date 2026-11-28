# Spike · HU-48 (SPEC-049) — qué soporta el `constraint-kit` vendoreado

**Fecha:** 27 de noviembre de 2026 · **Issue:** #108 · **Spec:** SPEC-049 (RF-1, AC1)
**Rama:** `feature/hu-48-materiales-tolerancias-bom` (desde `main` `6dc06f5`)
**Kit vendoreado:** revisión `2ed27db4d8fa821afef41103f0efc9befbf116e6` (`scripts/vendor-constraint-kit.sh:10`), restaurado con `make vendor` en el worktree.

## 1. Método

Lectura directa del kit y del pipeline de M2, más **sondas ejecutadas** con
`uv run --no-sync python` sobre el kit vendoreado: sin red, sin API key y sin GPU
(RNF-1). Se armó a mano un programa DSL (no hay LLM en el camino) y se imprimieron los
diagnósticos del verificador, el reporte de partes y el CSV del BOM.

**Corrección al contexto de `spec.md`** (las líneas quedaron desfasadas): la lista de
materiales no está en `src/m2_cad/pipeline.py:68-69`, sino en el artefacto de prompt
`prompts/planner-v1.txt:1`, cargado en `pipeline.py:74` (`PROMPT_VIGENTE =
prompts.cargar()`); `_resumen_materiales` vive en `pipeline.py:300-309`; el CSV se escribe
en `pipeline.py:322-328`. `dsl._check_part` sí está donde decía la spec: `dsl.py:128-142`.

## 2. Materiales

| Qué | Dónde | Contenido |
| --- | --- | --- |
| Densidades | `constraint_kit/parts.py:17-22` | `DENSITY_G_MM3` en **g/mm³**, 11 claves: `steel, stainless, iron, aluminum, al, brass, copper, abs, pla, petg, nylon` |
| Resistencia y módulo | `constraint_kit/rules.py:46-59` | `MATERIAL_STRENGTH`, 19 claves (`aluminium`, `6061`, `titanium`, `ti-6al-4v`, `pom`, `delrin`, …); `copper` **no** está |
| Tercera tabla | `constraint_kit/spec_compiler.py:90-93` | `PRESEED_MATERIALS`, en **g/cm³** (otra unidad y otro vocabulario) |
| Costos | — | no existe tabla de precios ni costos (`grep -i "cost\|price\|usd\|eur"` en `constraint_kit/` solo devuelve prosa) |

Cómo se usa el material al construir: `builder.py:320` —

```python
density = DENSITY_G_MM3.get(p["material"].lower(), DENSITY_G_MM3["steel"])
```

y el reporte conserva la etiqueta pedida (`builder.py:321-323`). El mismo respaldo
silencioso aparece en `assembly.py:79-80`, `massprops.py:26` y `construct.py:174-175`;
en cambio `rules.beam_bending` sí distingue material desconocido (`rules.py:73-76`,
devuelve `ok: None`). Son **dos políticas distintas** dentro del mismo kit.

**Sonda.** `plate` de 100 × 50 × 5 mm:

- con `material: "aluminum"` → `dsl.validate(...) == []` y masa con la densidad del aluminio;
- con `material: "titanium"` → **también `dsl.validate(...) == []`**, construye y reporta
  `{"type": "plate", "material": "titanium", "mass_g": 197.83}`: la masa sale de la
  densidad de respaldo (acero), no de la del titanio, y nadie avisa. Esto confirma el
  supuesto de AC3.

## 3. BOM

`constraint_kit/bom.py` es **solo formateo** sobre el roll-up de la jerarquía
(`bom.py:1-5`): no recalcula geometría y no conoce material ni costos. `bom_document(result,
fmt="md")` (`bom.py:21`) agrupa por **`part_type`** (`bom.py:12-18`) y las columnas CSV son
exactamente (`bom.py:31-35`):

```
part_type,qty,total_mass_g,unit_mass_g
<TIPO>,<qty>,<masa total>,<masa unitaria>
<TOTAL vacío>,<part_count>,<masa total>,
```

El test del kit fija esa cabecera: `vendor/constraint-kit/tests/test_kernel.py:2002`
(`test_bom_document`).

**Sonda** (una `plate` con `material: "titanium"`):

```
part_type,qty,total_mass_g,unit_mass_g
plate,1,197.83,197.83

TOTAL,1,197.83,
```

El material no aparece en ninguna columna.

**En M2.** `_resumen_materiales` (`pipeline.py:300-309`) agrega con `Counter(parte["type"])`
y `masa_por_tipo[parte["type"]] += parte.get("mass_g")`: el material se descarta antes de
llegar a `bom.bom_document` (`pipeline.py:326-328`). Consumidores del CSV:

| Consumidor | Qué asume | Evidencia |
| --- | --- | --- |
| API (descarga) | solo el sufijo `.csv`, dentro de `outputs/`; **no lee columnas** | `api.py:1513-1536` |
| API (artefactos) | expone la ruta en `artefactos` | `api.py:239`, `api.py:1239-1244` |
| MLflow | sube el archivo tal cual | `seguimiento.py:251-258` |
| Registro y banco | no leen el BOM | `registro.py:27-40`, `banco.py:29-39` |
| Evaluación | no lee el BOM | `evaluacion.py` (sin referencias a `csv`/`bom`) |
| Frontend | solo presencia y botón genérico | `frontend/src/api.ts:9,53-55`, `frontend/src/views/NewRequestView.vue` |
| Pruebas | **fijan cabecera y orden** | `tests/test_pipeline.py:217-220` |

## 4. Tolerancias

Lo que el kit ofrece, **fuera del programa**:

- `constraint_kit/iso286.py`: `interference_ei` (`:63`), `geom_mean` (`:75`), `tol_factor`
  (`:83`), `it_grade` (`:87`), `shaft_deviation` (`:94`), `hole_deviation` (`:122`) y
  `fit(hole_letter, hole_grade, shaft_letter, shaft_grade, nominal)` (`:130`); en µm,
  rango `3 < D ≤ 500 mm`, agujero solo base H (`iso286.py:129-132`).
- `constraint_kit/tolerance.py`: `_devs` (`:13`, acepta `hole: "H7"`/`shaft: "g6"` o
  `upper`/`lower` en mm) y `stackup(dims, as_clearance=False)` (`:25`) con peor caso y RSS.
- Endpoints del kit: `POST /synthesize/tolerance` (`api.py:431`) y `POST /tolerance/stackup`
  (`api.py:678`).

**El DSL no las conoce.** `dsl.py:23-24` importa solo `mate_intent`, `mates` y
`builder.ALL_PART_GENS`; `compile_program` (`dsl.py:160-165`) delega en
`assembly.build_tree`/`builder.build_assembly`. No hay una sola referencia a `iso286` en
`builder.py`, `parts.py`, `dsl.py` ni `assembly.py`: son funciones de librería y endpoints
del servidor, no parte del programa ni del verificador.

**Sonda sobre las dos vías de "meter" la tolerancia en el programa:**

1. Clave nueva a nivel de parte (`"tolerances": [{"dim": "thick", "fit": "H7/g6"}]`) →
   `dsl.validate(...) == []`: el kit **no tiene lista blanca de claves** en la parte
   (`_check_part` valida `id`, `type` y que `params` sea dict, `dsl.py:128-142`), así que la
   clave pasa sin error… pero nadie la lee: `builder.build_assembly` usa
   `type/params/material/finish` (`builder.py:262-272`) y el reporte se arma con campos
   explícitos (`builder.py:321-325`). Queda **almacenada y sin interpretar**.
2. Dentro de `params` → **rompe el build**: los generadores no aceptan `**kwargs`, así que
   una clave desconocida termina en `part-build-error` en el tier geométrico
   (`dsl.py:96-103`) o en excepción dura (`builder.py:266-268`).

Además, el verificador **no extrae cotas**: `dsl.signature` solo da `volume`, `area`,
`bbox_sorted`, `n_solids`, `n_faces` y `n_edges` (`dsl.py:181-186`). Una tolerancia "por
cota" exigiría un extractor de caras/ejes que hoy no existe.

## 5. Costo de un parche al kit (si se quiere RF-4 dentro del DSL)

`scripts/vendor-constraint-kit.sh` fija la revisión (`:10`) y aplica **dos parches
triviales** con `sed`/heredoc y `grep -q` para idempotencia (`:18-33`); la única
"verificación" es imprimir `git rev-parse --short HEAD` (`:35`). No hay aserción de que el
parche haya quedado aplicado.

| Pieza del parche | Archivos del kit | Estimación |
| --- | --- | --- |
| Transportar la tolerancia al reporte sin inyectarla al generador | `builder.py` | 25-40 líneas |
| Validarla en el esquema (códigos `unknown-tolerance-dim`, `bad-tolerance`) | `dsl.py` | 30-45 líneas |
| **Verificación real**: comparar cada cota nominal ± tolerancia contra la pieza | `dsl.py`/nuevo módulo | 60-120 líneas (`bbox_sorted` por eje es la vía barata; por cara exige extractor nuevo) |
| Cablear ISO 286 (`H7`/`g6` → desviaciones) | `tolerance.py` / `iso286.py` | ~10 líneas |
| Parche idempotente + aserción en el script | `scripts/vendor-constraint-kit.sh` | 10-20 líneas |
| Pruebas del parche | `vendor/constraint-kit/tests/` | ~30 líneas |

Total realista: **~130-200 líneas de kit + ~20 de scripting**, más mantener el parche entre
revisiones del kit. El kit se resuelve por `path` (`pyproject.toml`, `[tool.uv.sources]`),
así que un parche no exige regenerar `uv.lock`, pero sí obliga a `make vendor` en cada
checkout y en CI — y hoy nada verifica que el parche quedó aplicado.

## 6. Efecto sobre el corpus dorado (RNF-2)

El corpus congela **solo** el `sha256` del STEP normalizado: `CLAVES_CASO` (`"id", "fuente",
"programa", "resultado", "sha256"`) en `corpus_dorado.py:25` y `huella_step` en
`corpus_dorado.py:55-58`. No congela masa, BOM ni CSV.

- Añadir columnas de material y costo al CSV **no** invalida el corpus.
- Sí lo rompería una **excepción** al escribir el CSV, porque `observar` construye a través
  del pipeline (`corpus_dorado.py:177`): el nuevo escritor tiene que ser tan robusto como el
  actual.
- Si se toca la densidad de un material usado por casos congelados, o se añaden claves a sus
  `params`, los hashes cambian y hay que regenerar con `--write`.

## 7. Ruta recomendada para AC2 (insumo para `plan.md`)

**Pre-agrupar en M2 y escribir el CSV en M2**, sin parchear `bom.py`:

- `bom_document` consume solo `{bom, mass_by_type, mass_g, part_count}` (`bom.py:12-18`) y
  agrupa por tipo; añadir material y costo obliga a parchear `bom.py:12-35`, el test del kit
  (`tests/test_kernel.py:2002`) y el test de M2 (`tests/test_pipeline.py:217-220`), y deja el
  agregado de costo dentro de un repositorio de terceros.
- Un escritor propio en `construir_pieza` (`pipeline.py:322-328`) reutilizando
  `_resumen_materiales` (`pipeline.py:300-309`) cuesta ~40-60 líneas y no toca el kit; la
  descarga solo exige sufijo `.csv` (`api.py:1528-1532`).
- RNF-3 se sostiene extendiendo: las cuatro columnas actuales quedan al principio y en el
  mismo orden, y `tests/test_pipeline.py:217-220` se amplía fijando también la cabecera
  nueva (comportamiento previo conservado = columnas viejas intactas).

## 8. Recomendación de alcance (decisión del humano, AC1)

**Opción B — alcance reducido: material explícito (RF-2), guard de material (RF-5) y BOM con
costos (RF-3). Sin RF-4.**

Razones:

1. AC4 exige que la tolerancia viva **dentro** del programa y que el verificador la
   compruebe: eso es un parche de 130-200 líneas en un repositorio externo pinneado, sin
   verificación de aplicación en el script actual, y con mantenimiento entre revisiones.
2. El verificador no extrae cotas (`dsl.py:181-186`): "el reporte incluye la desviación
   aplicada y el resultado de la verificación" no existe sin construir un extractor nuevo.
3. El valor para el usuario es bajo frente al riesgo: el BOM con costos y la declinación por
   material ya entregan el objetivo de la historia ("valorar la fabricación desde el diseño
   preliminar").
4. La propia spec lo habilita: RF-4 es condicional ("si el spike lo confirma") y AC4 está
   "condicionado al spike".
5. Mantiene intactos el corpus dorado y el contrato del CSV, que es donde están los
   consumidores reales.

**Si el humano elige A**, el plan tiene que incluir: tercer parche con aserción en
`scripts/vendor-constraint-kit.sh`, tolerancias **solo lineales** (por eje de `bbox_sorted`,
no por cara), un caso nuevo del corpus con tolerancia (y su `--write`) y la actualización del
test del kit.

**Riesgo residual si se aprueba B:** RF-4 y AC4 quedan sin cumplir por decisión explícita; hay
que dejarlo escrito en `plan.md`, en `evidence.md` y en `specs/README.md` para que la spec no
aparente estar completa.

## 9. Datos adicionales para `plan.md` (no bloquean el alcance)

- **Guard de material (AC3).** La lista canónica es la del prompt (8 materiales:
  `steel, stainless, aluminum, brass, copper, abs, pla, nylon`,
  `prompts/planner-v1.txt:1`), mientras `DENSITY_G_MM3` tiene 11 claves (agrega `iron`, `al`,
  `petg`) y `MATERIAL_STRENGTH` no tiene `copper`. Hay que decidir si `al` se acepta como
  alias de `aluminum`; `iron`, `petg` y `titanium` deben declinar. El guard es código nuevo en
  `pipeline.py` (el kit no lo tiene), con un código de diagnóstico propio mapeado a una causa
  de `declinacion.Causa` (`declinacion.py:31-40`); `FAMILIA_NO_SOPORTADA` es la causa natural
  si el material está fuera del catálogo. Si el guard usa una lista distinta de la del
  prompt, el prompt no cambia (no hace falta versión nueva de `planner-v1`).
- **Precios.** No hay tabla de costos en el kit: el archivo versionado y configurable
  (Supuesto de la spec) es responsabilidad de M2, y su lectura debe ser offline y determinista.
- **Masas por material.** `mass_by_type` sale de `builder.build_assembly`
  (`builder.py:320-323`), que ya aplica `DENSITY_G_MM3`: el costo unitario se puede calcular
  como `masa_unit_g × precio_por_gramo`, sin recalcular geometría.
