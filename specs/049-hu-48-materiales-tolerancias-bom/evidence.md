# HU-48 — Evidencias de implementación

**Fecha:** 27 de noviembre de 2026
**Issue:** #108
**Especificación:** SPEC-049 (dependencia: SPEC-024)
**Rama:** `feature/hu-48-materiales-tolerancias-bom`
**PR:** pendiente (el encargo pedía no hacer push ni abrir PR)

## 1. Spike y alcance (AC1)

El spike de RF-1 está en [`spike.md`](./spike.md) (commit `7761e3b`) y se cerró **antes** de
implementar nada. Recomendó el alcance **B** —material explícito (RF-2), BOM con costos (RF-3)
y guard de material (RF-5)— porque AC4 exigía un parche de 130-200 líneas en el
`constraint-kit` vendoreado, sin verificación de aplicación en
`scripts/vendor-constraint-kit.sh`, y porque el verificador no extrae cotas. El humano aprobó
B; la decisión quedó registrada en [`spec.md`](./spec.md) y en [`plan.md`](./plan.md).
**RF-4/AC4 no se implementan.**

## 2. Implementación

- `data/materiales.toml`: tabla versionada (`version = 1`, moneda y unidad declaradas) con los
  ocho materiales canónicos del planificador, alias `al` → `aluminum`, densidad coherente con
  `DENSITY_G_MM3`, precio USD/kg, fuente y fecha.
- `src/m2_cad/materiales.py`: cargador único (`cargar`, `SOPORTADOS`, `normalizar`,
  `precio_usd_g`, `verificar`), ruta configurable con `M2_MATERIALES`, solo biblioteca
  estándar y lectura local.
- `src/m2_cad/pipeline.py`: `validar_materiales()` corre al inicio de `verificar_programa`,
  normaliza el alias y declina lo no soportado; `_resumen_materiales()` agrupa por
  `(tipo, material)`; `_csv_materiales()` escribe el CSV con material y costos. Se retiró el
  uso de `constraint_kit.bom` (el kit **no** se parchea).
- `src/m2_cad/declinacion.py`: causa nueva `MATERIAL_NO_SOPORTADO` con su motivo y su "qué
  haría falta".
- `scripts/verify_materiales.py` + `make materiales-check`, dentro de `make check` y del job
  `lint` del espejo, con guarda en `tests/test_ci_parity.py`.
- Pruebas nuevas: `tests/test_materiales.py` (tabla, alias, precios, verificación) y
  `tests/test_hu48_materiales_bom.py` (AC2, AC3, RNF-3).

## 3. Criterios de aceptación

| AC | Verificación | Resultado |
|---|---|---|
| AC1 — Spike | [`spike.md`](./spike.md) + decisión del humano registrada en `spec.md`/`plan.md` | Cumple: alcance B aprobado con la evidencia del kit. |
| AC2 — Material en el BOM | `test_ac2_el_csv_lleva_material_masa_y_costo`, `test_la_masa_usa_la_densidad_del_material_no_la_del_acero`, `test_el_alias_al_llega_al_csv_como_aluminum`, `test_el_csv_agrupa_por_tipo_y_material_y_suma_el_total` | Cumple: `material=aluminum`, masa con `DENSITY_G_MM3["aluminum"]` y costo unitario y de línea; la proporción masa aluminio/acero es exactamente la de las densidades (1e-3). |
| AC3 — Material no soportado | `test_ac3_declina_un_material_no_soportado_nombrandolo[titanium/iron/petg/acero/bronze]`, `test_ac3_el_motivo_declara_que_haria_falta` | Cumple: `PiezaDeclinada` con causa `material_no_soportado`, motivo que nombra el material y sin CSV escrito. |
| AC4 — Tolerancias | — | **No aplica**: fuera de alcance por decisión del spike (AC1). |
| RNF-1 — sin red, API key ni GPU | Las pruebas construyen el programa DSL a mano; no se invoca el modelo | Cumple. |
| RNF-2 — corpus dorado | `make corpus-dorado` | Cumple: «15 casos sin divergencias». |
| RNF-3 — CSV sin romper consumidores | `test_rnf3_las_cuatro_columnas_historicas_coinciden_byte_a_byte_con_el_kit`, `test_rnf3_el_consumidor_previo_lee_sus_cuatro_columnas`, `tests/test_pipeline.py` actualizado | Cumple: el prefijo histórico de cada fila —incluido el fin de línea `\r\n` y el `round(x, 3)` sin relleno— es idéntico byte a byte al de `bom.bom_document` sobre el mismo build, y un `DictReader` con las cuatro claves viejas sigue funcionando. |

