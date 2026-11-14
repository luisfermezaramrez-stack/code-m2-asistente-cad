# SPEC-015 · HU-15 — Interfaz Vue 3 con progreso en vivo (SSE)

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #46). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-015
- **Historia**: HU-15 · issue #39
- **Responsable**: Carlos Eduardo Trujillo (`cetrujillo`)
- **Rama**: `feature/39-hu-15-vue-fastapi-sse`
- **PR**: #46, fusionado en `develop` el 2026-11-14 02:00 UTC (2026-11-13 21:00, UTC−05:00); revisión de `luisfermezaramrez-stack`: cambios solicitados y luego aprobado
- **Estado**: Implementada. AC3 y AC4 parciales; ver brechas.
- **Archivos**: [`plan.md`](./plan.md) · [`tasks.md`](./tasks.md)

## Problema y contexto

La interfaz Gradio (HU-08) bloqueaba la pantalla hasta 70 s sin indicar la etapa de la
generación y no daba una apariencia de producto terminado. HU-15 reemplaza Gradio por
una SPA propia que consume FastAPI y recibe el avance real del pipeline por SSE. Al
retirar Gradio desaparece `gr.Model3D`, por lo que el visor 3D se reconstruye en Vue.

## Historia de usuario

> **Como** diseñador CAD que describe una pieza en español, **quiero** una interfaz web propia en Vue 3, con diseño cuidado y avance estado por estado, **para** trabajar en un producto que se ve terminado y que me dice en qué etapa está, en vez de una pantalla de Gradio congelada durante 70 s.

Criterios originales (verbatim, `reference/HU-Carlos-Eduardo-Trujillo.md`):

- **AC1 — Stack**: SPA en Vue 3 (Composition API) + Vite + TypeScript; Gradio deja de ser la interfaz y deja de declararse como dependencia de UI en `pyproject.toml`.
- **AC2 — Contrato**: la SPA consume solo FastAPI; `POST /generar` suma un canal de progreso (SSE) y `api.py` sirve el build estático con CORS restringido al origen del front.
- **AC3 — Streaming en el cliente**: el estado avanza en orden `validando` → `generando` → `verificado` | `declinado` | `error` leyendo SSE, y la solicitud se puede cancelar; si el backend no informa progreso, la vista lo declara en vez de simularlo.
- **AC4 — Diseño**: tokens (color, espaciado, tipografía) en un archivo único y referencia visual aprobada en `design/` antes de codificar; contraste AA, estados vacío/cargando/error/éxito, usable a 1280 y 768 px sin scroll horizontal, y navegable con teclado con foco visible.
- **AC5 — No se pierde cobertura**: cada comportamiento que hoy cubren los 23 tests de `test_interfaz.py` (declinación oculta descargas, STEP independiente del GLB, timeout configurable, aviso de preliminar visible) se reubica en tests de la SPA (Vitest) o de la API; la cobertura no baja.
- **AC6 — Despliegue**: `docker compose up` levanta API y front sin pasos manuales, con el build de Vue servido en el mismo origen; el puerto `7860` de Gradio deja de existir.

## Requisitos funcionales

- **RF-1**: `POST /generar` con `Accept: text/event-stream` emite eventos SSE por etapa real; sin esa cabecera conserva la respuesta JSON.
- **RF-2**: `GET /generaciones/{id}` consulta el último estado; `DELETE /generaciones/{id}` solicita cancelación cooperativa (202 activo, 200 terminal, 404 desconocido).
- **RF-3**: `GET|HEAD /generaciones/{id}/archivos/{step|glb|csv}` entrega cada archivo de forma independiente, solo para resultados `verificado` dentro de `outputs/`.
- **RF-4**: FastAPI sirve el build de Vue (`/`, `/assets/...`) y las rutas desconocidas responden JSON, nunca HTML.
- **RF-5**: La SPA muestra etapas, visor GLB (Three.js), descargas, motivo de declinación/error y el aviso «Diseño preliminar: requiere revisión profesional».

## Requisitos no funcionales

- **RNF-1**: CORS solo con orígenes exactos de `M2_CORS_ORIGINS`, sin comodines.
- **RNF-2**: Los mensajes públicos no exponen URL, clave ni trazas del proveedor.
- **RNF-3**: Sin porcentajes ni progreso simulado; `: keep-alive` cada 15 s no es una etapa.
- **RNF-4**: Un worker; registro de trabajos en memoria, máximo 128 retenidos.

## Criterios de aceptación (Dado / Cuando / Entonces)

