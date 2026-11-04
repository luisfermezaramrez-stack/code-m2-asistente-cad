# Implementation Plan: Declinación y marca "preliminar" (HU-05)

**Branch**: `003-declinacion-preliminar` | **Date**: 2026-11-03 | **Spec**: `specs/003-declinacion-preliminar/spec.md`

**Input**: Feature specification from `/specs/003-declinacion-preliminar/spec.md`

## Summary

Añadir al pipeline la declinación con motivo en español para piezas fuera del catálogo (sin STEP) y la marca "diseño preliminar" en toda salida (interfaz y STEP), con prueba automática que cubre los tres casos.

## Technical Context

**Language/Version**: Python 3.12 · `src/m2_cad/pipeline.py` (declinación), `src/m2_cad/interfaz.py` (marca en UI)

**Primary Dependencies**: constraint-kit (declinación del DSL), Gradio (marca en interfaz)

**Testing**: pytest · `tests/test_pipeline.py`

**Target Platform**: Linux + GPU alquilada

**Project Type**: pipeline de generación CAD

**Constraints**: verificación solo geométrica; la marca "preliminar" es obligatoria en toda salida

**Scale/Scope**: banco de 10 solicitudes fuera de catálogo (HU-02)

## Constitution Check

*GATE: src-layout, uv/pytest/Ruff. La declinación se escribe en español (motivo legible por el ingeniero).*

## Project Structure

```text
src/m2_cad/
├── pipeline.py        # declinación (motivo en español) + marca en STEP
└── interfaz.py        # marca "preliminar" en la UI Gradio

tests/
└── test_pipeline.py   # 3 casos de declinación/marca
```

**Structure Decision**: la lógica de declinación vive en `pipeline.py`; la marca en UI en `interfaz.py`.

## Complexity Tracking

*(Sin violaciones.)*
