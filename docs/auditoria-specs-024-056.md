# Auditoría de las SPEC-024 a SPEC-056 contra el código real

- **Objeto auditado**: commit `7d45bd4` de la rama `docs/backlog-v2-specs` (33 specs,
  `spec.md` por spec, sin `plan.md` ni `tasks.md`).
- **Alcance**: verificar que cada afirmación sobre el estado actual del código sea cierta,
  que cada criterio de aceptación sea verificable y que las dependencias y el orden sean
  ejecutables. **No** se auditó redacción, estilo ni pertinencia de las propuestas.
- **Método**: lectura de las 33 specs, contraste de las 122 referencias `ruta:línea` contra
  el árbol y contra `vendor/constraint-kit` (presente en el checkout aunque esté
  gitignored), y verificación manual de los 13 hallazgos de mayor impacto.
- **Decisión**: las correcciones se aplicaron **antes** de crear las issues, en la misma
  rama, para no publicar alcances falsos. Ver §8.

## Cómo usar esta nota

1. Al abrir la HU de una spec, leé primero su entrada en §1 y §3.
2. Aplicá las correcciones en la rama de la HU: es una spec *spec-first*, así que corregir
   antes de implementar es legítimo y no requiere marcar retroactividad.
3. Si una corrección cambia el alcance, reflejala también en la fila correspondiente de
   `specs/README.md` y en el tamaño de la HU del tablero.
4. Las specs sin entrada en §1 no requieren cambios: `SPEC-027`, `SPEC-029`, `SPEC-031`,
   `SPEC-036`, `SPEC-042`, `SPEC-045`, `SPEC-046`, `SPEC-048`, `SPEC-053`.

## 1. Hallazgos que cambian alcance o son falsos

### SPEC-024 · corpus dorado del núcleo en CI
- El diagnóstico "es la única que CI no vigila" es **impreciso**: `tests/test_pipeline.py`
  ya construye piezas reales en CI y compara volumen y caja contra tolerancia ±2 %
  (`tests/test_pipeline.py:106-130,219-227`), y el smoke de `ci.yml:55` ejecuta "CAD real".
  El hueco real es más fino: **no hay resultados congelados por hash**, así que una
  divergencia geométrica por debajo del 2 % no se detecta. Reformular el problema así.
- **AC1 y AC2 no son testeables**: exigen mutar `constraint-kit` o `dsl.check` dentro del
  PR. Sustituirlos por un caso del corpus cuyo hash esperado se altera a propósito y
  verificar que el job falla nombrando el caso.

### SPEC-025 · logging estructurado
- AC3 ("la clave no aparece en los logs") está vacío hoy: no existe código que pueda
  filtrarla. Agregar el caso real: error del proveedor que devuelve `Authorization` en el
  cuerpo de la respuesta.

### SPEC-026 · reintentos y caché del LLM
- La referencia a `vendor/constraint-kit/constraint_kit/llm.py:68` es **correcta**
  (`httpx.post` único); conviene aclarar que `vendor/` se restaura con `make vendor` y la
  revisión fijada en `scripts/vendor-constraint-kit.sh`, para que la cita resista un clone
  limpio.
- El mapeo a 503 no está en `api.py:176-180` (adaptador SSE) sino en
  `src/m2_cad/api.py:137-139`.
- AC3 ("401/402 sin reintentos") es el comportamiento actual (`pipeline.py:391-394`,
  `MENSAJES_HTTP:96-100`): convertirlo en prueba de no regresión, no en trabajo nuevo.

### SPEC-028 · tipos del frontend desde OpenAPI
- "Su forma no aparece hoy en `/openapi.json`" es impreciso: la ruta aparece como objeto
  genérico sin propiedades (`tests/test_sse.py:117-119`). Decir "aparece sin campos".

### SPEC-030 · runbook
- Ya existe un precedente de diagnóstico operativo en `docs/hu15-despliegue.md:100-114`.
  Delimitar el hueco a lo que falta: modelo caído, saldo/credencial, rotación de clave,
  rollback de imagen y de versión de modelo, restauración de datos.

### SPEC-032 · API `/v1`
- El 404 JSON de rutas desconocidas vive en `src/m2_cad/web.py:40-70`; `api.py:560` es el
  comentario y `api.py:561` la llamada a `configurar_web`. Corregir la cita.
- AC1 ("el cliente viejo sigue funcionando") es vacío antes de existir `/v1`: formularlo
  como no regresión explícita de las rutas planas actuales
  (`api.py:54,222,397,495`).

### SPEC-033 · costo, límites e idempotencia
- **Omisión de alcance**: ya existe un tope de capacidad de 128 trabajos con 503
  (`src/m2_cad/trabajos.py:144-161`). La spec debe decir cómo convive el tope por ventana
  con ese límite y con `--workers 1`.