## 4. Validaciones realizadas

| Validación | Comando | Resultado |
|---|---|---|
| RED inicial de las pruebas nuevas | `uv run --no-sync pytest -q tests/test_materiales.py tests/test_hu48_materiales_bom.py` | **2 errores de colección**: `ImportError: cannot import name 'materiales'` (el módulo no existía). |
| Tabla de materiales | `make materiales-check` | «materiales: 8 materiales verificados …, 8 con precio». |
| Pruebas de la historia | `uv run --no-sync pytest -q tests/test_hu48_materiales_bom.py tests/test_materiales.py` | **45 aprobadas**. |
| Corpus dorado | `make corpus-dorado` | **15 casos sin divergencias** (RNF-2). |
| Verificación completa | `make check` (con `M2_DOWNLOAD_SECRET` de 32 bytes) | **Verde**: Ruff, `prompts-check`, `materiales-check`, contratos OpenAPI, tipos, Vitest (**117 aprobadas**, 14 archivos), `vue-tsc`, build, sitio documental, **848 pytest aprobadas** (109 s) con cobertura **90,97 %** (umbral 70 %) y coherencia de release. |

## 5. Integración y correcciones

| Hallazgo | Corrección | Prueba |
|---|---|---|
| `ruff` rechazó una línea de 119 caracteres en el helper de pruebas. | Se partió el diccionario en tres líneas. | `make lint` limpio. |
| `make check` no llegaba a `cov` porque `mkdocs build --strict` exige que exista el `evidence.md` enlazado por `plan.md` y `tasks.md`. | Se escribió este archivo (el propio fallo del sitio documental es la guarda). | `docs-build` en verde. |
| El primer `make check` falló con 48 pruebas en rojo por `RuntimeError: Configure M2_DOWNLOAD_SECRET … al menos 32 bytes`: el valor de prueba que exporté era corto. | Se exportó `python3 -c 'import secrets;print(secrets.token_hex(32))'`, como hacen los pipelines. | Corrida completa en verde. |
| Una tabla de precios ilegible podía escapar como `RuntimeError` genérico (500 sin mensaje). | El guard atrapa `ErrorMateriales` y lo convierte en `ErrorPipeline` nombrando el archivo. | `test_una_tabla_de_precios_ilegible_es_error_del_servicio`. |

## 6. Limitaciones

- RF-4/AC4 no se implementan: tolerancias por cota requerirían parchear el kit (ver spike).
- Los precios son estimaciones internas, no cotizaciones; el CSV lo advierte en la propia
  tabla versionada (`fuente` y `actualizado` por material).
- El costo no incluye mecanizado, montaje ni merma: es material por masa.
- El job `e2e`/el pipeline del espejo no se ejecutaron en esta rama (no hay push).

## 7. Conclusión

El material viaja explícito desde el programa hasta el BOM, el CSV suma material, masa y costo
por línea y total con precios versionados, y un material fuera del catálogo declina nombrando
lo pedido en vez de construirse con la densidad del acero. El kit quedó intacto, el corpus
dorado sigue verde y las cuatro columnas históricas del CSV no cambiaron.

## 8. Correcciones de la verificación independiente

Ronda 2, en la misma rama; se observó RED en cada prueba nueva antes de corregir.

