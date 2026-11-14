# SPEC-015 · HU-15 — Tareas: Vue 3 + FastAPI SSE

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #46). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-015
- **Historia**: HU-15 · issue #39
- **Responsable**: Carlos Eduardo Trujillo
- **Rama**: `feature/39-hu-15-vue-fastapi-sse`
- **PR**: #46 (fusionado 2026-11-14 02:00 UTC)
- **Estado**: 14 de 18 tareas hechas; 4 abiertas (brechas)
- **Archivos**: [`spec.md`](./spec.md) · [`plan.md`](./plan.md)

El PR #46 se fusionó como un único commit en `develop` (`4d64ee7`); los commits citados
son los de la rama.

## Diseño (AC4)

- [x] T01 — Tokens de color, espaciado y tipografía en `design/tokens.css` · Responsable: Carlos Eduardo Trujillo · Hecho cuando: la SPA los importa como única fuente · Evidencia: `frontend/src/main.ts:3`
- [x] T02 — Referencia estática y validación a 1280/768 px, teclado y contraste · Responsable: Carlos Eduardo Trujillo · Hecho cuando: sin scroll horizontal y pares ≥ 4,5:1 · Evidencia: `design/index.html`, `design/validation.md`, `design/README.md`
- [ ] T03 — Aprobación registrada de la referencia visual antes de codificar · Responsable: Carlos Eduardo Trujillo · Hecho cuando: hay constancia de aprobación · Evidencia: brecha; `design/README.md` sigue como "pendiente de aprobación"

## Backend de progreso (AC2, AC3) — depende de T01

- [x] T04 — `ControlGeneracion` con etapas reales y cancelación en puntos seguros · Responsable: Carlos Eduardo Trujillo · Hecho cuando: cancelar no avanza etapas · Evidencia: `src/m2_cad/control.py`; `test_cancelacion_entre_operaciones_no_avanza_etapas`
- [x] T05 — `GestorTrabajos`/`Trabajo` con SSE, keep-alive de 15 s y retención de 128 · Responsable: Carlos Eduardo Trujillo · Hecho cuando: un único terminal por trabajo · Evidencia: `src/m2_cad/trabajos.py`; `tests/test_sse.py`
- [x] T06 — Negociación SSE en `POST /generar`, `GET`/`DELETE /generaciones/{id}` y descargas `GET`/`HEAD` · Responsable: Carlos Eduardo Trujillo · Hecho cuando: JSON intacto y archivos solo de resultados verificados · Evidencia: `src/m2_cad/api.py`; `test_descarga_resuelve_rutas_relativas_con_raiz_real`
- [x] T07 — Servir el build de Vue y CORS exacto · Responsable: Carlos Eduardo Trujillo · Hecho cuando: rutas desconocidas responden JSON · Evidencia: `src/m2_cad/web.py`; `tests/test_web.py` (7 pruebas)
- [ ] T08 — Cancelación de extremo a extremo con confirmación remota · Responsable: Carlos Eduardo Trujillo · Hecho cuando: la llamada al modelo se detiene y se confirma · Evidencia: brecha declarada en el PR #46 y en `docs/hu15-sse.md`
- [ ] T09 — Límite de concurrencia y respeto de valores `q` en `Accept` · Responsable: Carlos Eduardo Trujillo · Hecho cuando: hay semáforo con 503 y la negociación respeta `q=0` · Evidencia: abierto (revisión del PR #46, puntos 3 y 6)

## SPA (AC1, AC3) — depende de T06

- [x] T10 — Proyecto Vue 3 + Vite + TypeScript en `frontend/` · Responsable: Carlos Eduardo Trujillo · Hecho cuando: `make frontend-check` pasa · Evidencia: `frontend/package.json`; CI del PR #46
- [x] T11 — Parser SSE incremental y cliente HTTP con mensajes públicos filtrados · Responsable: Carlos Eduardo Trujillo · Hecho cuando: frames parciales se reensamblan y no se exponen URL ni claves · Evidencia: `frontend/src/sse.ts`, `api.ts:39-46`; `frontend/tests/sse.test.ts`, `api.test.ts`
- [x] T12 — Etapas en orden, aviso sin progreso, timeout configurable, cancelación y consulta de estado · Responsable: Carlos Eduardo Trujillo · Hecho cuando: un progreso inválido se rechaza y sin etapas se declara · Evidencia: `useGeneration.ts:153-165`, `App.vue:78`; `frontend/tests/App.test.ts`
- [x] T13 — Visor GLB con Three.js y descargas STEP/GLB/CSV independientes · Responsable: Carlos Eduardo Trujillo · Hecho cuando: sin GLB se mantienen STEP/CSV · Evidencia: `frontend/src/GlbViewer.vue`; `frontend/tests/App.test.ts`
- [x] T14 — Correcciones de la revisión: mensaje de desconexión y mensaje de clave ausente · Responsable: Carlos Eduardo Trujillo · Hecho cuando: los bloqueantes 1 y 2 quedan resueltos · Evidencia: commit `fix(hu-15): clarify cancellation and preserve safe configuration errors`; `useGeneration.ts:176-182`, `api.ts:42`

## Migración y retiro de Gradio (AC1, AC5) — depende de T10–T13

- [x] T15 — Reubicar los 23 casos de `test_interfaz.py` en Vitest o pytest y retirar `interfaz.py` y Gradio · Responsable: Carlos Eduardo Trujillo · Hecho cuando: cada caso tiene destino y la cobertura no baja · Evidencia: tabla en `docs/hu15-despliegue.md`; cobertura 95,33 % → 95,90 %

## Despliegue e integración (AC6) — depende de T15

- [x] T16 — Dockerfile multietapa (frontend + vendor), un worker, healthcheck; Compose sin 7860 · Responsable: Carlos Eduardo Trujillo · Hecho cuando: `docker compose up` sirve todo en `:8000` · Evidencia: `Dockerfile`, `docker-compose.yml`; `docs/hu15-docker-validation.md`
- [x] T17 — Integrar `develop` con HU-14 (contrato DeepSeek, `no aplica` en SSE) y con HU-16 (MLflow) · Responsable: Carlos Eduardo Trujillo · Hecho cuando: CI en verde tras resolver conflictos · Evidencia: `docs/hu15-integracion-hu14.md`; `test_hu14_sse_usa_espanol_y_clave_sin_url_y_registra_no_aplica`, `test_solicitud_sse_entregada_registra_su_corrida`; check `test` del PR #46 aprobado
- [ ] T18 — Validar el despliegue con inferencia real de DeepSeek · Responsable: Carlos Eduardo Trujillo · Hecho cuando: una generación real termina en `verificado` desde la SPA · Evidencia: no verificado; el PR #46 usó un modelo simulado

## Notas

- El PR #46 declara pendientes la instalación limpia en Windows (falta MSVC) y regenerar el diagrama Archify.
- Las secciones "Menores" de la revisión (restos de Gradio en plantillas, código inalcanzable,
  sondeo cada 50 ms, prefijo del motivo en el CSV de SSE) no se volvieron a verificar aquí.
