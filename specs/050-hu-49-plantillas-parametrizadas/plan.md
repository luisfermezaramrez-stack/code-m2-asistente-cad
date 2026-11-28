# Plan de implementación · HU-49 (SPEC-050)

## Contexto verificado

Todo lo de abajo está en `main` (`55db05d`, incluye HU-48) y se leyó en este worktree.

- **Tipos y familias.** `CATALOGO` mapea los 8 tipos del motor a nombres en español
  (`src/m2_cad/pipeline.py:62-71`). El banco agrupa por 6 familias de producto
  (`data/test_cases.csv:1` con cabecera `id,familia,solicitud,medidas,resultado_esperado`;
  `src/m2_cad/dataset.py:10-12`: `FAMILIES` + `tornillería`, `PRODUCT_FAMILIES` agrega
  `extrusion` y `pipe`). `tornillería` es etiqueta de banco, no tipo: se traduce a `screw`
  en `dataset.py:238-240`. `extrusion` y `pipe` existen como tipo pero no tienen familia de
  banco ni `PARAMETERS` (`dataset.py:14-23`).
- **Camino único de construcción.** `_construir_programa` (`pipeline.py:629-668`) escribe
  `programa.json`, aplica `validar_catalogo`, cancela de forma cooperativa y llama
  `construir_pieza`; `construir_pieza` (`pipeline.py:422-455`) hace
  `verificar_programa` → `build_assembly` → caja → BOM → export STEP/GLB → CSV → DXF.
  `verificar_programa` (`:285-308`) corre el guard de material (HU-48) y `dsl.check`.
- **HU-35 (SPEC-036)** ya está en `main`: `src/m2_cad/versiones.py` persiste el programa DSL
  por solicitud con propietario (`registrar_version(...)`, `versiones.py:160-190`), índice
  por archivo `data/versiones/<uuid>.json` (`:123-127`), y `GET /v1/generar/{id}/versiones`
  lo expone (`api.py:1534-1568`). La autorización es `_historial_propio` +
  `garantizar_propietario` (`api.py:1275-1292`).
- **Autenticación (HU-53).** `usuario_actual` (`autenticacion.py:195-207`) devuelve
  `ANONIMO = "anónimo"` con `M2_AUTH_ENABLED=0` y 401 sin sesión si está activa;
  `garantizar_propietario` (`:331-343`) responde 404 sin revelar existencia.
- **Contrato y tipos congelados (HU-31).** `contracts/openapi-v1.json` (1245 líneas) y
  `frontend/src/generated/api.ts` se regeneran con `make api-contract` y `make api-types`;
  `make check` corre ambos `--check` (`Makefile:105`) y `tests/test_hu31_api_v1.py:131-139`
  compara `app.openapi()` con el JSON versionado, así que una ruta nueva sin regenerar
  rompe CI.
- **App shell (HU-38)** en `main`: `frontend/src/router.ts:9-18` con `/nueva-solicitud`,
  `/historial`, `/historial/:identificador`, `/metricas`, `/ajustes`; nav en
  `frontend/src/App.vue:76-81`; estado de generación provisto por el shell
  (`provideGeneration()`, `App.vue:8`).
- **Firma geométrica.** `dsl.signature(ensamble)` se calcula en `construir_pieza`
  (`pipeline.py:439`) pero **sólo se usa su `volume`** (`:448`): la firma completa
  (volumen, área, `bbox_sorted`, `n_solids`, `n_faces`, `n_edges`) no se persiste ni sale
  por HTTP (`ResultadoPieza.a_respuesta()`, `:197-212`).

## Arquitectura

### 1. Catálogo versionado de plantillas (RF-1, RNF-3)

`data/plantillas.toml`, mismo patrón que `data/materiales.toml` (HU-48): `version = 1`,
unidad declarada y una entrada `[[plantillas]]` por familia del banco con

