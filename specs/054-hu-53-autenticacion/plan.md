# Plan de implementación · HU-53 (SPEC-054)

## Decisión de arquitectura

Se adopta una **sesión local con cookie firmada**, no OIDC. El proveedor externo queda
fuera de alcance porque las pruebas deben correr sin red, API key ni GPU (RNF-1) y el
despliegue actual es un único origen FastAPI + SPA (SPEC-037). La cookie `m2_sesion`
viaja con `HttpOnly`, `SameSite=Lax` y `Secure` configurable; la API y la UI comparten
origen, por lo que no se expone el token a JavaScript ni a la URL.

### Componentes

- `src/m2_cad/autenticacion.py`: configuración por entorno, hash PBKDF2-SHA256 de
  claves, emisión/validación de sesiones HMAC-SHA256, dependencia `usuario_actual` y
  comprobación de propiedad.
- `src/m2_cad/usuarios.py`: CLI para generar el hash de una clave sin versionarla.
- `src/m2_cad/api.py`: endpoints `/auth/login`, `/auth/logout`, `/auth/me`;
  dependencia de usuario en generación, consulta, cancelación, descarga y registro.
- `src/m2_cad/trabajos.py`: el trabajo en memoria conserva su propietario desde la
  creación. Al integrar `main`, la cola de HU-45 y su worker también guardan y
  registran el dueño (ver `evidence.md`, sección 5).
- `src/m2_cad/registro.py`: la fila del CSV incluye el usuario; las filas antiguas de
  8 columnas se migran añadiendo `anónimo`.
- `frontend/src/auth.ts`, `App.vue`: inicio/cierre de sesión, usuario activo y
  bloqueo de la generación mientras no haya sesión cuando la autenticación esté activa.

### Configuración

| Variable | Valor | Uso |
| --- | --- | --- |
| `M2_AUTH_ENABLED` | `1` por defecto; `0` sólo en desarrollo local/pruebas | Activa la autenticación. `/health` y `/ready` siguen abiertos. |
| `M2_AUTH_SECRET` | aleatorio, ≥32 bytes | Clave HMAC de las sesiones; obligatoria si está activa. |
| `M2_AUTH_USERS` | JSON `{"usuario": "<hash PBKDF2>"}` | Usuarios permitidos; nunca se versiona. |
| `M2_AUTH_COOKIE_SECURE` | `1` por defecto; `0` en HTTP local | Atributo `Secure` de la cookie. |
| `M2_AUTH_TTL_SECONDS` | `86400` (60–2592000) | Vigencia de la sesión. |

### Compatibilidad y seguridad

- Modo local explícito: `M2_AUTH_ENABLED=0` mantiene el comportamiento anterior y
  etiqueta las solicitudes como `anónimo`. La batería heredada y el smoke HTTP lo fijan.
- Las respuestas para un usuario ajeno son **404**, sin revelar existencia ni contenido
  (AC2). El token de descarga de HU-36 se exige además de la sesión.
- El registro incorpora la columna `usuario` al final; los CSV de 8 columnas se migran
  con bloqueo atómico antes de añadir filas. No se borra ni se reescribe información.
- Se conservan los contratos HTTP existentes; se añaden tres rutas `/auth/*` y se
  regeneran `frontend/src/generated/api.ts` y los tipos derivados del esquema.
- No se introducen dependencias nuevas: `hashlib`, `hmac`, `secrets` y `json` son
  biblioteca estándar; FastAPI y Pydantic ya están en el proyecto.

### Fuera de alcance

OIDC, roles finos, organizaciones, facturación y despliegue en la nube (SPEC-048). Los
topes de HU-32 (SPEC-033) se asocian al usuario al integrar `main`; el presupuesto
diario sigue siendo global.

## Verificación

1. `make check` (Ruff, `api-types-check`, Vitest, TypeScript, build y pytest/cobertura).
2. Pruebas HU-53 con proveedor simulado: 401 anónimo, aislamiento A/B, trazabilidad en
   el registro, salud abierta, cookie inválida y modo local.
3. Evidencia en `specs/054-hu-53-autenticacion/evidence.md` al cerrar la historia.
