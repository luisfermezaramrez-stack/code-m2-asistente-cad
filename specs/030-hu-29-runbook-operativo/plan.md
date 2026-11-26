# Plan · HU-29 — Runbook operativo

## Base y alcance

- Rama: `feature/hu-29-runbook-operativo`, desde `origin/main` (`cf7e908`).
- Fuente: SPEC-030 e issue #89. RF-1 define ocho escenarios; los ocho quedan cubiertos en
  `docs/runbook-operativo.md` con síntoma, diagnóstico, acción, verificación de recuperación y
  escalado, con comandos exactos (AC1/RF-2/RF-3).
- El runbook se enlaza desde `README.md` (AC3), bajo «Operación e incidentes».
- Los comandos usan `make`, `uv`, `docker compose` y `curl`, y no imprimen ni escriben
  `DEEPSEEK_API_KEY`, `LLM_API_KEY` ni `M2_DOWNLOAD_SECRET` (RNF-1).
- `backups/` se añade a `.gitignore` para que snapshots y tar de respaldo nunca se versionen.

## Fuentes de verdad para los comandos

- `README.md:144-186`: instalación, variables del modelo y errores 401/402/429 en español.
- `README.md:236-289`: `make up`, `make down`, `/health`, `/docs` y
  `uv run python scripts/smoke_deploy.py --n 5`.
- `docker-compose.yml:28-44`: servicio `m2-cad`, puerto `127.0.0.1:8000`, volúmenes `data/`
  y `outputs/`, y variables de entorno.
- `src/m2_cad/api.py:97-100`: `/health` devuelve `{"status": "ok"}`.
- `src/m2_cad/api.py:157-171`: `/ready` informa `modelo` y `registro` sin llamar al proveedor.
- `src/m2_cad/pipeline.py:100-105`: `MENSAJES_HTTP` para 401/402/429.
- `src/m2_cad/pipeline.py:389-431`: distingue configuración ausente, timeout, HTTP y fallo de
  conexión; el proveedor se registra redactado.
- `src/m2_cad/llm_resiliente.py:143-219`: reintentos solo para 500/502/503/504, timeout y
  transporte; las respuestas inválidas no se cachean.
- `src/m2_cad/observabilidad.py:33-47`: variables sensibles y reglas de redacción de logs.
- `src/m2_cad/persistencia_registro.py:111-140`: `backup()` y `restore()` con snapshot
  consistente y reemplazo atómico.
- `Dockerfile:51-52`: healthcheck de la imagen consulta `/health`.

## Estructura y orden

1. Encabezado común con ámbito, convención de "salida esperada" y criterios de escalado.
2. Ocho secciones, una por incidente de RF-1, con el mismo formato.
3. Enlace desde el README como cierre de descubribilidad (AC3).
4. Registro de evidencia en `specs/Evidence.md`: comandos ejecutados localmente frente a
   comandos verificados solo contra el repositorio.
5. Actualización de `CONSTITUTION.md` en el mismo commit, conforme a la directiva de
   mantenimiento y al skill `jan-project-standard`.

## Verificación prevista y ejecutada

- Sin credenciales ni llamadas al modelo: `git diff --check`,
  `docker compose config --quiet` con un valor ficticio de `M2_DOWNLOAD_SECRET`,
  `make -n up` / `make -n down` y lectura del código.
- Con contenedor real: build de la imagen, `docker compose ps`, `/health`, `/ready`,
  presencia de clave, logs redactados, rotación con valor ficticio, backup/restore del CSV,
  backup/restore de `outputs/` y rollback de imagen. El puerto 8000 estaba ocupado por un
  servicio ajeno, así que la validación usó un override temporal a 8001 con el mismo comando
  internamente.
- Con frontend compilado: `uv run --no-sync pytest -q` y Ruff en el entorno temporal creado
  con `uv` sin paquetes nativos Windows.
- No se ejecutó el humo contra DeepSeek: no hay clave real y gasto de tokens requiere
  autorización. Queda marcado como verificado solo contra el repositorio.
