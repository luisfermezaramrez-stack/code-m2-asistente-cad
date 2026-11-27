# Runbook de despliegue en la nube

 SPEC-048 / HU-47 · estado: **parametrizado, no ejecutado**. Este runbook deja el
procedimiento verificable sin crear cuentas, contratar proveedores, publicar imágenes ni
desplegar. Las secciones que se ejecutan contra un proveedor requieren autorización
explícita y los datos que se listan como pendientes.

## Alcance y pendiente exacto

La configuración versionada es `docker-compose.cloud.yml`, `deploy/Caddyfile` y
`scripts/verify_hu47_cloud_config.py`. No modifica el `Dockerfile` ni el contrato `/v1`.

Antes de publicar hacen falta, y **no están disponibles en este repositorio**:

1. Proveedor y cuenta autorizados; se propone un VPS en la nube de bajo costo con Docker y
   Compose. No se ha contratado ninguno.
2. Dominio propio bajo control DNS y correo de administración para ACME.
3. Referencia inmutable de la imagen publicada en un registro accesible al servidor.
4. Valores de secretos en el gestor del proveedor: `DEEPSEEK_API_KEY`,
   `M2_DOWNLOAD_SECRET`, `M2_AUTH_SECRET` y `M2_AUTH_USERS`. No hay valores reales aquí.
5. Credenciales de usuario y presupuesto autorizado para la prueba de generación real.

La verificación local de la estructura se ejecuta sin red ni secretos:

```bash
uv run --no-project python -B scripts/verify_hu47_cloud_config.py --modo plantilla
```

## Variables de la plantilla

Sólo se listan nombres; los valores se inyectan desde el entorno del proveedor.

| Variable | Uso | Requisito |
| --- | --- | --- |
| `M2_IMAGE` | Imagen inmutable de API y worker | etiqueta o digest; nunca `latest` |
| `M2_DOMAIN` | Sitio TLS y origen CORS | hostname sin esquema, puerto ni comodín |
| `M2_TLS_EMAIL` | Correo de administración para Caddy | dirección válida |
| `DEEPSEEK_API_KEY` | Llamadas al modelo (HU-14) | gestor de secretos; length ≥ 8 |
| `M2_DOWNLOAD_SECRET` | Firma de descargas (HU-36) | gestor de secretos; length ≥ 32 |
| `M2_AUTH_SECRET` | Firma de la cookie (HU-53) | gestor de secretos; length ≥ 32 |
| `M2_AUTH_USERS` | Usuarios PBKDF2 (HU-53) | JSON con al menos un hash |
| `LLM_MODEL` | Modelo solicitado | valor fijado por el equipo |
| `M2_LOG_LEVEL` | Nivel de logging estructurado | valor por defecto `INFO` |
| `MLFLOW_TRACKING_ENABLED` | Seguimiento opcional | por defecto `0` en la nube |

La API fuerza `M2_AUTH_ENABLED=1`, `M2_AUTH_COOKIE_SECURE=1`, `M2_COLA_HABILITADA=1`
y `M2_CORS_ORIGINS=https://$M2_DOMAIN`. El worker comparte la cola y los artefactos
mediante los volúmenes `m2-cad-data` y `m2-cad-outputs`. Caddy escucha en `80/443`,
termina TLS y no publica el puerto `8000` de la API.

## Despliegue parametrizado

No ejecutar sin el pendiente resuelto. Los secretos se exportan desde el gestor del
proveedor, sin escribir valores en el historial de la terminal.

```bash
export M2_IMAGE='<referencia-inmutable>'
export M2_DOMAIN='<dominio-propio>'
export M2_TLS_EMAIL='<correo-administracion>'
export LLM_MODEL='deepseek-v4-pro'
export MLFLOW_TRACKING_ENABLED='0'
uv run --no-project python -B scripts/verify_hu47_cloud_config.py --modo produccion
docker compose -f docker-compose.cloud.yml config --quiet
docker compose -f docker-compose.cloud.yml pull
docker compose -f docker-compose.cloud.yml up -d --remove-orphans
docker compose -f docker-compose.cloud.yml ps
```