- AC4 es débil: `costo_usd` ya se registra por corrida (`api.py:302-311`). Definir el
  endpoint o KPI acumulado como artefacto nuevo.

### SPEC-034 · prompts versionados
- AC3 ("tests de prompt: formato JSON, familias, ambiguo") ya está cubierto por
  `tests/test_pipeline.py:486-493` y `:631-638`. Redefinir AC3 sobre el prompt
  versionado (id + hash + registro), no sobre el texto inline.

### SPEC-035 · sistema de diseño v2
- AC2 ("cambiar un token no toca componentes") es vacío: los tokens ya son fuente única
  importada una vez (`design/tokens.css:2-63`, `frontend/src/main.ts:3`).
- Confirmado que **ya existe** una escala tipográfica (`--text-small`, `--text-body`,
  `--text-heading`, `--text-title`); lo que falta es documentarla y aplicar modo oscuro.

### SPEC-037 · endurecimiento de descargas
- AC3 mezcla dos cosas: la allowlist de formatos **ya** rechaza (`api.py:530`). Dejar AC3
  sólo en la validación estricta del id (`api.py:222-231`) y la expiración.

### SPEC-038 · historial en la UI
- **Omisión de alcance**: sólo el **STEP** de una solicitud pasada es re-descargable
  (`api.py:234-255`); GLB y CSV exigen estado vivo en `GestorTrabajos`
  (`api.py:520-531`), que se pierde al reiniciar. O el historial declara que sólo recupera
  STEP, o depende de SPEC-031 para persistir las rutas.
- AC3/RNF-1 ("sin copia autoritativa en el cliente") pasa hoy sin código. Reformular como
  "el listado usa un endpoint de listado", que hoy no existe: sólo `GET /registros/{id}`.

### SPEC-039 · app shell
- **Omisión de alcance**: `web.py:41-49` sólo sirve `/` y `/assets`, sin fallback SPA, y
  `tests/test_web.py:44-52` afirma 404 JSON para rutas desconocidas. Introducir rutas
  exige fallback y cambiar esa prueba: declararlo en el alcance.
- AC3 es parcialmente vacío: `App.vue:16-23,70-74` ya distingue estados
  vacío/cargando/error/declinado. Acotar el AC a los estados nuevos del shell.

### SPEC-040 · visor ortogonal, medidas y captura
- **AC3 es falso tal como está**: el CSV de la pieza es el BOM de materiales
  (`constraint_kit/bom.py:31`: `part_type,qty,total_mass_g,unit_mass_g`), no trae
  dimensiones. Las medidas están en `caja_mm` (`src/m2_cad/pipeline.py:307`). Comparar
  contra `caja_mm` o contra el evento SSE, nunca contra el CSV.
- **Gotcha técnico no declarado**: el renderer se crea sin `preserveDrawingBuffer`
  (`GlbViewer.vue:52`), así que `toDataURL` devuelve un lienzo vacío salvo que se
  re-renderice justo antes de capturar. La solución debe estar en el RNF, no descubrirse
  al implementar.
- Cita corrida: los botones de cámara están en `GlbViewer.vue:138-144` y las acciones en
  `:100-116`, no en `:124`.

### SPEC-041 · WCAG AA
- AC2 ("todo el flujo sólo con teclado") es casi vacío: las acciones ya son
  `<button>`/`<a>` y el visor tiene `@keydown` (`GlbViewer.vue:120-127`,
  `App.vue:57-65,94`). La brecha real medida hoy es `ol.steps` sin región viva
  (`App.vue:75`). Acotar el AC a brechas con evidencia de axe.

### SPEC-043 · exportación DXF
- **El alcance está subestimado, no sobrestimado**: el `constraint-kit` vendoreado ya
  exporta sección a DXF real con ezdxf y seis proyecciones ortogonales con eliminación de
  aristas ocultas, más dimensiones generales:
  `vendor/constraint-kit/constraint_kit/drawing.py:35` (`overall_dimensions`),
  `:38` (`section_dxf`), `:52` (`projection_svg`), `:63` (`drawing`), expuesto en el kit
  en `api.py:519-528`. Lo que **falta** es cotas por arista (excluidas a propósito,
  `drawing.py:14-17`), capa de aristas ocultas (HLR las elimina) y armado del plano.
- "`ezdxf` sólo como extra del kernel" es impreciso: es dependencia de `build123d`
  (`uv.lock:291-296`) y el extra `kernel` está activo (`pyproject.toml:9`), así que ya es
  importable.
- Consecuencia de tamaño: si la spec se limita a "vistas ortogonales en DXF", es **M**;
  pasa a **L** sólo si incluye cotas y capas.

### SPEC-044 · exportación PDF
- No existe escritor vector→PDF en el kit: `pypdf` está presente para **extraer** texto
  (`constraint_kit/spec_extract.py:117-131`). La spec debe declarar que hace falta una
  dependencia nueva de generación y evaluar licencia y peso de imagen.
