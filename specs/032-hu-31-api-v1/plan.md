# HU-31 — Plan técnico de API `/v1` con contrato congelado

## 1. Objetivo

Publicar todas las rutas de la API bajo el prefijo `/v1`, mantener las rutas planas como
redirecciones temporales anunciadas como obsoletas, congelar el OpenAPI de la versión 1 en
un archivo versionado y añadir un test que falle ante cambios incompatibles del contrato.
El frontend consume las rutas canónicas desde la misma HU.

## 2. Arquitectura propuesta

1. `api.py` define un `APIRouter(prefix="/v1")` y registra todas las rutas API allí; el OpenAPI
   publicado sólo contiene rutas `/v1` (AC3).
2. Las rutas planas se registran fuera del schema con `include_in_schema=False` y responden
   `307` a su equivalente `/v1`, conservando método, cuerpo y query string (AC1/RF-2).
3. Cada redirección añade `Deprecation: @1795564800` (RFC 9745, fecha de publicación de v1),
   `Sunset` y `Link: <...v1...>; rel="successor-version"` para anunciar la política (RF-5).
4. `app.openapi()` se serializa de forma determinista en `contracts/openapi-v1.json`.
5. `contrato_api.py` carga el contrato congelado y lo compara con el generado; el test de
   contrato falla si aparece, desaparece o cambia una ruta o un campo del schema (AC2/RF-4).
6. El frontend y los scripts de verificación pasan a `/v1`; los tipos generados por SPEC-028
   se regeneran desde el nuevo OpenAPI.

## 3. Componentes

| Archivo | Responsabilidad |
|---|---|
| `src/m2_cad/api.py` | Router `/v1`, redirecciones planas, versión `1.0.0` y manejo de errores |
| `src/m2_cad/contrato_api.py` | Carga y comparación del OpenAPI congelado |
| `contracts/openapi-v1.json` | Contrato congelado de la versión 1 |
| `docs/versionado-api.md` | Política de versionado y deprecación |
| `frontend/src/api.ts`, `frontend/src/useGeneration.ts` | Consumo de rutas `/v1` |
| `frontend/src/generated/api.ts` | Tipos regenerados desde el OpenAPI `/v1` |
| `scripts/smoke_hu07.py`, `scripts/verify_hu15_deployment.py` | Clientes de verificación en `/v1` |
| `tests/test_hu31_api_v1.py` | AC1–AC4 y no regresión |
| `tests/test_api_types.py`, `tests/test_sse.py`, `frontend/tests/*` | Ajuste a rutas canónicas |

## 4. Rutas y redirecciones

| Ruta plana | Canónica |
|---|---|
| `GET /health` | `GET /v1/health` |
| `GET /ready` | `GET /v1/ready` |
| `GET /registros/{identificador}` | `GET /v1/registros/{identificador}` |
| `GET /registros/{identificador}/step` | `GET /v1/registros/{identificador}/step` |
| `POST /generar` | `POST /v1/generar` |
| `GET /generaciones/{solicitud_id}` | `GET /v1/generaciones/{solicitud_id}` |
| `DELETE /generaciones/{solicitud_id}` | `DELETE /v1/generaciones/{solicitud_id}` |
| `GET/HEAD /generaciones/{solicitud_id}/archivos/{formato}` | `/v1/generaciones/...` |

Las rutas estáticas de la SPA (`/`, `/assets`) y el 404 JSON de rutas API desconocidas no
se versionan y se conservan (RNF-2).

## 5. Contrato congelado

- `info.version = "1.0.0"`.
- Se congela el documento completo devuelto por `app.openapi()` con `sort_keys=True` y dos
  espacios de indentación.
- `validar_contrato(generado, congelado)` informa la ruta/clave afectada; los tests lo usan
  directamente para demostrar que quitar un campo sin subir versión rompe CI (AC2).
- Un cambio compatible (por ejemplo añadir un campo opcional) también debe revisarse y
  regenerarse de forma explícita: el contrato es una fotografía, no un rango tolerado.

## 6. Política de deprecación

- Convivencia: **90 días** desde la publicación de v1 (`Sunset: Tue, 23 Feb 2027 00:00:00 GMT`),
  ampliable con `M2_SUNSET_RUTAS_PLANAS` si se retrasa el despliegue.
- Anuncio: cabeceras `Deprecation: @1795564800` (RFC 9745) y
  `Link: <ruta /v1>; rel="successor-version"` en toda respuesta de una ruta plana,
  incluidas las redirecciones. La compatibilidad requiere que el cliente siga el `307`.
- Tras el `Sunset` se retiran las rutas planas y se incrementa la versión mayor del contrato.
- Detalle publicado en `docs/versionado-api.md` y enlazado desde el README.

## 7. Estrategia de pruebas

Pytest con `TestClient` y modelo simulado; sin red, API key ni GPU (RNF-1):

- AC1: mismos resultados para JSON, consulta y descarga llamando a rutas planas y a `/v1`;
  se comprueba el código 307 y las cabeceras de deprecación en la ruta plana.
- AC2: `validar_contrato` falla al eliminar una propiedad de un schema en una copia del
  documento generado.
- AC3: todas las claves de `app.openapi()["paths"]` empiezan con `/v1`.
- AC4: el documento de política existe y contiene el plazo y el mecanismo de anuncio.
- Regresión: SSE, descargas con token, health/ready, SPA y 404 JSON.

Además: Ruff, formato, Pytest completo, cobertura ≥ 70 %, `api-types-check` y Vitest.

## 8. Alcance y restricciones

- Sin `/v2`, autenticación ni cambios funcionales de endpoints.
- No editar los tipos generados a mano: se usa el generador de SPEC-028.
- Las redirecciones son temporales: no se documentan en OpenAPI.
- Se conserva `X-Request-ID`, `X-Registro-ID`, `X-Download-Token` y el formato SSE.

## 9. Cierre

La HU se cierra cuando AC1–AC4 estén cubiertos, `make check` equivalente pase en local, el
PR sea aprobado y `evidence.md` documente los resultados y limitaciones.
