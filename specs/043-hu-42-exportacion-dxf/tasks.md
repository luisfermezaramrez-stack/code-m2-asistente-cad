# HU-42 — Seguimiento de tareas

## Fase 1. Análisis y planificación

- [x] Revisar SPEC-043 y el alcance de AC1–AC3 (RF-1..RF-4).
- [x] Correr el spike declarado: HLR → entidades DXF y recuperación de aristas ocultas (`docs/spikes/hu-42-dxf.md`).
- [x] Confirmar que el alcance no cambia (tamaño L; ver `plan.md` §2).
- [x] Redactar y documentar el diseño técnico en `plan.md`.

## Fase 2. Núcleo del plano DXF

- [x] Crear `src/m2_cad/plano_dxf.py`.
- [x] Acotar la dependencia directa `ezdxf` en `pyproject.toml`/`uv.lock`.
- [x] Proyección HLR de las tres vistas (frontal, superior, lateral).
- [x] Capas `ARISTAS-VISIBLES` y `ARISTAS-OCULTAS` (RF-2).
- [x] Cotas generales coherentes con `caja_mm` y cotas por arista (RF-3, AC2).
- [x] Recuadros de vista sin superposición y rótulo preliminar.

## Fase 3. Pipeline y canal de artefactos

- [x] `construir_pieza` escribe `pieza.dxf` (RNF-3: STEP/GLB/CSV intactos).
- [x] `ResultadoPieza.dxf` y `a_respuesta()` (contrato aditivo).
- [x] Allowlist `dxf` + MIME `image/vnd.dxf` en `descargar_archivo` (RF-4, AC3).
- [x] DXF en la lista de artefactos de la versión (HU-35).

## Fase 4. Frontend y contrato

- [x] `Format` incluye `'dxf'` en `frontend/src/api.ts`.
- [x] Botón de descarga DXF en la vista de resultados (etiquetado genérico del canal).
- [x] Regenerar `contracts/openapi-v1.json` y `frontend/src/generated/api.ts`.
- [x] Doble del backend (fakeCadService) con el formato `dxf` para Vitest.

## Fase 5. Pruebas (RED → GREEN, patrón AAA)

- [x] AC1: auditoría ezdxf limpia + capas declaradas (`test_ac1_auditoria_limpia_y_capas`).
- [x] RF-1: tres vistas rotuladas (`test_rf1_tres_vistas_rotuladas`).
- [x] RF-2: capas separadas visibles/ocultas (`test_rf2_*`).
- [x] AC2: cotas generales = `caja_mm`; medidas dentro de la caja (`test_ac2_*`).
- [x] AC3: descarga `dxf` con token; 403 sin token; 404 sin verificación (`tests/test_hu42_canal_dxf.py`).
- [x] No regresión HTTP: STEP/GLB/CSV siguen servidos (`test_canal_sigue_sirviendo_todos_los_formatos`).
- [x] RNF-1: el mismo programa produce el mismo DXF (`test_rnf1_mismo_programa_mismo_dxf`).
- [x] RNF-3: STEP/GLB/CSV intactos (`test_rnf3_step_glb_csv_intactos`).
- [x] Cobertura ≥ 70 %, Ruff y suite completa en verde (`make check`).

## Fase 6. Documentación y entrega

- [x] Spike documentado en `docs/spikes/hu-42-dxf.md`.
- [x] `README.md` y `AGENTS.md` actualizados (entrega DXF y módulo nuevo).
- [x] `CONSTITUTION.md` con la decisión técnica y la dependencia `ezdxf` directa.
- [x] `specs/README.md`: fila 043 en estado implementada.
- [x] `evidence.md` con resultados verificables.
- [x] Commits por unidad con Conventional Commits en español.
- [ ] Abrir PR hacia `main` (decisión del usuario; fuera de esta sesión).

## Criterios de cierre

- AC1: el DXF abre con auditoría limpia y contiene las tres vistas y sus capas.
- AC2: cotas generales y por arista dentro de la tolerancia frente a la verificación.
- AC3: la descarga del DXF va por el canal de artefactos de SPEC-037.
- RNF-3: la salida STEP/GLB/CSV existente no cambia.
- Las pruebas no requieren API keys, red externa ni GPU.
