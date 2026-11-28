# HU-43 — Seguimiento de tareas

## Fase 1. Análisis y planificación

- [x] Revisar SPEC-044 (RF-1..RF-4, RNF-1..RNF-4, AC1..AC3).
- [x] Verificar premisa de dependencia: `matplotlib` 3.11.2 transitiva en `uv.lock`, PSF-like, cero bytes nuevos.
- [x] Redactar el plan técnico (`plan.md`) y este seguimiento.

## Fase 2. Núcleo del plano PDF

- [ ] Exponer `polilinea_de`/`extremos_de` en `plano_dxf.py` (sin cambio de comportamiento).
- [ ] Crear `src/m2_cad/plano_pdf.py`: A4/A3, margen 10 mm, escala por serie.
- [ ] Cajetín: material, masa, fecha, id de solicitud, marca preliminar (RF-2).
- [ ] Declarar la escala elegida en el cajetín (RF-3).
- [ ] `uv add matplotlib` en `pyproject.toml`/`uv.lock`.

## Fase 3. Pipeline y canal de artefactos

- [ ] `construir_pieza` escribe `pieza.pdf` y acepta `solicitud_id` (opcional).
- [ ] `ResultadoPieza.pdf` y `a_respuesta()` (contrato aditivo).
- [ ] Allowlist `pdf` + MIME `application/pdf` (RNF-3).
- [ ] PDF en la lista de artefactos de la versión (HU-35).

## Fase 4. Frontend y contrato

- [ ] `Format` incluye `'pdf'` en `frontend/src/api.ts`.
- [ ] Doble `fakeCadService` con el formato `pdf`.
- [ ] Prueba Vitest del botón de descarga PDF.

## Fase 5. Pruebas (RED → GREEN, patrón AAA)

- [ ] AC1: tamaño A4 y A3 exactos, contenido dentro del margen (pypdf).
- [ ] AC2: cajetín con material, masa, fecha e id de solicitud (pypdf).
- [ ] AC3: relación medida/real coincide con la escala declarada (±1 %).
- [ ] RNF-1: mismos bytes con la misma fecha inyectada.
- [ ] RNF-3: descarga por canal con token; no-regresión HTTP de STEP/GLB/CSV/DXF.
- [ ] No-regresión de bytes: STEP/GLB/CSV/DXF no cambian al generar el PDF.
- [ ] `make check` verde con secreto de descargas exportado.

## Fase 6. Documentación y entrega

- [ ] `CONSTITUTION.md`: stack con `matplotlib` y entregable PDF, decisión historizada.
- [ ] `README.md`/`AGENTS.md`: entregable PDF y módulo nuevo.
- [ ] `specs/README.md`: fila 044 actualizada.
- [ ] `evidence.md` con resultados verificables.
- [ ] Commits por unidad con Conventional Commits en español.
- [ ] Abrir PR hacia `main` (decisión del usuario; fuera de esta sesión).

## Criterios de cierre

- AC1: páginas A4/A3 exactas, sin recortes de contenido (verificación física manual aparte).
- AC2: cajetín completo en el 100 % de los PDF.
- AC3: escala declarada coincide con la relación dibujado/real en ±1 %.
- RNF-1: determinista salvo la fecha del cajetín; RNF-2: sin red/API key/GPU.
- RNF-3: descarga por el canal de SPEC-037; RNF-4: dependencia con licencia y peso documentados.
