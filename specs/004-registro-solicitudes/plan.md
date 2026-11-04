# Implementation Plan: Registro de solicitudes de la API (HU-06 — parte de Luis Meza)

**Branch**: `004-registro-solicitudes` | **Date**: 2026-11-03 | **Spec**: `specs/004-registro-solicitudes/spec.md`

**Input**: Feature specification from `/specs/004-registro-solicitudes/spec.md`

## Summary

Implementar el módulo de registro que captura id, hora, texto, traducción, resultado, latencia, error y versión del modelo por cada solicitud, sin campos vacíos y excluyendo nombres y correos, integrado a la API FastAPI (cuya parte de endpoints es de J. C. Pérez).

## Technical Context

**Language/Version**: Python 3.12 · `src/m2_cad/registro.py` (módulo de registro)

**Primary Dependencies**: FastAPI (integración con POST /generar), pydantic (esquema del registro)

**Storage**: CSV/almacén local en `data/registro.csv` (gitignoreado) · excluye datos personales

**Testing**: pytest · `tests/test_api.py` y/o `tests/test_registro.py`

**Target Platform**: Linux + GPU alquilada

**Project Type**: servicio API (FastAPI)

**Constraints**: Ley 1581 de 2012 (sin datos personales); trazabilidad 100 % (resultado ligado a solicitud)

**Scale/Scope**: 20 llamadas de validación; banco de 40 solicitudes (HU-02)

## Constitution Check

*GATE: src-layout, uv/pytest/Ruff. El registro es local y no versiona datos personales.*

## Project Structure

```text
src/m2_cad/
├── registro.py        # módulo de registro (id, hora, texto, traducción, resultado, latencia, error, versión)
└── api.py             # FastAPI (J. C. Pérez) — integra el registro

data/
└── registro.csv       # salida del registro (gitignoreado)
```

**Structure Decision**: el registro vive en `src/m2_cad/registro.py` (ya existe como stub); `api.py` lo invoca en cada POST /generar.

## Complexity Tracking

*(Sin violaciones.)*
