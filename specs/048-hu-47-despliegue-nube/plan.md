# Plan de implementación · HU-47 (SPEC-048)

- **Rama**: `feature/hu-47-despliegue-nube`, creada desde `origin/main` en `fcac0ce`.
- **Issue**: [#107](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/107), abierta y asignada a `cetrujillo`.
- **Orden**: issue + spec → plan → tareas → configuración → pruebas → documentación → PR.
- **Auditoría del estándar**: no destructiva, `OK 4 · DIFIERE 21 · FALTA 0`; sin `--force`.
- **Dependencias**: PR #131 (HU-32), #124 (HU-36), #132 (HU-45) y #133 (HU-53) están fusionados en `main`; `git merge-base --is-ancestor` devuelve `0` para los cuatro merge commits.

## Objetivo

Dejar versionada y verificable localmente la configuración de despliegue en la nube con HTTPS, dominio propio, persistencia y rollback, sin crear cuentas, contratar servicios, publicar imágenes ni desplegar. La ejecución real queda documentada con la lista exacta de datos que faltan.

## Decisiones de diseño

1. Se elige un **VPS en la nube con Docker Compose y Caddy** como capa TLS. Es un proveedor de bajo costo con contenedores que conserva el sistema de archivos compartido entre API y worker (HU-45) sin reescribir la cola persistente ni el `Dockerfile`. El proveedor concreto, la cuenta, el dominio y el presupuesto quedan pendientes de autorización.
2. No se modifica el `Dockerfile`: la imagen ya construye frontend, vendor y Python, expone el puerto `8000`, usa un worker Uvicorn y comprueba `/v1/health`. SPEC-048 cita `/health`; esa referencia se corrige a la ruta pública real.
3. `docker-compose.cloud.yml` levanta `m2-cad`, `m2-cad-worker` y `caddy`. La API no publica puerto de host: Caddy termina TLS en `80/443` y proxya al servicio interno. El worker arranca después de que la API esté `healthy`, para no cerrar la cola (SPEC-046).
4. Los volúmenes con nombre `m2-cad-data` y `m2-cad-outputs` conservan `data/cola.json`, el registro, respaldos y entregables ante reinicios. No se usa `--force-recreate` en el procedimiento normal.
5. La autenticación (SPEC-054), la cookie `Secure` y el origen CORS exacto `https://$M2_DOMAIN` quedan forzados en la configuración cloud. Los secretos se inyectan desde el gestor del proveedor; nunca se versionan ni se escriben en la imagen.
6. `deploy/Caddyfile` usa `{$M2_DOMAIN}` y `{$M2_TLS_EMAIL}`. No desactiva HTTPS automático, no comprime SSE y mantiene `flush_interval -1` para no acumular eventos.
7. `scripts/verify_hu47_cloud_config.py` valida la estructura de los archivos versionados y, en modo `produccion`, la sintaxis de dominio y la presencia de secretos sin imprimirlos ni abrir red. El modo `plantilla` siempre informa lo que falta para publicar.
8. Las pruebas (`tests/test_hu47_cloud_config.py`) usan el repositorio y variables simuladas; no llaman al proveedor, no gastan tokens y no necesitan GPU, API key ni Docker.
9. El runbook cloud enlaza el runbook operativo y cubre despliegue, AC1–AC4, respaldos, rotación de secretos y rollback en menos de 15 minutos. Las órdenes reales quedan parametrizadas y marcadas como no ejecutadas.

## Criterios de aceptación cubiertos

| AC | Evidencia local | Verificación pendiente con autorización |
|----|-----------------|-----------------------------------------|
| AC1 — HTTPS | El validador comprueba Caddy, dominio TLS, ausencia de puerto de host y sonda `/v1/health`. | Resolver DNS, desplegar y comprobar `https://$M2_DOMAIN/v1/health` con certificado válido. |
| AC2 — Punta a punta | El runbook reutiliza `scripts/smoke_deploy.py --base-url https://$M2_DOMAIN` sin ejecutarlo. | Solicitar una pieza o declinación desde la UI con credenciales y presupuesto autorizados. |
| AC3 — Reinicio | Compose monta volúmenes con nombre y el worker depende de API `healthy`; el validador lo verifica. | Reiniciar la API con una solicitud en curso y comprobar reanudación/estado. |
| AC4 — Rollback | El runbook fija imagen anterior, recreate ordenado y comprobación de salud. | Cronometrar un rollback real y confirmar que termina en menos de 15 minutos. |

## Riesgos y fuera de alcance

- Caddy necesita DNS público apuntando al servidor y puertos `80/443` libres; sin eso no hay certificado. El validador no comprueba DNS ni red.
- Un VPS requiere parcheo y copias de seguridad del sistema; esto se documenta como responsabilidad del operador, no se automatiza.
- No se crean cuentas, imágenes remotas, dominios, certificados, secretos reales ni despliegues.
- No se rehace el empaquetado, no se escala horizontalmente y no se cambia el contrato `/v1`.
