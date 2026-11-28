# HU-43 — Plan técnico de exportación PDF con cotas (SPEC-044)

## 1. Objetivo

Entregar un plano imprimible en PDF con las vistas acotadas de SPEC-043, un cajetín con
material, masa, fecha e id de solicitud (RF-2), la escala declarada (RF-3) y formatos
A4 y A3 sin recortes (RF-4), servido por el mismo canal de artefactos de SPEC-037
(RNF-3), sin cambiar STEP/GLB/CSV/DXF (no-regresión).

## 2. Dependencia de generación de PDF (RNF-4, decisión)

La spec pide evaluar promover una transitiva antes de sumar un paquete nuevo.

- **`matplotlib` 3.11.2 ya está en `uv.lock`** (transitiva por `vtk`) e incluye un
  backend PDF vectorial multipágina. Zero paquetes nuevos en el lock.
  - **Licencia:** PSF-like (*BSD compatible, matplotlib license based on PSF*),
    compatible con la MIT del propio código (CONSTITUTION §12 no la lista como
    copyleft y es la misma familia de licencia permisiva).
  - **Impacto en la imagen:** **cero**. El paquete y todas sus dependencias
    (`numpy`, `pillow`, `fonttools`, `kiwisolver`, `cycler`, `pyparsing`,
    `contourpy`) ya están presentes por `vtk`; declararla directa no añade bytes.
- `pypdf` 6.21.4 también está transitivo (aún sin promover, otro extra del kit), pero
  es un lector/manipulador de PDF, no un generador vectorial: queda solo para las
  pruebas (verificación de página y de cajetín), como ya lo usa `constraint-kit` para
  extraer texto.
- **Decisión: `uv add matplotlib`** (promoción a directa, lock sin cambios de árbol).

## 3. Arquitectura

1. `src/m2_cad/plano_dxf.py`: se exponen públicamente los dos helpers puros que el PDF
   reutiliza — `polilinea_de(arista)` (antes `_polilinea_de`) y `extremos_de(arista)`
   (antes `_extremos_de`), más `proyeccion_hlr`, `cotas_generales_de_vista` y
   `MARCA_PRELIMINAR_PLANO` — sin cambiar su comportamiento (los DXF de las pruebas
   existentes siguen pasando byte a byte).
2. `src/m2_cad/plano_pdf.py` (nuevo, SPEC-044): dado el `ResultadoPieza`, el id de
   solicitud y las métricas del builder (`partes`), dibuja una hoja vectorial:
   - Tamaños A4 (210×297 mm) y A3 (297×420 mm) en orientación horizontal, margen 10 mm
     (supuesto del AC1). La escala del bloque de vistas se elige automáticamente por
     serie (1:1, 1:2, ... hasta encajar dentro del margen) y se escribe en el cajetín
     (RF-3, AC3).
   - Dibuja las tres vistas HLR de SPEC-043 reusando `proyeccion_hlr`/`polilinea_de`
     (RF-1), con línea continua para visibles y discontinua para ocultas.
   - Cajetín en la esquina inferior derecha (RF-2): material (suma de los materiales
     distintos de las partes), masa total en g (`mass_g` del builder), fecha
     (`AAAA-MM-DD`, inyectable para el determinismo de RNF-1), id de solicitud,
     marca preliminar, escala y formato.
3. `src/m2_cad/pipeline.py`: `construir_pieza` escribe `pieza.pdf` junto a los otros
   cuatro entregables; `ResultadoPieza.pdf` es campo aditivo (`Path | None`, igual
   patrón que `dxf`) y `a_respuesta()` lo incluye cuando existe. El id de solicitud viaja
   por nuevo parámetro opcional `solicitud_id` (default vacío = "—" en el cajetín),
   llenado por `api.py` desde el trabajo.
4. `src/m2_cad/api.py`: allowlist de `descargar_archivo` gana `"pdf"` con
   `media_type="application/pdf"`, y los artefactos de la versión incluyen `resultado.pdf`.
5. Frontend: `Format` gana `'pdf'`; el doble `fakeCadService` lo sirve; Vitest cubre el
   botón de descarga. El contrato OpenAPI congelado no cambia (literal `formato` libre
   y `resultado` `dict[str,str]`, igual que en HU-42).

