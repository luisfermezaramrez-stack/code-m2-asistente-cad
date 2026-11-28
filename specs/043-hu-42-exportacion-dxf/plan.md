# HU-42 — Plan técnico de exportación DXF (SPEC-043)

## 1. Objetivo

Entregar un plano 2D en DXF con las vistas ortogonales frontal, superior y lateral en una
sola hoja, capas de aristas visibles y ocultas, cotas generales y cotas por arista, y
servirlo por el canal de artefactos de SPEC-037 (`/v1/generaciones/{id}/archivos/dxf`),
sin cambiar la salida STEP/GLB/CSV existente (RNF-3).

## 2. Spike (resultado antes de implementar)

El spike declarado en la spec (medio día) se corrió contra `vendor/constraint-kit` y el
venv del proyecto con una pieza real de `constraint_kit.builder` (`plate` 40×20×6):

- **Pregunta 1 — proyección a entidades DXF:** `HLRBRep_Algo` + `HLRBRep_HLRToShape`
  (mismo mecanismo del exportador SVG de CadQuery, `cadquery/occ_impl/exporters/svg.py`)
  devuelve aristas proyectadas como `Compound`; discretizadas con `positionAt`
  (2 puntos para líneas, n según longitud para curvas) y escritas como `LWPOLYLINE`
  con ezdxf 1.4.5. El DXF resultante pasa la auditoría (`ezdxf.audit.Auditor.run()`:
  0 errores, 0 correcciones).
- **Pregunta 2 — aristas ocultas:** `HCompound`/`Rg1LineHCompound`/`OutLineHCompound`
  devuelven las aristas ocultas (53 en la vista frontal de la placa) y se escriben en la
  capa `ARISTAS-OCULTAS` con `linetype="DASHED"`.
- **Cotas:** `add_linear_dim`/`add_aligned_dim` de ezdxf generan `DIMENSION` reales; la
  medida se recupera con `Dimension.get_measurement()` (40.0, 6.0 y 40.447 mm en el
  spike), lo que permite probar AC2 contra `caja_mm` y la geometría.

**Veredicto: el alcance no cambia.** Se mantiene el tamaño L con cotas por arista y
capa de ocultas; nada del enfoque declarado se invalida.

## 3. Arquitectura

1. `src/m2_cad/plano_dxf.py` (nuevo, SPEC-043): dado el `ensamble` construido y su
   `caja_mm`, produce el DXF completo en un archivo:
   - proyecta con HLR las tres vistas (`frontal` = dirección `(0, 1, 0)`, `superior` =
     `(0, 0, 1)`, `lateral` = `(1, 0, 0)`);
   - coloca cada vista en su propio recuadro de la hoja sin superposición, trasladando
     las entidades por el offset de la vista;
   - escribe aristas en capas separadas por tipo: `ARISTAS-VISIBLES` (línea continua) y
     `ARISTAS-OCULTAS` (línea discontinua, RF-2);
   - añade las **cotas generales** por vista (RF-3): la proyección de `caja_mm` en el
     plano de la vista, así las cotas quedan coherentes con la verificación (AC2);
   - añade **cotas por arista** (RF-3) para cada arista recta visible, desduplicada por
     sus extremos redondeados y numerada con un offset escalonado para reducir choques
     de texto (alcance honesto: el posicionado puede traslaparse en piezas con muchas
     aristas; una disposición automática completa es alcance de SPEC-049);
   - deja un marco con el rótulo de cada vista y la marca de diseño preliminar, coherente
     con la regla de dominio «toda salida declara que es preliminar».
2. `src/m2_cad/pipeline.py`: `construir_pieza` escribe `pieza.dxf` junto a STEP/GLB/CSV y
   `ResultadoPieza` gana el campo `dxf: Path`; `a_respuesta()` lo incluye (cambio
   aditivo del contrato).
