# HU-42 — Evidencia de la exportación DXF (SPEC-043)

Fecha: 2026-11-28 · Rama: `feature/hu-42-exportacion-dxf` · Base: `main` (`f7b117d`)

## Verificación

| Comprobación | Comando | Resultado |
| --- | --- | --- |
| Núcleo del plano DXF (AC1, AC2, RF-1..RF-3, RNF-1, RNF-3) | `pytest tests/test_plano_dxf.py` | 10 pasan |
| Canal de descargas con DXF (AC3, RF-4, no-regresión HTTP) | `pytest tests/test_hu42_canal_dxf.py` | 8 pasan |
| No regresión del pipeline | `pytest tests/test_pipeline.py` | todas pasan |
| Suite completa de Python | `pytest` con `M2_DOWNLOAD_SECRET` efímero (como en CI) | 796 pasan |
| Contrato OpenAPI congelado | `make api-contract-check` | ok (sin diff: cambio aditivo runtime) |
| Tipos TypeScript desde OpenAPI | `make api-types-check` | ok (sin diff) |
| Vitest (117 pruebas, incluida la del botón DXF) | `npx vitest run` | 117 pasan |
| Lint Ruff + verificación completa | `make check` | **EXIT=0** (2026-11-28): 796 pytest, cobertura **91,09 %** (≥ 70 %), Vitest 117, TS, build y docs estrictos |

## Cobertura de criterios por prueba

- AC1 → `test_ac1_auditoria_limpia_y_capas` (auditoría ezdxf sin errores, capas declaradas).
- AC2 → `test_ac2_cotas_generales_igual_caja_mm`, `test_ac2_dimension_reporta_la_medida`,
  `test_ac2_medidas_dentro_de_la_caja`.
- AC3 → `test_ac3_*` y `test_canal_sigue_sirviendo_todos_los_formatos` en
  `tests/test_hu42_canal_dxf.py` (200 con token, 403 sin token/ajeno, 410 expirado,
  404 sin verificación o formato desconocido).
- RF-1 → `test_rf1_tres_vistas_rotuladas`; RF-2 → `test_rf2_*`; RF-4 → allowlist/MIME
  de `descargar_archivo`.
- RNF-1 → `test_rnf1_mismo_programa_mismo_dxf` (bytes iguales con metadatos fijos).
- RNF-3 → `test_rnf3_step_glb_csv_intactos` (hashes de STEP/GLB/CSV sin cambiar).

## Apertura en visor CAD estándar (AC1, verificación manual)

El DXF de la placa 40×20×6 se reabre con ezdxf (auditoría limpia) y contiene las
capas `ARISTAS-VISIBLES`, `ARISTAS-OCULTAS`, `COTAS` y `ROTULO` con las tres vistas
rotuladas. La verificación en visor externo (QCAD/FreeCAD) queda como comprobación
manual complementaria al fusionar (el AC se declara satisfecho por auditoría ezdxf
según el plan, §7).

## Archivos creados/modificados

- `src/m2_cad/plano_dxf.py` (nuevo), `pipeline.py`, `api.py`, `__init__.py`,
  `pyproject.toml`/`uv.lock` (`ezdxf` directa).
- `frontend/src/api.ts`, doble de pruebas Vitest, contrato y tipos regenerados.
- `tests/test_plano_dxf.py`, `tests/test_hu42_canal_dxf.py` (nuevos).
- Docs: `README.md`, `AGENTS.md`, `CONSTITUTION.md`, `specs/README.md`,
  `docs/spikes/hu-42-dxf.md`, `spec/plan/tasks` de SPEC-043.
