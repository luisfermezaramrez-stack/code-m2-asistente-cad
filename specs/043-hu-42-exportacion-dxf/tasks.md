# HU-42 — Seguimiento de tareas

## Fase 1. Análisis y planificación

- [x] Revisar SPEC-043 y el alcance de AC1–AC3 (RF-1..RF-4).
- [x] Correr el spike declarado: HLR → entidades DXF y recuperación de aristas ocultas.
- [x] Confirmar que el alcance no cambia (tamaño L; ver `plan.md` §2).
- [x] Redactar y documentar el diseño técnico en `plan.md`.

## Fase 2. Núcleo del plano DXF

- [ ] Crear `src/m2_cad/plano_dxf.py`.
- [ ] Acotar la dependencia directa `ezdxf` en `pyproject.toml`/`uv.lock`.
- [ ] Proyección HLR de las tres vistas (frontal, superior, lateral).
- [ ] Capas `ARISTAS-VISIBLES` y `ARISTAS-OCULTAS` (RF-2).
- [ ] Cotas generales coherententes con `caja_mm` y cotas por arista (RF-3, AC2).
- [ ] Recuadros de vista sin superposición y rótulo preliminar.

## Fase 3. Pipeline y canal de artefactos

- [ ] `construir_pieza` escribe `pieza.dxf` (RNF-3: STEL/GLB/CSV intactos).
- [ ] `ResultadoPieza.dxf` y `a_respuesta()` (contrato aditivo).
- [ ] Allowlist `dxf` + MIME `image/vnd.dxf` en `descargar_archivo` (RF-4, AC3).
- [ ] DXF en la lista de artefactos de `versiones.registrar_version`.

## Fase 4. Frontend y contrato

- [ ] `Format` incluye `'dxf'` en `frontend/src/api.ts`.
- [ ] Botón de descarga DXF en la vista de resultados.
- [ ] Regenerar `contracts/openapi-v1.json` y `frontend/src/generated/api.ts`.
- [ ] `make api-contract-check` y `make api-types-check` en verde.

## Fase 5. Pruebas (RED → GREEN, patrón AAA)

- [ ] AC1: auditoría ezdxf limpia + tres vistas + capas visibles/ocultas.
- [ ] AC2: cotas generales = `caja_mm`; cotas por arista = longitud de arista.
- [ ] AC3: descarga `dxf` con token; 403 sin token; 404 sin verificación.
- [ ] No regresión: STEP/GLB/CSV siguen descargándose por el mismo canal.
- [ ] RNF-1: el mismo programa produce el mismo DXF.
- [ ] Cobertura ≥ 70 %, Ruff y suite completa en verde.

## Fase 6. Documentación y entrega

- [ ] `docs/` actualizado (entrega DXF y nueva variable/no-variable según aplique).
- [ ] `specs/README.md`: fila 043 con la PR de entrega.
- [ ] `CONSTITUTION.md` con la decisión técnica y la dependencia `ezdxf` directa.
- [ ] Commits por unidad con Conventional Commits en español.
- [ ] `evidence.md` con resultados verificables.
- [ ] Abrir PR hacia `main` (fuera del alcance de esta sesión; veredicto queda en el repo).

## Criterios de cierre

- AC1: el DXF abre con auditoría limpia y contiene las tres vistas y sus dos capas.
- AC2: cotas generales y por arista dentro de la tolerancia frente a la verificación.
- AC3: la descarga del DXF va por el canal de artefactos de SPEC-037.
- RNF-3: la salida STEP/GLB/CSV existente no cambia.
- Las pruebas no requieren API keys, red externa ni GPU.
