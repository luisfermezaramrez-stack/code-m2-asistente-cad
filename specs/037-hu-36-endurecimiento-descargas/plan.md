# HU-36 — Plan técnico de seguridad de descargas

## 1. Objetivo

Proteger los artefactos CAD mediante tokens vinculados a cada solicitud, expiración configurable y validación estricta de UUID, sin modificar la generación CAD ni el procesamiento SSE.

## 2. Arquitectura propuesta

El sistema utilizará tokens firmados mediante HMAC-SHA256.

1. FastAPI crea una solicitud y genera su token de descarga.
2. El token se asocia al UUID y contiene una fecha de expiración protegida por la firma.
3. FastAPI entrega el token al cliente mediante una cabecera HTTP.
4. Vue conserva el token temporalmente en memoria.
5. Vue envía `X-Download-Token` en las solicitudes HEAD y GET.
6. FastAPI verifica UUID, firma y expiración antes de acceder al archivo.

El UUID identifica la solicitud, pero no constituye una credencial de autorización.

## 3. Componentes

| Archivo | Responsabilidad |
|---|---|
| `seguridad_descargas.py` | Generación y validación de tokens |
| `api.py` | Protección de endpoints y entrega de tokens |
| `trabajos.py` | Integración del token con el ciclo de vida de solicitudes |
| `frontend/src/api.ts` | Autorización de consultas y descargas |
| `test_seguridad_descargas.py` | Pruebas de seguridad |

## 4. Configuración propuesta

- `M2_DOWNLOAD_SECRET`: secreto de firma, configurado de forma segura y persistente.
- `M2_DOWNLOAD_TTL_SECONDS`: duración de los tokens, inicialmente 3600 segundos como valor propuesto.
- Cabecera de autorización: `X-Download-Token`.

Los tokens no se incluirán en URLs, registros CSV, MLflow ni eventos SSE.

## 5. Contrato HTTP

| Condición | Código |
|---|---|
| UUID inválido | 422 |
| Token ausente o incorrecto | 403 |
| Token válido, pero expirado | 410 |
| Archivo autorizado y disponible | 200 |
| Archivo autorizado, pero inexistente | 404 |

La verificación de credenciales ocurrirá antes de consultar el archivo.

## 6. Endpoints afectados

- `GET /registros/{identificador}`: validación estricta de UUID.
- `GET /registros/{identificador}/step`: UUID, token y expiración.
- `GET /generaciones/{solicitud_id}/archivos/{formato}`: UUID, token y expiración.
- `HEAD /generaciones/{solicitud_id}/archivos/{formato}`: mismas validaciones que GET.

Se conservarán los tipos MIME permitidos, la restricción a `outputs/` y las cabeceras `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`.

## 7. Estrategia de pruebas

Las pruebas utilizarán Pytest, TestClient, archivos temporales y dependencias simuladas, sin GPU ni llamadas a DeepSeek.

Se verificarán AC1, AC2 y AC3, además de no regresiones en descargas válidas, SSE y frontend.

## 8. Alcance y restricciones

- No implementar autenticación de usuarios.
- No implementar limpieza automática de artefactos.
- No modificar el pipeline CAD.
- No exponer secretos en respuestas de estado ni observabilidad.
- Mantener compatibilidad con Vue y las solicitudes SSE existentes.

## 9. Cierre

La historia se considerará terminada cuando las pruebas de seguridad, FastAPI y frontend pasen, la evidencia esté documentada y el PR sea aprobado.