| Campo | Uso |
| --- | --- |
| `id`, `nombre`, `descripcion` | Identidad y texto para la UI. |
| `tipo` | Tipo del motor (`plate`, `screw`, …), validado contra `CATALOGO`. |
| `familia` | Familia del banco (`tornillería` en el tornillo), para trazabilidad. |
| `programa` | Programa DSL completo con los valores por defecto; el material es explícito. |
| `parametros[]` | `nombre` (clave de `params` del DSL), `etiqueta`, `unidad`, `defecto`, `minimo`, `maximo`, `entero`. |

`src/m2_cad/plantillas.py` es el único cargador (`RUTA_PLANTILLAS`, `M2_PLANTILLAS`,
`cargar()`, `verificar()`, `instanciar()`), y `scripts/verify_plantillas.py` +
`make plantillas-check` (dentro de `make check` y del `job lint` del espejo, con guarda en
`tests/test_ci_parity.py`) verifican: versión, tipos dentro de `CATALOGO`, familias de
`PRODUCT_FAMILIES`, que cada `parametros[].nombre` exista en el `params` del programa,
que `defecto` esté en `[minimo, maximo]` y que el programa base pase el verificador.

### 2. Instanciación sin LLM (RF-2, RF-4, RNF-1)

`plantillas.instanciar(plantilla, valores)` valida **antes de construir**: parámetro
desconocido, valor no numérico, entero no entero y fuera de rango se rechazan con
`ErrorPlantilla` cuyo mensaje nombra el parámetro, el valor recibido y el rango
(`«espesor debe estar entre 2 y 50 mm; recibí 1»`). Con los valores válidos arma una copia
del `programa` y la pasa por el **mismo** `_construir_programa` que el flujo por texto, así
que el guard de material, `validar_catalogo`, la verificación determinista, el registro y
el versionado son idénticos. No hay llamada al modelo en ningún punto del camino (AC1 se
prueba con un doble de `generar_pieza` que falla si se invoca).

### 3. Guardar una pieza como plantilla (RF-3)

`POST /v1/plantillas` recibe `{solicitud_id, nombre}`; lee la última versión del historial
de HU-35 (`versiones.ultima_version`), verifica propiedad con `garantizar_propietario`,
deriva los parámetros y persiste la plantilla con su `usuario`. AC3 se cumple porque la
plantilla guarda **el mismo programa** y unos rangos cuyo valor por defecto es el original:
instanciarla sin cambios reproduce la firma geométrica.

### 4. API y contrato congelado (HU-31)

Tres rutas nuevas bajo `/v1`, todas con `Depends(usuario_actual)`:

| Ruta | Qué hace |
| --- | --- |
| `GET /v1/plantillas` | Catálogo versionado + plantillas guardadas **del usuario**, con `origen` (`catalogo`/`guardada`). |
| `POST /v1/plantillas/{id}/instanciar` | Body `{valores}`; instancia y construye; devuelve la respuesta de pieza (artefactos, volumen, caja, tiempos, `firma`). |
| `POST /v1/plantillas` | Body `{solicitud_id, nombre}`; guarda la última versión como plantilla. |

Se regeneran `contracts/openapi-v1.json` y `frontend/src/generated/api.ts` en el mismo
commit (`make api-contract`, `make api-types`). Los endpoints existentes no cambian.

### 5. UI (RF-5)

`frontend/src/views/TemplatesView.vue` en `/plantillas`, con entrada en
`router.ts:9-18` y en el nav de `App.vue:76-81`: lista del catálogo, formulario con un campo
por parámetro (unidad y rango visibles), botón «Generar» que llama al endpoint de
instanciación y muestra los artefactos con el patrón de descargas existente
(`frontend/src/api.ts`, `availableArtifacts`/`downloadArtifact`), y acción «Guardar como
plantilla» sobre una solicitud. Pruebas Vitest con el doble `frontend/tests/fakeCadService.ts`
y **un** escenario E2E en `frontend/e2e/` (instanciar la plantilla de placa del catálogo),
porque el repo ya tiene Playwright y AC1 es un camino de punta a punta.

## Verificación