- AC1 y AC3 ("se imprime sin recortes", "se mide con regla") no son verificables en CI:
  declararlos como verificación manual o reemplazarlos por metadatos de página y escala.

### SPEC-047 · alertas de regresión
- "No existe baseline histórico" es impreciso: hay reportes commiteados con tasa por
  familia y causa por caso en `docs/hu07/banco-real-*/reporte.md`. El hueco real es que la
  comparación **automática** contra ese baseline no existe.

### SPEC-049 · materiales, tolerancias y BOM con costos
- **El DSL no admite tolerancias por cota**: el programa es
  `parts{id,type,params,material}` + `mates`, y `_check_part` valida `id`, `type` y
  `params`. Las tolerancias existen en el kit (`iso286.py`, `tolerance.py`,
  `/tolerance/stackup`, `/synthesize/tolerance`) pero **fuera** del programa. RF-4 exige
  parchear el repo externo en una revisión fija: es el mayor riesgo del backlog, no una
  incógnita menor. Conviene un spike antes de comprometer la HU.
- **AC2 es imposible tal como está**: el BOM agrupa por `part_type`
  (`constraint_kit/bom.py:31`), no por material. Concretar: pre-agrupar en
  `pipeline.py:268-278` o cambiar el BOM vendorizado.
- **AC3 no es determinista hoy**: `DENSITY_G_MM3` (`constraint_kit/parts.py:18-22`) admite
  `iron`, `al`, `petg`, `pla`, `abs`, `nylon`, `brass`, `copper` además de la lista del
  prompt (`pipeline.py:68`), y no hay guard de material. La declinación por material
  requiere código nuevo.
- Inventario incompleto: el kit también trae `massprops.py` y `manufacture.py`
  (printability FDM: overhang, pared, canal, volumen), sin costos y sin endpoint en la API.
  Declararlo para no duplicar trabajo.

### SPEC-050 · plantillas parametrizadas
- "No existe un catálogo" es impreciso: el kit expone bibliotecas de dominio
  (`GET /libraries`, `POST /assembly/from_library`, `library.py`). Precisar el hueco:
  hay librerías, no plantillas con rangos validados y unidades declaradas.

### SPEC-052 · panorama de métricas
- Falta `POST /generar` en la enumeración de rutas (`api.py:397-398`).

### SPEC-054 · autenticación
- Cita `POST /generaciones`, que **no existe**: la ruta es `POST /generar`
  (`api.py:398`).
- `api.py:222-235` son `GET /registros/{id}` y `/registros/{id}/step`, ambos de sólo
  lectura: citarlos como lectura, no como escritura abierta.
- AC4 ("`/health` responde sin credenciales") ya se cumple (`api.py:54-57`):
  convertirlo en prueba de no regresión.

### SPEC-055 · sitio de documentación
- La enumeración de `docs/` está incompleta: faltan `docs/README.md`,
  `hu15-docker-validation.md`, `hu15-integracion-hu14.md`, `hu15-sse.md` y `docs/hu07/`.
- "No hay sitio publicado" no es verificable desde el repo: declararlo supuesto.

### SPEC-056 · releases automáticos
- "Al fusionar en la rama principal" es ambiguo: el CI sólo dispara en `develop`
  (`.github/workflows/ci.yml:3-7`), el flujo de PR según `AGENTS.md` va a `develop` y no
  hay rama de release declarada. Especificar si el release corta desde `develop` o desde
  `main`, y quién crea la etiqueta.

## 2. Dependencias faltantes

| Spec | Falta depender de | Motivo |
| --- | --- | --- |
| SPEC-043 | SPEC-037 | RF-4 y AC3 descargan el DXF por el canal de artefactos endurecido |
| SPEC-044 | SPEC-037 | hereda el canal de 043 |
| SPEC-047 | SPEC-027 | RF-3 y AC3 agrupan por la etiqueta de causa de declinación |

El grafo restante está bien: sin ciclos y sin dependencias hacia adelante.

## 3. Criterios de aceptación vacíos o no verificables

| Spec | AC | Situación |
| --- | --- | --- |
| 024 | AC1, AC2 | exigen mutar código de otro repo dentro del PR: no testeable |
| 025 | AC3 | no hay código que pueda filtrar la clave hoy |
| 026 | AC3 | ya es el comportamiento actual |
| 028 | — | la ruta sí aparece en OpenAPI, sin campos |
| 032 | AC1 | vacío antes de que exista `/v1` |
| 033 | AC4 | la métrica de costo ya se registra por corrida |
| 034 | AC3 | ya cubierto por tests existentes |
| 035 | AC2 | los tokens ya son fuente única |
| 037 | AC3 | la allowlist ya rechaza formatos |
| 038 | AC3 | pasa hoy sin código |
| 039 | AC3 | los estados ya se distinguen |
| 041 | AC2 | el flujo ya es operable sin mouse |
| 044 | AC1, AC3 | verificación manual disfrazada de AC |
| 051 | AC1 | "se ve la sección rellena": juicio visual |
| 054 | AC4 | `/health` ya responde sin credenciales |

