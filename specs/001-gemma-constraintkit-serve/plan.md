# Implementation Plan: Servir Gemma 4 12B ConstraintKit (HU-01)

**Branch**: `001-gemma-constraintkit-serve` | **Date**: 2026-11-03 | **Spec**: `specs/001-gemma-constraintkit-serve/spec.md`

**Input**: Feature specification from `/specs/001-gemma-constraintkit-serve/spec.md`

## Summary

Dejar servido el modelo Gemma 4 12B ConstraintKit (GGUF Q6_K) con llama.cpp y el contenedor de constraint-kit operativo en la GPU alquilada, verificando integridad (SHA-256), límite de VRAM (≤ 16 GB), suite del contenedor (113/113) y una prueba end-to-end (5/5 programas pasan `/dsl/check`). Sin reentrenamiento: el modelo se consume tal como lo publicó su autor.

## Technical Context

**Language/Version**: Python 3.12 (en contenedor Docker; constraint del proyecto M2)

**Primary Dependencies**: llama.cpp (servido GGUF), constraint-kit (CadQuery 2.7.0, build123d 0.10.0, bd_warehouse 0.2.0, OpenCascade, python-solvespace)

**Storage**: Pesos GGUF Q6_K (9,8 GB) en disco de la GPU alquilada (ignorados por git)

**Testing**: suite del contenedor (113 pruebas) + 5 solicitudes de humo contra `/dsl/check`

**Target Platform**: Linux + GPU alquilada (≥ 16 GB VRAM)

**Project Type**: servicio de inferencia + contenedor de motor geométrico

**Performance Goals**: modelo cargado con 8 192 tokens de contexto; VRAM ≤ 16 GB

**Constraints**: sin reentrenamiento; contenedor del autor sin modificar (fuera de él fallan 27/113); Python 3.12 (no 3.13)

**Scale/Scope**: 1 instancia de inferencia para el sprint de 15 días; DeepSeek como plan B

## Constitution Check

*GATE: convención del proyecto M2 — `uv`/`uv.lock`, src-layout, sin `pip install` ni `requirements.txt`; el núcleo CAD va fijado (cadquery 2.7.0, build123d 0.10.0, bd_warehouse 0.2.0). Los pesos (`.gguf`) nunca se versionan (ya en `.gitignore`).*

## Project Structure

### Documentation (this feature)

```text
specs/001-gemma-constraintkit-serve/
├── spec.md              # Feature spec (HU-01)
├── plan.md              # Este archivo
└── tasks.md             # Actividades (salida de /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2_cad/              # código propio del equipo (stubs actuales)
data/                    # banco de solicitudes (HU-02)
models/                  # pesos GGUF — gitignoreado (no se crea en este repo)
```

**Structure Decision**: el modelo y el contenedor viven en la GPU alquilada, fuera del repo; el repo solo guarda el código propio (`src/m2_cad/`) y la documentación. No se añaden módulos nuevos en esta HU: es infraestructura de entorno.

## Complexity Tracking

*(Sin violaciones a la constitución: no se añade proyecto, patrón ni dependencia nueva al código del repo.)*
