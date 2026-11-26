# Tareas · SPEC-030 / HU-29

- [x] T01 — Leer SPEC-030, fijar alcance y crear `plan.md` y `tasks.md`.
- [x] T02 — Crear `docs/runbook-operativo.md` con los ocho escenarios de RF-1: síntoma,
  diagnóstico, acción, verificación de recuperación y escalado; distingue caída de aplicación,
  fallo de proveedor y configuración.
- [x] T03 — Contrastar comandos y rutas con `README.md`, `docker-compose.yml`, `Makefile`,
  `Dockerfile` y `src/m2_cad/`; registrar salida esperada y límites de ejecución local.
- [x] T04 — Escenario «Cuenta sin crédito» (HTTP 402; síntoma, diagnóstico, acción y verificación).
- [x] T05 — Escenario «Respuesta inválida del modelo» (salida no programable o validador fallido).
- [x] T06 — Escenario «Rotación de la clave DeepSeek» (sin exponer la clave en historial ni logs).
- [x] T07 — Escenario «Rollback de la versión de modelo» (`LLM_MODEL` / `LLM_MODEL_VERSION`).
- [x] T08 — Escenario «Rollback de la imagen del servicio» (build/Compose y vuelta atrás).
- [x] T09 — Escenario «Restauración de `data/registro.csv`».
- [x] T10 — Escenario «Restauración de `outputs/`».
- [x] T11 — Enlazar `docs/runbook-operativo.md` desde `README.md` (AC3).
- [x] T12 — Ejecutar los comandos de diagnóstico con contenedor real y sin mostrar la API key
  (AC2). El puerto 8000 estaba ocupado; se validó en 8001 con un override temporal. El humo real
  no se ejecutó por no disponer de clave/autorización de gasto.
- [x] T13 — Ejecutar controles finales (`git diff --check`, Ruff, pytest), abrir PR #136,
  actualizar `specs/README.md` con su número y vincular #89.

## Evidencia

Detalle completo en [`evidence.md`](./evidence.md). Resumen:

- `git diff --check` y comprobación de archivos nuevos: sin errores de whitespace.
- `docker compose config --quiet` y `make -n up` / `make -n down`: correctos.
- Contenedor `m2-cad` en `127.0.0.1:8001` (antes de integrar `main`, con rutas planas): `Up (healthy)`, `/health` 200 y `/ready` 503 con
  `"modelo":"no_disponible"` y `"registro":"ok"` (sin clave real).
- Comprobación de presencia de clave: `ausente`; tras rotación ficticia: `configurada`;
  sin secretos en logs.
- `backup`/`restore` de `registro.csv` y de `outputs/` ejecutados con archivos temporales.
- Rollback de imagen ejecutado con etiqueta `ultima-buena`.
- Ruff: `All checks passed!`.
- Pytest con build frontend y `M2_DOWNLOAD_SECRET` ficticio: `413 passed, 5 failed`; los cinco
  fallos son de entorno Windows/carga local y se detallan en la evidencia.
- Repetición sin esos cinco casos: `413 passed, 5 deselected`.