**AC1 — Stack.** *Cumplido.*
Dado el repositorio, cuando se revisan `frontend/` y `pyproject.toml`, entonces la SPA usa
Vue 3 Composition API, Vite y TypeScript, y Gradio no figura como dependencia.
Evidencia: `frontend/package.json` (`vue` 3.5.45, `vite`, `typescript`); `src/m2_cad/interfaz.py`
y `tests/test_interfaz.py` eliminados; `pyproject.toml` −1 línea y Gradio retirado de `uv.lock` en el PR #46.

**AC2 — Contrato FastAPI + SSE + CORS.** *Cumplido, con observación.*
Dada una solicitud con `Accept: text/event-stream`, cuando llega a `POST /generar`,
entonces recibe SSE; el build se sirve desde `api.py` y CORS acepta solo orígenes exactos.
Evidencia: `api.py:261-263` (`_acepta_sse`), `src/m2_cad/web.py:12-51`;
`test_cors_solo_origen_exacto_y_metodos_necesarios`, `test_api_real_sirve_build_vue_y_conserva_errores_json`;
contrato en `docs/hu15-sse.md`. Observación: la negociación ignora los valores `q` del
`Accept` (señalado en la revisión del PR #46, punto 6; sigue abierto).

**AC3 — Streaming, cancelación y ausencia de progreso.** *Parcial — Brecha en cancelación.*
Dada una generación en curso, cuando la SPA lee el stream, entonces las etapas avanzan
`validando` → `generando` → terminal y, si no llega ninguna etapa, la vista lo declara.
Evidencia: `test_progreso_corresponde_a_operaciones_reales`, `test_sse_sin_modelo_informa_validacion_y_error`;
`frontend/src/useGeneration.ts:153`, `frontend/src/App.vue:78`.
Brecha: la cancelación es cooperativa y local (`control.py`); no detiene la llamada al
modelo en curso y `cancelacion_remota_confirmada` siempre es `false`. El PR #46 declara
que "no se declara cerrado ese aspecto de AC3". Se añadió el terminal `cancelado`, que el AC no enumeraba.

**AC4 — Diseño.** *Parcial — Brecha en la aprobación.*
Dados los tokens y la referencia de `design/`, cuando se construye la SPA, entonces usa un
único archivo de tokens y cumple AA, 1280/768 px sin scroll horizontal y foco visible.
Evidencia: `design/tokens.css` importado en `frontend/src/main.ts:3`; contraste calculado
(15 pares de texto, mínimo 6,31:1) en `design/README.md`; 1280/768 y teclado en Chrome
sobre la referencia (`design/validation.md`) y sobre la app servida por FastAPI
(`docs/hu15-despliegue.md`, "Resultados ejecutados").
Brecha: `design/README.md` se titula "Propuesta visual pendiente de aprobación" y no hay
registro de aprobación humana. Que la referencia precediera al código no es verificable
(el PR se fusionó como un solo commit). El contraste se calculó sobre la maqueta, no se midió en la SPA final.

**AC5 — Cobertura de los 23 casos de Gradio.** *Cumplido (según evidencia del PR).*
Dados los 23 casos de `test_interfaz.py`, cuando se retiró Gradio, entonces cada uno tiene
destino en Vitest o en pytest y la cobertura no bajó.
Evidencia: tabla de migración en `docs/hu15-despliegue.md` (sección "Migración de los 23
casos"); cobertura 95,90 % frente a 95,33 % previa; tras integrar HU-14 el PR informa
246 pruebas Python y 97,74 %, y 39 casos Vitest.

**AC6 — Despliegue mismo origen sin 7860.** *Cumplido.*
Dado Docker y `DEEPSEEK_API_KEY`, cuando se ejecuta `docker compose up`, entonces el
servicio `m2-cad` sirve API y Vue en `:8000` y no existe el puerto 7860.
Evidencia: `docker-compose.yml:24-31`, `Dockerfile` (build multietapa, `EXPOSE 8000`);
`docs/hu15-docker-validation.md`; `scripts/verify_hu15_deployment.py`; CI del PR #46 en verde.
Límite: la validación usó un modelo simulado; no se repitió inferencia real en este PR.

## Fuera de alcance

- Cancelación remota del proveedor (DeepSeek/llama.cpp) y rollback de archivos.
- Persistencia de trabajos entre reinicios o coordinación entre varios workers.
- Compatibilidad con lectores de pantalla u otros navegadores (no se afirma).

## Métricas de éxito

| Métrica | Meta | Observado (PR #46) |
| --- | --- | --- |
| Casos de `test_interfaz.py` reubicados | 23/23 | 23/23 (tabla de migración) |
| Cobertura Python | No baja | 95,33 % → 95,90 %; 97,74 % tras integrar HU-14 |
| Scroll horizontal a 1280 y 768 px | Ninguno | Ninguno (Chrome) |
| Contraste texto/fondo | ≥ 4,5:1 | Mínimo 6,31:1 (maqueta) |
| Puerto 7860 | Eliminado | Eliminado |