Crear la API antes que el worker: Compose declara `depends_on` con
`condition: service_healthy`, basada en el `HEALTHCHECK` de la imagen contra
`/v1/health`. Reiniciar sólo el worker deja la cola cerrada; en ese caso recrear primero
la API y después el worker, como en el [runbook operativo](runbook-operativo.md).

## AC1 — Servicio accesible por HTTPS

Tras resolver DNS y emitir el certificado:

```bash
curl -fsS "https://$M2_DOMAIN/v1/health"
```

La respuesta es HTTP 200. Caddy usa HTTPS automático y no desactiva la renovación; no se
copian certificados ni claves privadas al repositorio. `/health` es una ruta plana que
sólo redirige con `307`; la sonda válida es `/v1/health`.

## AC2 — Generación de punta a punta

La prueba real gasta tokens y requiere autorización y usuario con sesión. Se reutiliza
el script existente, que acepta la URL base:

```bash
read -rs M2_SMOKE_CLAVE && export M2_SMOKE_CLAVE
export M2_SMOKE_USUARIO='<usuario-autorizado>'
uv run python scripts/smoke_deploy.py --base-url "https://$M2_DOMAIN" --n 5
unset M2_SMOKE_CLAVE
```

También puede enviarse una solicitud desde la UI con el dominio propio. Se acepta una
pieza con STEP, GLB y CSV o una declinación con motivo; un `422` con
`Pieza declinada:` no es un incidente. Un `401` indica sesión faltante y un `429` con
`X-Limite-Tipo` indica topes de HU-32, no fallo del proveedor.

## AC3 — Reinicio sin pérdida

Con una solicitud SSE en curso, recrear la API y esperar a que esté `healthy`, y luego
recrear el worker:

```bash
docker compose -f docker-compose.cloud.yml up -d --force-recreate m2-cad
docker compose -f docker-compose.cloud.yml ps m2-cad
docker compose -f docker-compose.cloud.yml up -d m2-cad-worker
docker compose -f docker-compose.cloud.yml logs --tail=100 m2-cad-worker
```

La solicitud se reanuda desde `m2-cad-data:/app/data/cola.json` o informa su estado sin
perderse. Los entregables y respaldos siguen en `m2-cad-outputs:/app/outputs` y
`m2-cad-data:/app/data/backups/`. No eliminar los volúmenes durante el reinicio.

## AC4 — Rollback

El objetivo es volver a la versión anterior en menos de 15 minutos, sin tocar volúmenes:

1. Anotar la referencia inmutable desplegada y la anterior. No usar `latest`.
2. Reexportar `M2_IMAGE` con la referencia anterior y validar:
   `uv run --no-project python -B scripts/verify_hu47_cloud_config.py --modo produccion`.
3. Recrear API y worker, en ese orden:
   `docker compose -f docker-compose.cloud.yml up -d m2-cad m2-cad-worker`.
4. Comprobar `curl -fsS "https://$M2_DOMAIN/v1/health"` y una solicitud del banco con
   la prueba de AC2.
5. Registrar la hora de inicio y fin; si supera 15 minutos, escalar y documentar la causa.

Si el fallo viene de un secreto o del modelo, primero aplicar la rotación o corrección y
recrear en el mismo orden; el rollback de imagen no resuelve credenciales inválidas.

## Rotación de secretos

Rotar en el gestor del proveedor, exportar los nuevos valores sin eco y recrear API y
worker en ese orden. No reconstruir ni publicar una imagen para cambiar secretos: la
imagen no los contiene. Después de rotar, repetir AC1 y AC2. Si un comando muestra una
clave, una URL privada o un token, detenerlo y escalar según el
[runbook operativo](runbook-operativo.md).

## Respaldos y restauración

Los respaldos vuelven en `data/backups/` dentro del volumen `m2-cad-data`. La rutina del
runbook operativo se aplica con el nombre de servicio `m2-cad`; no pegar respaldos en
tickets ni versionarlos. Una restauración debe hacerse con la API y el worker detenidos y
los volúmenes montados, para no sobrescribir la cola activa.

Evidencia local y comprobaciones pendientes:
[`specs/048-hu-47-despliegue-nube/evidence.md`](../specs/048-hu-47-despliegue-nube/evidence.md).
