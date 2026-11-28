# HU-43 — Seguimiento de tareas

## Fase 1. Análisis y planificación

- [x] Revisar SPEC-044 (RF-1..RF-4, RNF-1..RNF-4, AC1..AC3).
- [x] Verificar premisa de dependencia: `matplotlib` 3.11.2 transitiva en `uv.lock`, PSF-like, cero bytes nuevos.
- [x] Redactar el plan técnico (`plan.md`) y este seguimiento.

## Fase 2. Núcleo del plano PDF

- [x] Exponer `polilinea_de`/`extremos_de` en `plano_dxf.py` (sin cambio de comportamiento). — 9316c9f
- [x] Crear `src/m2_cad/plano_pdf.py`: A4/A3, margen 10 mm, escala por serie. — 5b4442b
- [x] Cajetín: material, masa, fecha, id de solicitud, marca preliminar (RF-2). — 5b4442b
- [x] Declarar la escala elegida en el cajetín (RF-3). — 5b4442b
- [x] `uv add matplotlib` en `pyproject.toml`/`uv.lock`. — ae706aa

## Fase 3. Pipeline y canal de artefactos

- [x] `construir_pieza` escribe `pieza.pdf` y acepta `solicitud_id` (opcional). — 9f226ff (el id lo inyecta quien llama')
- [x] `ResultadoPieza.pdf` y `a_respuesta()` (contrato aditivo). — 9f226ff
- [x] Allowlist `pdf` + MIME `application/pdf` (RNF-3). — 09d21fe
- [x] PDF en la lista de artefactos de la versión (HU-35). — 16a517b

## Fase 4. Frontend y contrato

- [x] `Format` incluye `'pdf'` en `frontend/src/api.ts`. — 97812a4
- [x] Doble `fakeCadService` con el formato `pdf`. — 97812a4
- [x] Prueba Vitest del botón de descarga PDF. — 97812a4 (118 pruebas ok, typecheck y build ok)

## Fase 5. Pruebas (RED → GREEN, patrón AAA)

- [x] AC1: tamaño A4 y A3 exactos, contenido dentro del margen (pypdf). — tests/test_plano_pdf.py
- [x] AC2: cajetín con material, masa, fecha e id de solicitud (pypdf). — tests/test_plano_pdf.py
- [x] AC3: relación medida/real coincide con la escala declarada (±1 %). — tests/test_plano_pdf.py
- [x] RNF-1: mismos bytes con la misma fecha inyectada. — tests/test_plano_pdf.py
- [x] RNF-3: descarga por canal con token; no-regresión HTTP de STEP/GLB/CSV/DXF. — tests/test_hu43_canal_pdf.py
- [x] No-regresión de bytes: GLB/CSV/DXF no cambian al generar el PDF. — c9c2ba9 (el STEP de build123d varía por marca de tiempo; se comparan corridas congenéreas)
- [x] `make check` verde con secreto de descargas exportado. — pytest 825, cobertura 91,09 %

## Fase 6. Documentación y entrega

- [x] `CONSTITUTION.md`: stack con `matplotlib` y entregable PDF, decisión historizada.
- [x] `README.md`: entregable PDF (AGENTS.md no menciona entregables concretos; sin cambio).
- [x] `specs/README.md`: fila 044 actualizada (estado "En revisión").
- [x] `evidence.md` con resultados verificables.
- [x] Commits por unidad con Conventional Commits en español (sin atribución IA).
- [ ] Abrir PR hacia `main` (decisión del usuario; fuera de esta sesión).

## Criterios de cierre

- AC1: páginas A4/A3 exactas, sin recortes de contenido (verificación física manual aparte).
- AC2: cajetín completo en el 100 % de los PDF.
- AC3: escala declarada coincide con la relación dibujado/real en ±1 %.
- RNF-1: determinista salvo la fecha del cajetín; RNF-2: sin red/API key/GPU.
- RNF-3: descarga por el canal de SPEC-037; RNF-4: dependencia con licencia y peso documentados.

## Revisión (post-primer informe)

- [x] B1: el cajetín lleva el id real de la solicitud por la cadena
  `generar_pieza`/`editar_pieza` → `construir_pieza` → `plano_pdf.escribir`,
  con retrocompatibilidad (el id entra por parámetro o por el contexto
  `job_id` que fijan las rutas SSE (`trabajos.py`), el worker (`worker.py`) y
  las rutas JSON; los dobles históricos de pruebas no cambian). — test_hu43_solicitud_id.py
- [x] B2: merge con `origin/main` (HU-48, PR #161, `55db05d`); conservados el
  guard de materiales (`verificar_programa` → `validar_materiales`) y
  `plano_pdf`; el cajetín muestra el material canónico (`al` → `aluminum`). — test_hu43_solicitud_id.py
