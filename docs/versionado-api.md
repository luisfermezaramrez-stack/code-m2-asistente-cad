# Política de versionado de la API (HU-31, SPEC-032)

## 1. Versión pública

La API pública es `/v1`. Todas las rutas funcionales se publican bajo ese prefijo:

| Ruta canónica | Método |
| --- | --- |
| `/v1/health` | GET |
| `/v1/ready` | GET |
| `/v1/generar` | POST |
| `/v1/generaciones/{solicitud_id}` | GET, DELETE |
| `/v1/generaciones/{solicitud_id}/archivos/{formato}` | GET, HEAD |
| `/v1/registros/{identificador}` | GET |
| `/v1/registros/{identificador}/step` | GET |

El prefijo es parte del contrato. La SPA, los scripts de verificación y los tipos
generados consumen estas rutas. `/openapi.json` y `/docs` describen únicamente `/v1`.

## 2. Convivencia con las rutas planas

Las rutas sin prefijo (`/health`, `/generar`, …) siguen funcionando como
**redirecciones temporales `307`** hacia su equivalente `/v1`. La redirección conserva
método, cuerpo y query string.

La compatibilidad de AC1 depende de que el cliente **siga la redirección**: `httpx` con
`follow_redirects=True`, `curl -L` y `TestClient` (por defecto) la siguen. Un cliente que
no la siga recibe la `307` y debe reenviar la misma petición a `Location`; el servidor
no duplica la respuesta. Si la aplicación está montada bajo `root_path`, el destino
conserva ese prefijo (por ejemplo, `/api/v1/health`).

Cada respuesta de una ruta plana anuncia su obsolescencia:

```http
HTTP/1.1 307 Temporary Redirect
Location: http://127.0.0.1:8000/v1/generar
Deprecation: @1795564800
Sunset: Tue, 23 Feb 2027 00:00:00 GMT
Link: <http://127.0.0.1:8000/v1/generar>; rel="successor-version"
```

- `Deprecation: @1795564800` es la fecha de publicación de v1
  (`2026-11-25T00:00:00Z`) en el formato de fecha estructurada de **RFC 9745**. RFC 8594
  definía el valor booleano `true`; se conserva la mención histórica pero el servicio
  emite el formato final del RFC.
- `Sunset` fija el plazo de convivencia: **90 días** desde esa fecha. El valor por
  defecto es `Tue, 23 Feb 2027 00:00:00 GMT` y puede ampliarse con la variable
  `M2_SUNSET_RUTAS_PLANAS` si se retrasa el despliegue, sin acortar el plazo anunciado.
- `Link` señala la ruta que la sustituye.

Las redirecciones no aparecen en el OpenAPI publicado: son un puente temporal, no parte
del contrato congelado. Después del `Sunset` se retiran y cualquier cambio incompatible
posterior exige una versión mayor nueva (`/v2`).

## 3. Contrato congelado

`contracts/openapi-v1.json` es una fotografía determinista del documento devuelto por
`app.openapi()` (UTF-8, claves ordenadas, dos espacios, LF). `info.version` es `1.0.0`.

- `make api-contract` regenera el archivo.
- `make api-contract-check` falla si el esquema en memoria diverge del archivo; se
  ejecuta también en `make check` y en CI.
- `make api-types` / `make api-types-check` mantienen alineados los tipos TypeScript
  generados desde el mismo esquema.

Quitar un campo, cambiar su tipo, eliminar una ruta o alterar un código de respuesta
rompe la comprobación. No basta con editar el JSON: hay que decidir si el cambio es
compatible o si merece una nueva versión mayor.

## 4. Reglas de cambio

| Tipo de cambio | Acción |
| --- | --- |
| Añadir un campo opcional | Se puede publicar dentro de v1: actualizar contrato, tipos y documentación en el mismo PR |
| Quitar/renombrar un campo o ruta | Requiere `/v2`; `/v1` permanece hasta su `Sunset` |
| Corregir un error que cambia el comportamiento | Decidir si es compatible; si no, nueva versión mayor |
| Cambiar autenticación o semántica de descargas | Nueva versión mayor, nunca una redirección |

Toda decisión de este tipo se registra en `CONSTITUTION.md` y en el `evidence.md` de la
historia correspondiente.

## 5. Alcance

Esta política cubre la API HTTP/SSE. Las rutas estáticas de la SPA (`/`, `/assets/...`)
no se versionan. Las rutas API desconocidas siguen devolviendo `404` con `content-type:
application/json`, nunca el índice Vue. No se introduce autenticación ni `/v2` en esta HU.
