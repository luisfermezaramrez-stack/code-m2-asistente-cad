# Plan de implementación · HU-48 (SPEC-049) — alcance B

## Decisión de arquitectura

El alcance aprobado tras el [spike](./spike.md) es **B**: material explícito (RF-2), BOM con
costos (RF-3) y guard de material (RF-5). **RF-4/AC4 quedan fuera** por decisión del spike:
exigirían un parche de 130-200 líneas en el `constraint-kit` vendoreado, sin verificación de
aplicación en `scripts/vendor-constraint-kit.sh`, y el verificador del kit no extrae cotas
(`dsl.signature` solo da `volume/area/bbox_sorted/n_solids/n_faces/n_edges`). La spec ya
declara RF-4 condicional y AC4 "condicionado al spike".

Tres piezas nuevas, todas en M2 y ninguna dentro del kit:

1. **Guard de material** en `verificar_programa` (`src/m2_cad/pipeline.py`), que corre tanto
   en el camino del usuario como en el corpus (que llama `construir_pieza` directo).
   Normaliza el alias `al` → `aluminum` y declina cualquier otro material con un motivo que
   lo nombra. El kit hoy cae a la densidad del acero en silencio (`builder.py:320`).
2. **Tabla de precios versionada** en `data/materiales.toml` + cargador
   `src/m2_cad/materiales.py`, con `make materiales-check` como puerta de CI.
3. **CSV del BOM escrito por M2**, pre-agregando por tipo y material en
   `_resumen_materiales` y sin usar `bom.bom_document`. Decisión de AC2: parchear
   `bom.py` obligaría a tocar el test del kit (`vendor/constraint-kit/tests/test_kernel.py:2002`),
   meter el agregado de costo en un repositorio de terceros y arrastrar el parche entre
   revisiones; escribir el CSV en M2 cuesta ~40-60 líneas y deja el kit intacto.

### Componentes

- `data/materiales.toml`: 8 materiales canónicos (los del prompt,
  `prompts/planner-v1.txt:1`), con `alias`, `densidad_g_mm3`, `precio_usd_kg`, `fuente` y
  `actualizado`; `version = 1` y moneda/unidad declaradas.
- `src/m2_cad/materiales.py`: `cargar()`, `SOPORTADOS`, `normalizar()`, `precio_usd_kg()` y
  `verificar()`. Ruta configurable con `M2_MATERIALES` (por defecto `data/materiales.toml`).
  Sin red y sin caché: se lee al escribir el BOM, así un cambio de precios no requiere reiniciar.
- `scripts/verify_materiales.py` + `make materiales-check` (dentro de `make check` y del job
  `lint` del espejo): falla si falta un material canónico, si una densidad no coincide con
  `DENSITY_G_MM3` del kit, si un precio no es positivo o si un alias choca con un nombre.
- `src/m2_cad/pipeline.py`: `validar_materiales()` llamado al inicio de `verificar_programa`;
  `_resumen_materiales()` ahora agrupa por `(tipo, material)`; `_csv_materiales()` escribe el
  CSV con material y costos; se retira el uso de `constraint_kit.bom`.
- `src/m2_cad/declinacion.py`: causa nueva `MATERIAL_NO_SOPORTADO` con su motivo y su "qué
  haría falta", para que el catálogo cerrado siga siendo la única fuente de causas.

### Formato del CSV (RF-3 y RNF-3)

Las cuatro columnas actuales quedan **al principio y en el mismo orden**; se agregan tres al
final:

| Columna | Contenido |
| --- | --- |
| `part_type` | Tipo de la pieza (sin cambios). |
| `qty` | Cantidad de esa línea (tipo + material). |
| `total_mass_g` | Masa de la línea, con la densidad del material (`DENSITY_G_MM3`). |
| `unit_mass_g` | Masa unitaria. |
| `material` | Material canónico (`aluminum` cuando el modelo pidió `al`). |
| `unit_cost_usd` | Costo unitario = masa unitaria / 1000 × precio del material. |
| `total_cost_usd` | Costo de la línea. |

La fila `TOTAL` conserva `TOTAL`, la cantidad de piezas y la masa total en sus primeras
posiciones, y suma el costo total en la última. El prefijo histórico se escribe **igual que `bom.py`**: `csv.writer` sin `lineterminator`
(fin de línea `\r\n`), masa con `round(x, 3)` sin rellenar ceros y una fila vacía antes del
total. Un lector que use las cuatro columnas viejas sigue funcionando, y la prueba de RNF-3
compara ese prefijo **byte a byte** contra `bom.bom_document` sobre el mismo build.

### Configuración

| Variable | Valor por defecto | Uso |
| --- | --- | --- |
| `M2_MATERIALES` | `data/materiales.toml` | Ruta de la tabla de precios (versionada en el repo, configurable por entorno). |

Un material sin precio en la tabla es un error de configuración, no del usuario: se levanta
`ErrorPipeline` nombrando el material, para no inventar un costo.

### Compatibilidad y seguridad

- El kit **no se parchea**: `vendor/` queda idéntico y `make vendor` no cambia.
- El corpus dorado congela solo el `sha256` del STEP (`corpus_dorado.py:25,55-58`), así que
  agregar columnas al CSV no lo invalida; el guard acepta `steel` (los 12 casos `acepta` lo
  usan) e ignora los programas `{"unsupported": …}` (los 3 `declina`).
- Sin red, sin API key y sin GPU: la tabla es un archivo local y las pruebas inyectan el
  modelo como ya hace la suite.
- Solo se agrega una causa al catálogo cerrado; las respuestas existentes no cambian de forma.

### Fuera de alcance

RF-4/AC4 (tolerancias por cota) por decisión del spike; cotización real con proveedores;
tolerancia de medición del banco; análisis por elementos finitos.

## Verificación

1. Pruebas nuevas en RED antes de implementar: `tests/test_materiales.py` (tabla y verificación)
   y `tests/test_hu48_materiales_bom.py` (AC2, AC3, RNF-3).
2. `make check` con `M2_DOWNLOAD_SECRET` exportado: Ruff, `materiales-check`, contratos,
   Vitest, TypeScript, build, pytest con cobertura.
3. `make corpus-dorado` verde tras el cambio.
4. Evidencia en [`evidence.md`](./evidence.md).
