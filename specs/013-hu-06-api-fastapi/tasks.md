# SPEC-013 · HU-06 — Tareas de la API FastAPI

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #16). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-013
- **Historia**: #6
- **Responsable**: Juan Camilo Pérez
- **Rama**: `feature/hu-06-fastapi`
- **PR**: #16 (fusionado 2026-11-10)
- **Estado**: Implementada; quedan brechas abiertas (T09–T11)
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

## Tareas

- [x] T01 — Crear la app FastAPI en `src/m2_cad/api.py` · Responsable: J. C. Pérez ·
  Hecho cuando: `from m2_cad import api` importa · Evidencia:
  `tests/test_api.py::test_modulo_api_importable`
- [x] T02 — `GET /health` con `{"status": "ok"}` (dep. T01) · Responsable: J. C. Pérez ·
  Hecho cuando: responde 200 con ese cuerpo · Evidencia:
  `tests/test_api.py::test_health_endpoint`
- [x] T03 — Modelo `SolicitudGenerar` (1–1000 caracteres, recorte, rechazo de solo
  espacios) (dep. T01) · Responsable: J. C. Pérez · Hecho cuando: `""`, `"   "` y 1001
  caracteres devuelven 422 · Evidencia: `tests/test_api.py::test_generar_rechaza_entrada_invalida`
- [x] T04 — Dependencia `obtener_procesador` y `POST /generar` delegando en ella
  (dep. T03) · Responsable: J. C. Pérez · Hecho cuando: un override sustituye el
  procesador · Evidencia: `tests/test_api.py::test_generar_con_procesador_simulado`
- [x] T05 — Procesador por defecto que responde 503 (dep. T04) · Responsable:
  J. C. Pérez · Hecho cuando: sin override, `POST /generar` responde 503 · Evidencia:
  `tests/test_api.py::test_generar_pipeline_no_disponible`
- [x] T06 — Prueba de éxito con STEP/GLB/CSV simulados (dep. T04) · Responsable:
  J. C. Pérez · Hecho cuando: responde 200 con las rutas simuladas · Evidencia:
  `tests/test_api.py::test_generar_archivos_cad_simulados`
- [x] T07 — Cobertura ≥ 80 % del módulo (AC5) (dep. T02–T06) · Responsable:
  J. C. Pérez · Hecho cuando: `--cov=m2_cad.api` ≥ 80 % · Evidencia: reejecución el
  2026-11-13 sobre `3aab5f4`: 8 pruebas, 100 % de 23 sentencias; hoy 99 % con la suite
  completa
- [x] T08 — Revisión y fusión del PR #16 en `develop` · Responsable: J. C. Pérez ·
  Hecho cuando: PR aprobado y fusionado · Evidencia: aprobación de
  `luisfermezaramrez-stack` (2026-11-10 02:51 UTC), fusión 02:53 UTC
- [ ] T09 — Prueba automática de latencia de `GET /health` ≤ 1 s (AC2) · Responsable:
  sin asignar · Hecho cuando: una prueba falla si se superan 1000 ms · Evidencia:
  **Brecha**; solo existe la medición manual del PR #16 y la medición en proceso de
  esta documentación
- [ ] T10 — Alinear AC1 (declinación con 200) con el 422 que devuelve hoy
  `DeclinacionSolicitud` · Responsable: sin asignar · Hecho cuando: el backlog o el
  código fijan un único código · Evidencia: **Brecha**
- [ ] T11 — Prueba del borde exacto de 1000 caracteres (aceptado) · Responsable: sin
  asignar · Hecho cuando: 1000 caracteres no devuelve 422 · Evidencia: **Brecha**

## Dependencias externas

- Registro de solicitudes (AC3, AC4): SPEC-004, Luis Meza.
- Pipeline real conectado en `a0084b6` (HU-04), posterior a este PR.
