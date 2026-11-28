# HU-43 — Evidencia de la exportación PDF (SPEC-044)

Fecha: 2026-11-28 · Rama: `feature/hu-43-exportacion-pdf` · Base: `main` (`6dc06f5`, con HU-42 ya fusionada en PR #160)

## Verificación

| Comprobación | Comando | Resultado |
| --- | --- | --- |
| Núcleo del plano PDF (AC1, AC2, AC3, RF-1, RF-3, RF-4, RNF-1, RNF-4) | `pytest tests/test_plano_pdf.py` | 13 pasan |
| Canal de descargas con PDF (RNF-3, no-regresión HTTP) | `pytest tests/test_hu43_canal_pdf.py` | 10 pasan |
| No-regresión del canal DXF de SPEC-043 | `pytest tests/test_plano_dxf.py tests/test_hu42_canal_dxf.py` | todas pasan |
| Suite completa de Python | `pytest` con `M2_DOWNLOAD_SECRET` efímero (como en CI) | 825 pasan |
| Botón PDF en la SPA | `npx vitest run` | 118 pasan (incluida la del botón PDF) |
| Lint Ruff + verificación completa | `make check` | ver cierre de esta tarjeta (make check final) |

## Cobertura de criterios por prueba

- AC1 → `test_ac1_pagina_del_tamano_declarado_con_margen` (a4/a3 con `pypdf`,
  MediaBox exacto) y `test_ac1_contenido_dentro_del_margen` (vistas y cajetín
  dentro de la página menos 10 mm).
- AC2 → `test_ac2_cajetin_completo` (líneas del cajetín) y
  `test_rf2_cajetin_leible_en_el_pdf` (texto extraído con `pypdf`).
- AC3 → `test_ac3_relacion_de_la_cota_coherente_con_la_escala` (longitud dibujada
  de la cota / medida real = 1/den, ±1 %) y `test_rf3_declaracion_de_escala`.
- RF-1 → `test_rf1_tres_vistas_de_spec043` (reutiliza HLR y cotas de `plano_dxf`,
  más la marca preliminar); RF-4 → `test_rf4_formato_ajeno_rechazado` (solo A4/A3)
  y `test_rnf4_matplotlib_directa_en_pyproject`.
- RNF-1 → `test_rnf1_bytes_identicos_con_la_misma_fecha` (mismos bytes con la
  misma fecha inyectada; cambian con otra fecha; metadatos PDF fijos).
- RNF-3 → `tests/test_hu43_canal_pdf.py`: PDF 200 con MIME `application/pdf` y
  cabeceras del canal, sin token 403, token ajeno 403, token expirado 410,
  formato ajeno 404, sin verificación 404; no-regresión STEP/GLB/CSV/DXF
  (el DXF conserva su MIME `image/vnd.dxf`); bytes GLB/CSV/DXF intactos con el
  `test_no_regresion_glb_csv_dxf_con_pdf`.
- Pipeline → `test_pipeline_genera_pdf_y_existe` (`pieza.pdf` junto a los demás
  entregables y campo `pdf` añadido a `a_respuesta()`).

## Decisiones registradas

- Dependencia: `matplotlib>=3.11.2` promovida de transitiva (por `vtk`) a directa
  (RNF-4). Licencia PSF-like compatible; cero bytes nuevos en el lock. `pypdf`
  queda solo como verificador en pruebas.
- Determinismo (RNF-1): metadatos PDF fijos (`CreationDate` nulo, `Producer`
  propio); la única huella variable admisible es la fecha del cajetín, inyectable
  en `plano_pdf.escribir` y `paquete`.
- Reutilización estricta: las vistas HLR (`proyeccion_hlr`, `polilinea_de`) y los
  valores de cotas (`cotas_generales_de_vista`, `MARCA_PRELIMINAR_PLANO`) vienen
  de `plano_dxf` (SPEC-043); no hay proyección ni cotas reimplementadas.
