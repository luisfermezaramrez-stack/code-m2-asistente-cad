# SPEC-015 · HU-15 — Plan técnico: Vue 3 + FastAPI SSE

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #46). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-015
- **Historia**: HU-15 · issue #39
- **Responsable**: Carlos Eduardo Trujillo
- **Rama**: `feature/39-hu-15-vue-fastapi-sse`
- **PR**: #46 (fusionado 2026-11-14 02:00 UTC)
- **Estado**: Implementada; AC3 y AC4 parciales
- **Archivos**: [`spec.md`](./spec.md) · [`tasks.md`](./tasks.md) · contrato detallado en [`docs/hu15-sse.md`](../../docs/hu15-sse.md)

## Diseño técnico

1. La SPA (`frontend/src/useGeneration.ts`) envía `POST /generar` con
   `Accept: text/event-stream` y lee el cuerpo con `fetch` + `ReadableStream`
   (`frontend/src/sse.ts`); `EventSource` no sirve porque solo admite GET.
2. `api.generar` negocia el transporte (`_acepta_sse`) y crea un `Trabajo` en
   `GestorTrabajos` (`src/m2_cad/trabajos.py`), que ejecuta el pipeline en un hilo.
3. El pipeline recibe un `ControlGeneracion` (`src/m2_cad/control.py`): `informar(etapa)`
   publica una etapa real y comprueba la cancelación en puntos seguros.
4. `RespuestaSSE` serializa los eventos; al llegar al terminal se escribe el registro CSV
   y la corrida MLflow (HU-16) dentro del hilo del trabajo.
5. Con resultado `verificado`, la SPA comprueba cada archivo con `HEAD` y muestra el GLB
   en `GlbViewer.vue` (Three.js, carga diferida).

| Componente | Archivo | Responsabilidad |
| --- | --- | --- |
| SPA | `frontend/src/App.vue`, `useGeneration.ts` | Formulario, etapas, cancelación, timeout, mensajes |
| Cliente | `frontend/src/api.ts`, `sse.ts` | Contrato HTTP, parser SSE incremental, `publicMessage` |
| Visor | `frontend/src/GlbViewer.vue` | GLB con `GLTFLoader` y `OrbitControls` |
| Trabajos | `src/m2_cad/trabajos.py` | Hilo por trabajo, secuencia de eventos, keep-alive, retención |
| Control | `src/m2_cad/control.py` | Etapas reales y cancelación cooperativa |
| Web | `src/m2_cad/web.py` | Servir build y `assets`, CORS exacto |
| Diseño | `design/tokens.css`, `design/index.html` | Tokens únicos y referencia estática |
| Despliegue | `Dockerfile`, `docker-compose.yml` | Build multietapa, un worker, healthcheck |

## Decisiones

- **SSE sobre el mismo `POST /generar`** negociado por `Accept`: conserva el contrato JSON
  y las pruebas existentes sin abrir un endpoint paralelo.
- **Etapas solo reales.** No hay porcentajes ni temporizadores: si no llega ninguna etapa,
  la SPA dice que el servicio no informa progreso (pedido explícito del AC3).
- **Cancelación cooperativa local.** No se matan hilos ni se aborta la llamada HTTP al
  modelo; se comprueba la señal entre operaciones. Por eso `cancelacion_remota_confirmada` es siempre `false`.
- **Terminal `cancelado` adicional** para no disfrazar una cancelación de `error`.
- **Mismo origen.** FastAPI sirve el build; CORS se restringe a orígenes exactos.
- **Mensajes públicos filtrados.** `publicMessage` descarta textos con URL, IP, clave o
  trazas, salvo el mensaje exacto de clave ausente (corrección del bloqueante 2 de la revisión).
- **Desconexión = cancelación.** Cerrar el stream solicita cancelación; tras la revisión
  (bloqueante 1) se ajustó el mensaje de la SPA en lugar de cambiar el comportamiento.
- **Three.js en lugar de `<model-viewer>`**, con carga diferida del visor.

## Contratos

| Ruta | Respuesta |
| --- | --- |
| `POST /generar` (JSON) | Igual que antes de HU-15 |
| `POST /generar` + `Accept: text/event-stream` | 200 SSE; cabecera `X-Solicitud-ID`; 422 JSON si el cuerpo es inválido; 503 si no hay capacidad |
| `GET /generaciones/{id}` | Último estado (`iniciando` antes del primer evento) |
| `DELETE /generaciones/{id}` | 202 activo, 200 terminal, 404 desconocido |
| `GET`/`HEAD /generaciones/{id}/archivos/{step\|glb\|csv}` | Archivo o 404 |
| `GET /`, `GET /assets/{nombre}` | Build de Vue |

Eventos SSE (`id: <solicitud_id>:<secuencia>`, `event: <estado>`, `data:` JSON con
`solicitud_id`, `secuencia`, `estado`, `terminal`, `cancelacion_solicitada`):

| Evento | Campos adicionales |
| --- | --- |
| `validando`, `generando` | — |
| `verificado` | `resultado` (mismo diccionario que la respuesta JSON) |
| `declinado` | `motivo`, `codigo_http: 422` |
| `error` | `motivo`, `codigo_http` |
| `cancelado` | `motivo`, `pipeline_detenido: true`, `cancelacion_remota_confirmada: false` |

Variables: `M2_CORS_ORIGINS` (por defecto `http://localhost:8000,http://127.0.0.1:8000`),
más las de HU-14 (`DEEPSEEK_API_KEY`, `LLM_MODEL`). Timeout de espera en la SPA: 180 s
por defecto, configurable entre 5 y 600 s.

## Riesgos

| Riesgo | Estado |
| --- | --- |
| Un hilo CAD por solicitud sin semáforo (revisión, punto 3) | Abierto; solo limita la retención de 128 trabajos |
| Cancelación tardía deja STEP/GLB/CSV huérfanos (punto 4) | Documentado como límite en `docs/hu15-sse.md` |
| `Accept` ignora valores `q` (punto 6) | Abierto (`api.py:261-263`) |
| Registro de trabajos en memoria | Se pierde al reiniciar; un único worker |
| Inferencia real no repetida en el PR | Validación con modelo simulado y CAD real |

## Alternativas descartadas

- **Mantener Gradio**: no permite el diseño ni el progreso por etapas que pide la historia.
- **`EventSource`**: solo GET; el cuerpo de la solicitud exige POST.
- **WebSocket o sondeo periódico**: más infraestructura que SSE para un flujo unidireccional.
- **Progreso simulado**: prohibido por el AC3.

## Estrategia de pruebas

- Python: `tests/test_sse.py` (secuencia, terminal único, declinación frente a 422,
  modelo no disponible, cancelación, desconexión, rutas de archivos) y `tests/test_web.py`
  (estáticos, CORS, rutas desconocidas en JSON).
- Pipeline: `test_progreso_corresponde_a_operaciones_reales`,
  `test_cancelacion_entre_operaciones_no_avanza_etapas` (`tests/test_pipeline.py`).
- SPA (Vitest): `frontend/tests/App.test.ts`, `api.test.ts`, `sse.test.ts`, con dobles
  explícitos de API y WebGL (`fakeCadService.ts`).
- Despliegue: `scripts/verify_hu15_deployment.py` con `docker-compose.hu15-validation.yml`.
- `make check` encadena Ruff, Vitest, TypeScript, build y pytest con cobertura.