Regla para corregirlos al tomar la HU: un AC debe **fallar hoy**. Si pasa antes de escribir
código, es prueba de no regresión y debe decirse así.

## 4. Citas de línea corridas

| Spec | Cita | Realidad |
| --- | --- | --- |
| 026 | `api.py:176-180` para el 503 | `src/m2_cad/api.py:137-139` |
| 030 | hueco de diagnóstico operativo | ya hay precedente en `docs/hu15-despliegue.md:100-114` |
| 032 | `api.py:559-560` para el 404 JSON | el comportamiento está en `src/m2_cad/web.py:40-70` |
| 033 | tope de capacidad | `src/m2_cad/trabajos.py:144-161` (omitido) |
| 040 | `GlbViewer.vue:124` para los botones | `GlbViewer.vue:138-144` |
| 047 | "no hay baseline" | hay reportes en `docs/hu07/banco-real-*/reporte.md` |
| 050 | "no existe catálogo" | `GET /libraries` y `library.py` del kit |
| 052 | enumeración de rutas | falta `POST /generar` (`api.py:397-398`) |
| 054 | `POST /generaciones` | `POST /generar` (`api.py:398`) |
| 055 | enumeración de `docs/` | faltan 5 entradas |

## 5. Erratas del propio backlog v2

`docs/backlog-v2.md` quedó desactualizado respecto de las specs y hoy es la única fuente
con datos falsos:

- dice que `design/tokens.css` tiene 72 líneas (`docs/backlog-v2.md:149`); tiene 63;
- conserva las referencias de línea antiguas que las specs ya corrigieron;
- no incluye las dependencias 043/044 → 037 ni 047 → 027.

Al retomar, o se regenera desde las specs o se reduce a un puntero a `specs/README.md`, para
no mantener dos fuentes que se contradicen.

## 6. Nota de método

Durante la auditoría dos verificadores afirmaron que `vendor/` no existe en el checkout.
Sí existe (`vendor/constraint-kit`, gitignored y restaurable con `make vendor`), y las citas
`constraint_kit/*` de las specs resuelven correctamente. La consecuencia práctica es que
SPEC-043 y SPEC-049 se redactaron sin leer `drawing.py`, `bom.py`, `massprops.py` y
`manufacture.py`, y por eso subestiman lo que ya existe y proponen AC imposibles.

## 7. Estado de la rama

- Commit auditado: `7d45bd4`, rama `docs/backlog-v2-specs`, **local, sin push**.
- No se crearon issues ni se cargó nada en el tablero `m2-asistente-cad`.
- Este archivo no modifica ninguna spec: es la lista de correcciones a aplicar por HU.

## 8. Aplicación de las correcciones

Las correcciones de §1 a §4 se aplicaron en la rama `docs/backlog-v2-specs`, antes de crear
las issues. Cada spec corregida lo declara en su encabezado (**Auditoría**). Cada hallazgo
se volvió a verificar contra el código antes de aplicarlo; estos se ajustaron o rechazaron:

| Spec | Hallazgo de la auditoría | Resultado de la verificación |
| --- | --- | --- |
| 026 | el 503 no está en `api.py:176-180` | también está ahí (ruta SSE); se citan ambos lugares |
| 030 | precedente operativo en `docs/hu15-despliegue.md:100-114` | cubre problemas de entorno al levantar, no incidentes en operación |
| 038 | GLB y CSV dependen de SPEC-031 | las rutas ya se guardan en `resultado` (`api.py:477-480`); falta servirlas; se acota a STEP |
| 043 | el kit ya proyecta a DXF | las proyecciones ortogonales del kit son SVG (`drawing.py:52-60`); la sección sí es DXF |
| 043 | exclusión de cotas en `drawing.py:14-17` | está en `drawing.py:9-11` |
| 044 | hace falta una dependencia PDF nueva | `matplotlib` ya está instalado vía `vtk`; la spec admite ambas opciones |
| 047 | baseline en `docs/hu07/banco-real-*/reporte.md` | está un nivel más abajo: `docs/hu07/banco-real-*/*/reporte.md` |
| 049 | `pla`, `abs`, `nylon`, `brass`, `copper` fuera del prompt | ya están en el prompt (`pipeline.py:68-69`); los extras son `iron`, `al`, `petg` |

`docs/backlog-v2.md` se redujo a priorización, trazabilidad y reglas: los `spec.md` son la
fuente de verdad del alcance (§5 resuelta).
