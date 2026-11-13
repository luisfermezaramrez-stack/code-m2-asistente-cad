# Constitución del asistente CAD

## Propósito y frontera

Convertir descripciones de piezas del catálogo en CAD preliminar verificado o
declinar con motivo. La verificación geométrica no certifica resistencia ni
cumplimiento normativo. No se infieren medidas ni confirmaciones de cancelación.

## Arquitectura vigente

- Python en `src/m2_cad`, gestionado con uv y `uv.lock`; contenedor Python 3.12.
- Vue 3 Composition API, TypeScript y Vite en `frontend/`; Node 24 y npm lockfile.
- `design/tokens.css` es la única fuente de tokens; `design/` conserva la referencia.
- FastAPI sirve HTML/assets, API JSON, SSE y archivos desde un mismo origen.
  Las rutas inexistentes devuelven errores JSON, nunca el índice de la SPA.
- Un worker mantiene el registro acotado de trabajos en memoria. La cancelación
  es cooperativa entre operaciones bloqueantes; no se confirma detención remota.
- El modelo se consume desde el servidor. Claves y direcciones del proveedor no
  se incorporan al bundle ni se publican como configuración del frontend.

## Calidad y operación

`make check`: Ruff, Vitest, TypeScript, build y pytest con cobertura. CI reproduce
estos objetivos con instalaciones desde lockfiles. Las pruebas con dobles se
identifican como simuladas; no prueban inferencia real ni disponibilidad Docker.
Ramas desde `develop`, integración por PR; commits convencionales solo cuando
se soliciten. Este documento se actualiza ante decisiones arquitectónicas.

## Decisiones

- **2026-11-13 — HU-15/#39:** Vue sustituye a Gradio; Docker multietapa compila
  frontend y vendor. FastAPI es el único servicio web de usuario, sin proxy que
  almacene SSE. CORS admite exclusivamente orígenes HTTP(S) exactos configurados.
  Contrato, migración y evidencia: `docs/hu15-sse.md` y `docs/hu15-despliegue.md`.
