# SPEC-012 · HU-03 — Tareas de la traducción ES→EN

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #27). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-012
- **Historia**: HU-03 (issue #3)
- **Responsable**: Juan Camilo Pérez (`JuanC0319`)
- **Rama**: `feature/hu-03-traduccion`
- **PR**: #27 (fusionado el 2026-11-10, commit `dbe7dca`); antecedente PR #15
- **Estado**: Implementada y luego retirada por HU-14 (SPEC-008)
- **Documentos**: [`spec.md`](./spec.md) · [`plan.md`](./plan.md)

Las tareas `[x]` se verificaron en `dbe7dca`, `cff998f` o `25d397d`. Las `[ ]` son
brechas frente a los AC que quedaron sin cerrar antes del retiro y ya no se ejecutarán.

## Implementación

- [x] T01 — Implementar `_proteger_valores` con marcadores `__CADVAL_N__` · Responsable: J. C. Pérez · Hecho cuando: cifras y unidades desaparecen del texto enviado · Evidencia: `test_proteccion_de_medidas`, `test_medidas_parametrizadas`
- [x] T02 — Implementar `_restaurar_valores` con control de marcadores y de números · Responsable: J. C. Pérez · Depende de: T01 · Hecho cuando: marcadores faltantes o cifras añadidas lanzan `ErrorTraduccion` · Evidencia: `test_marcador_faltante`, `test_restauracion_rechaza_cantidades_alteradas`
- [x] T03 — Implementar `_consultar_gemini` (REST, `temperature: 0`, 8 s) · Responsable: J. C. Pérez · Hecho cuando: errores de red y respuestas incompletas lanzan `ErrorTraduccion` · Evidencia: `test_gemini_error_de_red`
- [x] T04 — Implementar `traducir_solicitud` con validación de entrada y clave · Responsable: J. C. Pérez · Depende de: T01–T03 · Hecho cuando: entrada vacía, > 1000 caracteres o sin clave fallan con el error tipado · Evidencia: `test_solicitud_vacia`, `test_solicitud_demasiado_larga`, `test_sin_api_key`, `test_traduccion_con_gemini_simulado`

## Pruebas y revisión

- [x] T05 — Primera entrega en el PR #15 · Responsable: J. C. Pérez · Hecho cuando: revisión recibida · Evidencia: PR #15 cerrado sin fusionar el 2026-11-10; cambios solicitados por cobertura 64 % < 70 %
- [x] T06 — Añadir los 4 casos pedidos en la revisión y reenviar en el PR #27 · Responsable: J. C. Pérez · Depende de: T05 · Hecho cuando: CI en verde con cobertura ≥ 70 % · Evidencia: PR #27 (16/16, 80,33 %); check `test` en verde; aprobado y fusionado el 2026-11-10
- [x] T07 — Cubrir ≥ 10 casos con decimales con coma (AC4) · Responsable: J. C. Pérez · Depende de: T06 · Hecho cuando: `test_translate.py` tiene ≥ 10 casos · Evidencia: 16 casos en `dbe7dca:tests/test_translate.py`
- [ ] T08 — Normalizar la coma decimal (`"12,5 mm"` → `"12.5 mm"`) como pide el issue #3 · Responsable: J. C. Pérez · Depende de: T02 · Hecho cuando: una prueba lo afirma · Evidencia: brecha; la prueba afirma que se conserva `12,5 mm`

## Integración y medición

- [x] T09 — Conectar la traducción al pipeline (`generar_pieza`, parámetro `traducir`) y mapear `ErrorTraduccion` a HTTP 503 · Responsable: L. Meza (HU-04) · Depende de: T04 · Hecho cuando: el planificador recibe el texto traducido · Evidencia: commit `cff998f` (`src/m2_cad/pipeline.py`); `25d397d^:src/m2_cad/api.py`
- [ ] T10 — Registrar traducción y tiempo de traducción en `data/registro.csv` (AC1) · Responsable: sin asignar · Depende de: T09 · Hecho cuando: el registro guarda la traducción real y su duración · Evidencia: brecha; la API pasaba `traduccion=""` y solo había latencia total
- [ ] T11 — Comparar números y unidades en 20 solicitudes del banco (AC2) · Responsable: sin asignar · Depende de: T09 · Hecho cuando: existe una ejecución automática con 100 % de conservación · Evidencia: no encontrada
- [ ] T12 — Medir el p90 de la traducción (AC3) · Responsable: sin asignar · Depende de: T09 · Hecho cuando: p90 ≤ 5 s medido · Evidencia: no encontrada

## Retiro (HU-14)

- [x] T13 — Eliminar `traduccion.py`, `test_translate.py`, `ErrorTraduccion` y `GEMINI_API_KEY`; registrar `SIN_TRADUCCION` en la columna existente · Responsable: L. Meza (HU-14) · Hecho cuando: el pipeline planifica desde español sin traducción · Evidencia: PR #43, commit `25d397d`; `src/m2_cad/registro.py:43`; `specs/008-hu-14-deepseek/evidence.md`