| Hallazgo | Corrección | Prueba |
|---|---|---|
| **B1 (RNF-3)**: el CSV había cambiado el prefijo histórico: `lineterminator="\n"` y `f"{x:.3f}"` (`20.72` → `20.720`), cuando `bom.py` usa CRLF y `round(x, 3)`. | `csv.writer` sin `lineterminator` (CRLF), masa con `round(x, 3)` sin formatear y fila `TOTAL` con el mismo prefijo; las columnas nuevas conservan su formato. | `test_rnf3_las_cuatro_columnas_historicas_coinciden_byte_a_byte_con_el_kit`: compara campo a campo y el fin de línea contra `bom.bom_document` del mismo build. |
| Un precio faltante se detectaba después de exportar STEP y GLB, dejando archivos a medias. | El CSV se arma antes de `builder.export`; la falta de precio aborta sin escribir nada. | `test_un_material_sin_precio_falla_antes_de_exportar`: exige `ErrorPipeline` y que no existan `pieza.step`, `pieza.glb` ni `pieza.csv`. |
| Un alias declarado en `data/materiales.toml` (por ejemplo `alias = ["iron"]`) reabría en silencio un material declinado. | Los alias viven en el código (`ALIAS = {"al": "aluminum"}`) y la tabla solo los documenta: `normalizar` no consulta la tabla y `verificar()` rechaza cualquier alias no permitido o mal asignado. | `test_verificar_rechaza_un_alias_que_reabre_un_material_declinado`: la tabla con `iron` produce problema y `normalizar("iron"/"petg"/"titanium")` sigue siendo `None`. |
| Un material vacío, no textual o una lista producía motivos como «» o «['steel']». | `_material_legible()` describe el material pedido: lo nombra si es texto y, si no, dice «sin material válido (vacío o no es texto)». | `test_ac3_el_motivo_es_legible_para_cualquier_valor`, parametrizada con `""`, `"   "`, `None`, `5`, `["steel"]` y `"aluminium"`. |
| Faltaba fijar la normalización de RF-2 en el guard. | Sin cambios de código: el comportamiento ya era correcto y ahora queda fijado. | `test_rf2_normaliza_mayusculas_espacios_y_saltos`: `" AL "` y `"Al"` → `aluminum`, `"\tnylon\n"` → `nylon`, `"STEEL "` → `steel`. |
| `spec.md` dejaba la parte de tolerancia de RF-5 ambigua. | RF-5 aclara que solo se implementa la parte de material; la de tolerancia queda fuera con RF-4. `plan.md`, `README.md` y `docs/hu15-sse.md` describen el fin de línea y el `round` reales. | Revisión de los cuatro documentos. |

## 9. Pulido previo al PR

| Hallazgo | Corrección | Prueba |
|---|---|---|
| El motivo de un material vacío se leía «el material sin material válido (vacío o no es texto) no está entre…». | Para vacío o no texto: «la pieza «<id>» no indica un material válido; materiales soportados: …». Para un material desconocido se mantiene el formato que lo nombra. | `test_ac3_el_motivo_es_legible_para_cualquier_valor`, parametrizada con la frase nueva. |
| El costo unitario y el de línea se redondeaban por separado: 3 espaciadores de nailon daban unitario `0,08` y línea `0,25`, y la fila no cuadraba. | Convención de factura: `unitario = round(costo exacto por unidad, 2)`, `línea = round(unitario × cantidad, 2)` y `TOTAL` = suma de las líneas. | `test_el_costo_de_linea_sale_del_unitario_redondeado` (3 × 2,95 g de nailon: `0,08`, `0,24` y total `0,24`). |
| El prefijo histórico del CSV no podía moverse con el pulido. | Sin cambios en las cuatro columnas ni en el fin de línea. | `test_rnf3_las_cuatro_columnas_historicas_coinciden_byte_a_byte_con_el_kit` sigue en verde. |
