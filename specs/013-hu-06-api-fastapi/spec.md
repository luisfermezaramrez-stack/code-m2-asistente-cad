# SPEC-013 · HU-06 — API FastAPI (parte de Juan Camilo Pérez)

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #16). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-013
- **Historia**: #6 · 3 SP compartidos (2 SP de esta parte) · Etiquetas: Backend · CPM: J
- **Responsable**: Juan Camilo Pérez (API: AC1, AC2, AC5). El registro (AC3, AC4) es de
  Luis Meza y está especificado en [`../004-registro-solicitudes/`](../004-registro-solicitudes/spec.md).
- **Rama**: `feature/hu-06-fastapi`
- **PR**: #16 (autor en GitHub: `JuanC0319`; aprobado por `luisfermezaramrez-stack`),
  fusionado en `develop` el 2026-11-10 02:53 UTC (commit `3aab5f4`)
- **Estado**: Implementada y fusionada; evolucionada después por HU-04, HU-14, HU-16 y HU-15
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

El pipeline CAD (descripción → programa → verificación → STEP/GLB/CSV) necesitaba una
entrada HTTP estable para que la UI, el banco de pruebas y el registro de solicitudes
trabajaran contra un mismo contrato. Al momento del PR #16 el pipeline (HU-04) y el
registro (parte de L. Meza) aún no estaban integrados, por lo que la API se construyó con
un procesador inyectable y un procesador de producción que responde 503.

## Historia de usuario

Cita literal de `reference/HU-Juan-Camilo-Perez.md`, «## HU-06»:

> **Como** evaluador del producto, **quiero** una API FastAPI (POST /generar y GET /health) que registre texto, traducción, resultado, latencia, error y versión del modelo de cada solicitud, **para** calcular las métricas de los objetivos 1 y 2 sin revisar casos a mano.
>
> - **AC1**: POST /generar responde 200 con STEP o declinación y 422 ante texto vacío o de más de 1 000 caracteres. *(J. C. Pérez)*
> - **AC2**: GET /health responde en ≤ 1 s. *(J. C. Pérez)*
> - **AC3**: en 20 llamadas, 0 campos vacíos en el registro (id, hora, texto, traducción, resultado, latencia, error y versión). *(L. Meza — registro)*
> - **AC4**: el registro excluye nombres y correos. *(L. Meza — registro)*
> - **AC5**: cobertura ≥ 80 % del módulo de la API. *(J. C. Pérez)*

AC3 y AC4 quedan fuera de esta especificación (ver SPEC-004).

## Requisitos funcionales

- **RF-1**: `GET /health` devuelve `200` con `{"status": "ok"}` sin tocar el pipeline.
- **RF-2**: `POST /generar` recibe un JSON `{"texto": str}` validado con Pydantic
  (`SolicitudGenerar`): 1–1000 caracteres; el texto se recorta y un texto solo con
  espacios se rechaza.
- **RF-3**: una entrada inválida responde `422` (validación de FastAPI/Pydantic).
- **RF-4**: el procesamiento se delega en un procesador obtenido por inyección de
  dependencias (`obtener_procesador`), sustituible en pruebas con `dependency_overrides`.
- **RF-5**: mientras el pipeline no esté disponible, `POST /generar` responde `503`
  con un mensaje explícito.
- **RF-6**: la respuesta de éxito es el diccionario que devuelve el procesador
  (pieza entregada con rutas de STEP/GLB/CSV, o declinación).

## Requisitos no funcionales

- **RNF-1**: pruebas sin GPU ni red, con `fastapi.testclient.TestClient`.
- **RNF-2**: cobertura ≥ 80 % del módulo `m2_cad.api` (AC5).
- **RNF-3**: estilo Ruff (`line-length = 100`) y docstrings en español.

## Criterios de aceptación

### AC1 — Respuestas de `POST /generar`

- **Dado** un procesador simulado que devuelve una pieza (STEP/GLB/CSV) o una declinación,
  **cuando** se envía `POST /generar` con un texto válido, **entonces** responde `200`
  con ese contenido.
- **Dado** un texto `""`, `"   "` o de 1001 caracteres, **cuando** se envía
  `POST /generar`, **entonces** responde `422`.
- **Evidencia**: `tests/test_api.py::test_generar_con_procesador_simulado`,
  `::test_generar_archivos_cad_simulados`, `::test_generar_rechaza_entrada_invalida`
  (en el PR #16, líneas 38, 50 y 100; hoy 50, 62 y 115).
- **Estado**: Cumplido para el alcance del PR #16, con dos salvedades:
  1. En el PR #16 el `200` solo se demostró con procesadores simulados; el procesador
     de producción respondía `503`. El pipeline real se conectó después (commit
     `a0084b6`, HU-04).
  2. Hoy una declinación real del pipeline responde `422` (`DeclinacionSolicitud`,
     `src/m2_cad/api.py:73`, "sin cambiar el 422 de HU-05"), no `200`. La lectura
     literal de AC1 («200 con … declinación») ya no se cumple con el pipeline real.
     **Brecha** de redacción entre HU-06 y HU-05, no resuelta en el backlog.
  3. El borde exacto de 1000 caracteres (aceptado) no tiene prueba propia.

### AC2 — `GET /health` en ≤ 1 s

- **Dado** el servicio en ejecución, **cuando** se llama `GET /health`, **entonces**
  responde `200` en ≤ 1 s.
- **Evidencia**: `tests/test_api.py::test_health_endpoint` comprueba `200` y el cuerpo,
  pero **no mide el tiempo**. El PR #16 informa 20/20 respuestas, media 2,56 ms y
  máximo 6,30 ms (medición del autor, no reproducible desde el repositorio). Medición
  propia del 2026-11-13 con `TestClient` en proceso: 20 llamadas, media 2,40 ms,
  máximo 12,05 ms.
- **Estado**: Cumplido en proceso; **no verificado** contra un servidor desplegado ni
  con una prueba automática de latencia.

### AC5 — Cobertura ≥ 80 % del módulo de la API

- **Dado** la suite de pruebas, **cuando** se ejecuta con `--cov=m2_cad.api`,
  **entonces** la cobertura del módulo es ≥ 80 %.
- **Evidencia**: reejecución el 2026-11-13 de `tests/test_api.py` del commit `3aab5f4`
  sobre su `api.py`: 8 pruebas pasan, 23 sentencias, **100 %**. Sobre el código actual:
  `tests/test_api.py` solo cubre 66 % de `api.py` (181 sentencias), y la suite completa
  (`uv run --offline pytest --cov=m2_cad.api`) cubre **99 %** (270 pruebas).
- **Estado**: Cumplido (100 % en el PR #16; 99 % hoy con la suite completa).
  Nota: `test_api.py` aislado ya no alcanza el 80 %; el resto lo cubren
  `test_sse.py`, `test_api_seguimiento.py` y `test_web.py`.

## Fuera de alcance

- Registro de solicitudes y exclusión de PII (AC3, AC4): SPEC-004.
- Integración del pipeline CAD real (HU-04), modelo DeepSeek (HU-14), seguimiento con
  MLflow (HU-16), SSE, cancelación y descargas (HU-15).
- Autenticación, límites de tasa y concurrencia.

## Métricas de éxito

- Códigos de estado de `POST /generar` (200/422/503) fijados por pruebas automáticas.
- Cobertura del módulo de la API ≥ 80 % en CI.
- `GET /health` por debajo de 1 s.
