# Tareas · HU-47 (SPEC-048)

Orden de ejecución; la evidencia final vive en [evidence.md](./evidence.md).

- [x] T0 · Verificar que #107 sigue abierta y asignada a `cetrujillo`, leer SPEC-048, confirmar que SPEC-033/037/046/054 están fusionadas en `main`, buscar rama/PR previa y auditar el estándar sin `--force`.
- [x] T1 · Redactar `plan.md` y `tasks.md` antes de tocar configuración; elegir VPS con Docker Compose y Caddy y registrar lo que falta para publicar.
- [x] T2 · Corregir en SPEC-048 la ruta `/v1/health`, el estado de las dependencias y la referencia a `web.py`.
- [x] T3 · Crear `docker-compose.cloud.yml` con Caddy, API, worker, volúmenes con nombre, auth/cookie segura y secretos inyectados.
- [x] T4 · Crear `deploy/Caddyfile` con TLS automático, dominio parametrizado y SSE sin buffering.
- [x] T5 · Crear `scripts/verify_hu47_cloud_config.py` y `tests/test_hu47_cloud_config.py`; validar estructura, dominio y secretos sin red ni impresión de valores.
- [x] T6 · Crear `docs/runbook-cloud.md`; enlazarlo desde `docs/runbook-operativo.md`, `docs/README.md`, `mkdocs.yml` y `README.md`.
- [x] T7 · Actualizar `CONSTITUTION.md` y `specs/README.md` en la misma rama.
- [x] T8 · Ejecutar verificaciones locales, registrar `evidence.md` con lo pendiente y abrir PR a `main` con `Closes #107` sin desplegar ni contratar.