3. `src/m2_cad/api.py`: `descargar_archivo` amplía la allowlist a
   `{"step", "glb", "csv", "dxf"}` con `media_type: image/vnd.dxf` (RF-4); el resto del
   canal de SPEC-037 (token `X-Download-Token`, propiedad del dueño, restricción a
   `outputs/`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`) se conserva
   sin cambios.
4. `src/m2_cad/versiones.py` recibe el DXF en la lista de artefactos de la versión.
5. Frontend: `Format` gana `'dxf'` y la vista de resultados ofrece la descarga junto a
   STEP/GLB/CSV; los tipos generados se regeneran desde el contrato.

`ezdxf` pasa a dependencia directa (`uv add ezdxf`): ya era transitiva de `build123d`,
pero el import propio exige declararla.

## 4. Componentes

| Archivo | Responsabilidad |
|---|---|
| `src/m2_cad/plano_dxf.py` | HLR, capas, vistas en hoja y cotas del DXF (RF-1..RF-3) |
| `src/m2_cad/pipeline.py` | Escribir el DXF y exponerlo en `ResultadoPieza` |
| `src/m2_cad/api.py` | Allowlist y MIME de la descarga DXF (RF-4) |
| `src/m2_cad/versiones.py` | DXF en la lista de artefactos de la versión (HU-35) |
| `frontend/src/api.ts` | `Format` incluye `'dxf'` |
| `contracts/openapi-v1.json` + `frontend/src/generated/api.ts` | Regenerados (HU-27/HU-31) |
| `tests/test_plano_dxf.py` | Pruebas del núcleo (AC1, AC2, RF-1..RF-3) |
| `tests/test_api.py`, `tests/test_pipeline.py` | Canal de descarga (AC3) y no regresión |

## 5. Capas y convenciones del DXF

| Capa | Contenido |
|---|---|
| `ARISTAS-VISIBLES` | aristas proyectadas visibles, línea continua |
| `ARISTAS-OCULTAS` | aristas proyectadas ocultas, línea discontinua |
| `COTAS` | cotas generales y por arista |
| `ROTULO` | marco y rótulos de vista con la marca preliminar |

Las vistas se ordenan en la hoja como en un plano tradicional: frontal abajo a la
izquierda, superior arriba a la izquierda y lateral derecha de la frontal. Unidades en
mm; el texto de las cotas en mm sin sufijo.

## 6. Contrato HTTP

La ruta `/v1/generaciones/{solicitud_id}/archivos/{formato}` acepta `formato=dxf` con
las mismas garantías del canal de SPEC-037: 403 sin token válido, 410 expirado, 404 si
no está verificado o el archivo no existe, y sólo archivos bajo `outputs/`. El cuerpo de
respuesta es `FileResponse` con `image/vnd.dxf` y `filename=pieza.dxf`. El resto de la
API no cambia; el contrato congelado se regenera con el cambio aditivo de `dxf` en la
respuesta de generación y el literal del `formato`.

## 7. Estrategia de pruebas

Test-first (RED → GREEN), patrón AAA, sin red, API key ni GPU:

- AC1: DXF generado se relee con ezdxf, la auditoría no reporta errores y el documento
  contiene las tres vistas (contando entidades por recuadro) y las capas visibles y
  ocultas.
- AC2: cotas generales iguales a `caja_mm` (proyectadas por vista) y cotas por arista
  iguales a la longitud de la arista de origen, dentro de la tolerancia declarada
  (±0.05 mm por redondeo y discretización).
- AC3: descarga `dxf` por el canal de artefactos con token, y 404 antes de verificar /
  sin token; no regresión: STEP/GLB/CSV siguen descargándose igual.
- RF-1..RF-3 sobre el núcleo: tres vistas presentes, capas separadas, cotas por arista
  presentes para una placa y ausentes para una esfera (no hay arista recta).
- RNF-1: el mismo programa produce el mismo DXF byte a byte.
- RNF-3: el CSV de materiales y el STEP/GLB no cambian de contenido.

## 8. Alcance honesto

- Las cotas por arista se limitan a aristas rectas visibles; superficies curvas sólo
  llevan cotas generales. La acotación completa de fabricación es SPEC-049.
- Sin PDF ni cajetín (SPEC-044) ni edición del DXF en la UI.
- La apertura en un visor CAD estándar (AC1) queda como verificación manual
  complementaria; la prueba automatizada usa `ezdxf` y su auditoría.