1. Pruebas nuevas en RED antes de implementar: `tests/test_plantillas.py` (catálogo,
   rangos, errores), `tests/test_hu49_plantillas.py` (AC1 con doble que prohíbe el LLM,
   AC2, AC3 por firma, aislamiento entre usuarios) y Vitest de la vista.
2. No regresión: flujo por texto, CSV del BOM (compatibilidad byte a byte del prefijo
   histórico), endpoints existentes y `make corpus-dorado`.
3. `make check` con `M2_DOWNLOAD_SECRET` de 32 bytes; `make e2e` si se agrega el escenario.
4. Evidencia en `evidence.md` al cerrar.

## Decisiones abiertas (recomendación)

**(a) Formato y ubicación del catálogo versionado (RNF-3).**
Recomiendo **`data/plantillas.toml`** con `version = 1`, cargado por
`src/m2_cad/plantillas.py` y verificado por `make plantillas-check`. Razón: es el patrón
inmediatamente anterior del repo (`data/materiales.toml` + `materiales.py` +
`verify_materiales.py`, HU-48), TOML está en la biblioteca estándar, admite comentarios de
procedencia y el archivo se revisa en el PR como datos, no como código. El JSON queda para
instantáneas máquina-a-máquina (`data/corpus_dorado.json`). Ruta configurable con
`M2_PLANTILLAS`; nada de base de datos.

**(b) Dónde se persisten las plantillas guardadas y con qué propietario (RF-3).**
Recomiendo **un índice JSON `data/plantillas.json`** (gitignored, junto a `data/cola.json`),
con una entrada por plantilla `{id, usuario, nombre, tipo, familia, programa, parametros,
creada}`, escritura atómica bajo el bloqueo de `persistencia_registro` y
`garantizar_propietario` en lectura e instanciación (404 para plantillas ajenas). Razón: el
propietario queda **en el dato**, no en la ruta, así ningún nombre de usuario se convierte
en nombre de archivo (evita traversal y colisiones), y el aislamiento es una comparación
explícita y testeable. `M2_PLANTILLAS_JSON` para pruebas y despliegue. Con
`M2_AUTH_ENABLED=0` todo cae en `anónimo` y no hay aislamiento, igual que hoy en versiones y
registros: se documenta, no se inventa un modo local distinto.

**(c) Qué parámetros y qué rangos expone una plantilla creada desde una pieza generada.**
Recomiendo **exponer todos los parámetros numéricos del programa** (los de `params` que son
`int`/`float`) con **rango derivado ±50 %** alrededor del valor original, sin relleno
manual: mínimo `0` cuando el original es `0` (p. ej. `boss_d`), mínimo `1` cuando el
original es ≥1 y el parámetro es una cuenta (`bolt_count`, entero, máximo `2×`), unidad
`mm` salvo los contadores (`u`), y el resto de parámetros (`nps`, `size`, `kind`,
`material`, `fastener_type`) quedan **fijos** en el programa y no se exponen. Razón: AC3
exige que instanciar con los valores por defecto reproduzca la firma, y eso sólo se
garantiza si el defecto es el valor original; ±50 % da margen útil sin pedirle al usuario
que diseñe rangos, y marcar parámetros a mano añadiría UI, API y pruebas que no entran en
3 SP. Si más adelante se quiere control fino, el formato ya admite ajustar los rangos en el
TOML.

**(d) Familias del catálogo inicial.**
De `data/test_cases.csv` salen **6 familias de producto** (`plate`, `sheet_bracket`,
`adapter`, `flange`, `spacer`, `tornillería`; `fuera_alcance` son los 10 negativos).
Recomiendo **una plantilla por familia**, seis en total: `plate` (placa con agujeros, la de
AC1: 60 × 50 × 6 mm + `bolt_d`/`bolt_circle`/`bolt_count`), `sheet_bracket`, `adapter`,
`flange` y `spacer` con su `tipo` homónimo, y `tornillo` con `tipo = "screw"` y
`familia = "tornillería"` (mapeo explícito de `dataset.py:238-240`). `extrusion` y `pipe`
quedan fuera del catálogo inicial porque no tienen familia en el banco: se anotan como
seguimiento, no se inventan.