## 4. Componentes

| Archivo | Responsabilidad |
|---|---|
| `src/m2_cad/plano_dxf.py` | Exposición pública de `polilinea_de`, `extremos_de` (sin cambios de comportamiento) |
| `src/m2_cad/plano_pdf.py` | Vistas+cajetín+escala del PDF (RF-1..RF-3, AC1..AC3) |
| `src/m2_cad/pipeline.py` | Escribir el PDF y exponerlo (campo `pdf`, `solicitud_id`) |
| `src/m2_cad/api.py` | Allowlist `pdf` + MIME `application/pdf` (RF-4, RNF-3) |
| `frontend/src/api.ts` | `Format` incluye `'pdf'` |
| `contracts/` y `frontend/src/generated/` | Sin cambios (canonicalizados igual que en HU-42) |
| `tests/test_plano_pdf.py` | Pruebas del núcleo PDF (AC1..AC3, RF-1..RF-3, RNF-1) |
| `tests/test_hu43_canal_pdf.py` | Canal de descarga (AC3/RNF-3) y no-regresión HTTP |

## 5. Convenciones del PDF

- Hoja horizontal (A4 paisaje: 297×210 mm; A3 paisaje: 420×297 mm) en pértigas de mm;
  la conversión a puntos la hace matplotlib (1 pt = 1/72 in, `1 mm = 2.83465 pt`).
- Bloque de vistas arriba-izquierda; el cajetín abarca ~80 mm y se sitúa a la
  inferior-derecha, alineado al borde del margen (convención de plano).
- La fecha del cajetín es `datetime.date.today()` en producción y pasada por parámetro
  en las pruebas (RNF-1: determinista salvo la fecha del cajetín).

## 6. Contrato HTTP

`/v1/generaciones/{solicitud_id}/archivos/{formato}` acepta `formato=pdf` con las
garantías de SPEC-037: token, 403 sin token, 410 expirado, 404 sin verificación o
formato desconocido, restricción a `outputs/`, `Cache-Control: no-store` y
`X-Content-Type-Options: nosniff`. Cuerpo `FileResponse` con `application/pdf` y
`filename=pieza.pdf`.

## 7. Estrategia de pruebas

Test-first (RED → GREEN), patrón AAA, sin red, API key ni GPU:

- AC1: `pypdf` lee cada PDF (A4 y A3) y pasa los dos tamaños con margen (caja envolvente
  del contenido dibujable dentro de la página — la caja se toma del MediaBox y del
  recinto del bloque animal con el cajetín).
- AC2: leemos el texto con `pypdf` del PDF del corpus (mismo builder real, sin red) y
  el cajetín contiene material, masa, fecha e id de solicitud.
- AC3: la relación «longitud de página entre longitud real» para una cota general cae
  por serie y coincide con la escala escrita en el cajetín (tolerancia ±1 %).
- RF-1..RF-3 sobre el núcleo: las tres vistas están; el cajetín declara escala y
  formato; el PDF aparte repite las vistas acotadas de SPEC-043.
- RNF-1: el mismo programa con la misma fecha produce bytes idénticos.
- RNF-3: la descarga del PDF va por el canal con token, y no-regresión: STEP/GLB/CSV/DXF
  siguen servidos y STEP/GLB/CSV intactos (hashes).
- RNF-4: fallback documentado en pyproject con licencia y peso (verificación de sync en
  `evidence.md`, no una prueba unitaria).

## 8. Alcance honesto

- La escala se elige por serie entera (1:1, 1:2, 1:5...) para que las cotas de page
  mm verificados por regla correspondan a la escala declarada. Sin escala exótica.
- Sin plantillas de cajetín personalizables (fuera de alcance, especificado).
- La impresión física sin recortes y con regla es verificación manual (la declaración
  del AC1/AC3 es su versión en puntos, no en impresión física).
- El bloque de vistas en PDF replica capas dibujadas: sin especificar el orden exacto
  a nivel pixel; la geometría y las cotas vienen de SPEC-043.
