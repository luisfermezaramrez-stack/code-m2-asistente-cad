# Implementation Plan: Generar pieza STEP verificada (HU-04)

**Branch**: `002-step-verificado` | **Date**: 2026-11-03 | **Spec**: `specs/002-step-verificado/spec.md`

**Input**: Feature specification from `/specs/002-step-verificado/spec.md`

## Summary

Implementar el pipeline de generación y verificación que convierte el programa constraint-kit en una pieza verificada con entregables STEP + GLB + CSV, dentro de ±2 % de tolerancia geométrica y con tiempo de generación registrado.

## Technical Context

**Language/Version**: Python 3.12 (contenedor) · código propio en `src/m2_cad/pipeline.py`

**Primary Dependencies**: constraint-kit (CadQuery, build123d, OpenCascade), Blender (GLB)

**Storage**: STEP/GLB/CSV en `outputs/` (gitignoreado) · registro en CSV (HU-06)

**Testing**: pytest · validación con FreeCAD y verificador de constraint-kit

**Target Platform**: Linux + GPU alquilada (el núcleo CAD corre en CPU)

**Project Type**: pipeline de generación CAD

**Performance Goals**: latencia p90 ≤ 60 s (objetivo 2)

**Constraints**: salida marcada "preliminar"; verificación solo geométrica (sin resistencia/NSR-10)

**Scale/Scope**: banco de 40 solicitudes (HU-02); 5 casos de tolerancia

## Constitution Check

*GATE: src-layout (`src/m2_cad/`), uv/pytest/Ruff, sin pip install. El código CAD se escribe en español (convención del repo).*

## Project Structure

```text
src/m2_cad/
├── pipeline.py        # generación + verificación + exportación STEP/GLB/CSV
└── traduccion.py      # ES→EN (HU-03)

tests/
└── test_pipeline.py   # verificación, tolerancia, entregables

outputs/               # STEP/GLB/CSV generados (gitignoreado)
```

**Structure Decision**: el núcleo vive en `src/m2_cad/pipeline.py`; los artefactos generados van a `outputs/` (no versionados).

## Complexity Tracking

*(Sin violaciones.)*
