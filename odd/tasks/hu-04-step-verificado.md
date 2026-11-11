# HU-04 · Pieza STEP verificada

Objective: implement the generation pipeline (program → constraint-kit verifier → STEP + GLB + BOM CSV, with timing) in `src/m2_cad/pipeline.py`.
Branch: `feature/hu-04-step-verificado` (from `origin/develop`) · Delivery: ask-on-risk · Runner: `uv run pytest` (+ `uv run ruff check src tests`).

## Specs

Source: GitHub issue #4 and `specs/002-step-verificado/`.

- S1 (AC1): "el programa generado pasa el verificador de constraint-kit sin errores."
- S2 (AC2): "el STEP abre en FreeCAD sin advertencias de geometría."
- S3 (AC3): "en 5 casos de prueba, volumen y caja envolvente quedan dentro de ±2 % del valor esperado."
- S4 (AC4): "cada respuesta entrega STEP, GLB y lista de materiales en CSV."
- S5 (AC5): "el tiempo de generación y construcción queda registrado por solicitud."

Assumptions (not user-stated):
- A1: FreeCAD and Blender are not installed locally; S2 is checked with the OpenCascade STEP reader/shape validity in tests, and the real FreeCAD check is a manual validation step.
- A2: the GLB is exported from the B-rep without Blender unless the explorer finds a constraint-kit path that requires it.
- A3: the LLM (HU-01 served model) is injected; tests use deterministic programs, no network.

## Tasks

| ID | Specs | Route | Status | Evidence |
|----|-------|-------|--------|----------|
| T1 | S1 | inline | done | cff998f · RED 16 failed → GREEN 16 passed |
| T2 | S2, S4 | inline | done (S2 FreeCAD manual pending) | cff998f |
| T3 | S3 | inline | done | cff998f · 5 analytic cases |
| T4 | S5 | inline | done | cff998f |
| T5 | S1-S5 | inline | done | API commit · RED 3 failed on base api.py → GREEN |

Route evidence: no Writer trigger (single dependent unit of behavior); mapping trigger fired once (constraint-kit API) → one read-only explorer.

## Log

- L1 (2026-11-10, user): "implementa la HU-04 en una nueva rama a partir de develop"
- L2: context — issue #4 was closed by PR #29 (registro de solicitudes) although `pipeline.py` held only a docstring; HU-05 is blocked on this work.
- L3: local env check — constraint_kit, build123d, cadquery, OCP, trimesh import OK; FreeCAD and Blender absent. `data/test_cases.csv` has only its header (HU-02 pending).
- L4: A2 confirmed — `builder.export` writes GLB via `cadquery-gltf`, no Blender. Spacer volume 1256.6371 mm³ equals the analytic value.
- L5: unrequested change dropped — filling `registro.traduccion` from the pipeline (suggest it separately for HU-06 metrics).
- L6: full suite 62 passed, coverage 92 %, ruff check OK. `tests/test_api.py` was already not ruff-formatted at base (pre-existing).
- Next: real end-to-end validation on the GPU instance (Spanish request → STEP/GLB/CSV) and open the STEP in FreeCAD (S2).
