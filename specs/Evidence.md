# Evidencia · HU-29 Runbook operativo

- **Fecha:** 2026-11-25
- **Spec:** [SPEC-030](030-hu-29-runbook-operativo/spec.md)
- **Rama:** `feature/hu-29-runbook-operativo`
- **PR:** [#136](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/136)
- **Worktree:** `C:\Users\cetd9\AppData\Local\Temp\opencode\hu29-runbook`
- **Base:** `origin/main` en `cf7e908ff4cf69e61844a850f846d7807c3d3c2c`
- **Alcance:** ocho escenarios de RF-1, enlace desde README y convivencia con HU-28 sin cambios.

## Criterios de aceptación

| AC | Resultado | Evidencia |
| --- | --- | --- |
| AC1 — Estructura por escenario | Cumplido | `docs/runbook-operativo.md` cubre 8/8 escenarios con síntoma, diagnóstico, acción, verificación de recuperación y escalado. Cada diagnóstico/acción incluye comandos exactos. |
| AC2 — Comandos ejecutables | Cumplido con salvedad documentada | Diagnósticos ejecutados en contenedor real con puerto 8001 (8000 estaba ocupado por otro servicio). Sin secretos en pantalla. El humo real no se ejecutó: requiere clave y gasto de tokens. |
| AC3 — Descubrible | Cumplido | `README.md` → «Operación e incidentes» → `docs/runbook-operativo.md`. |

## Estandarización del repositorio

Skill `jan-project-standard` cargada y aplicada sin scaffolder destructivo.

```powershell
$env:PYTHONIOENCODING='utf-8'
python "C:\Users\cetd9\.agents\skills\jan-project-standard\scripts\new_project.py" --path . --audit
```

Resultado: `✓ OK: 4 · ≠ DIFIERE: 21 · ✖ FALTA: 0`. Las diferencias son particularidades ya
declaradas en `CONSTITUTION.md` (Python 3.12, hatchling, integración existente), no ausencias.
`CONSTITUTION.md` se actualiza en el mismo commit con el runbook y la convención de respaldos.

## Validación estática y de entorno

| Comando | Resultado |
| --- | --- |
| `docker compose config --quiet` con `M2_DOWNLOAD_SECRET=placeholder` | Correcto; secreto no impreso |
| `make -n up` / `make -n down` | `docker compose up` / `docker compose down` |
| `git diff --check` | Sin errores de whitespace |
| `git diff --no-index --check` sobre archivos nuevos | Correcto; solo avisos LF→CRLF de Windows |
| `uv run --no-sync ruff check src tests scripts/verify_hu15_deployment.py scripts/generate_api_types.py` | `All checks passed!` |
| `uv run --no-sync python scripts/generate_api_types.py --check` | `Tipos OpenAPI actualizados.` |
| `npm --prefix frontend test` | 3 archivos, 50 pruebas pasadas |
| `npm --prefix frontend run typecheck` | `vue-tsc --noEmit` sin errores |
| `npm --prefix frontend run build` | Build Vite correcto; aviso de chunk > 500 kB |
| `uv run --no-sync pre-commit run --files ...` sobre los archivos de HU-29 | Todos los hooks aplicables pasaron |

El entorno de validación fue un venv temporal creado con `uv` y
`--no-install-package python-solvespace --no-install-package llama-cpp-python`, porque en Windows
esos sdists requieren MSVC/`nmake`. El warning de `VIRTUAL_ENV` distinto se ignora porque
`UV_PROJECT_ENVIRONMENT` apunta al venv temporal.

## Validación con contenedor real

El puerto `127.0.0.1:8000` respondía `{"status":"ok","service":"mantenimientos"}` (PID 18324),
ajeno al proyecto. Para no interferir, se construyó el proyecto `hu29validate` con un override
temporal que publica `127.0.0.1:8001->8000/tcp`. Los comandos internos del contenedor son los
mismos del runbook; solo cambia el puerto y el nombre del proyecto de Compose.

```powershell
$env:M2_DOWNLOAD_SECRET='dummy_secret_for_local_tests_20261125'
Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
docker compose -p hu29validate -f docker-compose.yml -f <override> up -d --build m2-cad
```

Resultados:

| Comando | Salida observada |
| --- | --- |
| `docker compose ps` | `hu29validate-m2-cad-1 ... Up 8 seconds (healthy) 127.0.0.1:8001->8000/tcp`; `hu29validate-mlflow-1 ... Up` |
| `curl.exe .../health` | `{"status":"ok"}` · `HTTP 200` |
| `curl.exe .../ready` | `{"status":"no_disponible","dependencias":{"modelo":"no_disponible","registro":"ok"}}` · `HTTP 503` |
| `docker compose exec -T m2-cad uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"` | `ausente` |
| `docker compose logs --no-color --tail=30 m2-cad` | `Application startup complete.` y GET `/health` 200, `/ready` 503; sin secretos |
| Configuración efectiva | `LLM_MODEL=deepseek-v4-pro`, `LLM_MODEL_VERSION=no-fijado` |
| Rotación ficticia + `up -d --force-recreate` | `configurada`; al retirar la variable ficticia, `ausente` de nuevo |
| Rollback de imagen con etiqueta `ultima-buena` | `ROLLBACK_IMAGE_OK`; contenedor recreado; `/health` 200 tras el arranque |

`LLM_MODEL_VERSION=no-fijado` confirma lo documentado: `docker-compose.yml` no interpola esa
variable. No se usó ninguna clave real ni se hicieron llamadas pagas al proveedor.

## Backup y restauración

Se ejecutaron dentro del contenedor con archivos temporales, sin tocar los datos reales:

| Comando | Salida |
| --- | --- |
| `python -m m2_cad.persistencia_registro backup --registro data/registro-runbook-prueba.csv --destino backups/registro-runbook-prueba.csv` | `backup: backups/registro-runbook-prueba.csv` |
| `python -m m2_cad.persistencia_registro restore --registro data/registro-runbook-prueba.csv --origen backups/registro-runbook-prueba.csv` | `restore: data/registro-runbook-prueba.csv` |
| `tar -czf /app/backups/outputs-runbook-prueba.tar.gz -C /app outputs` + borrado temporal + `tar -xzf ... -C /app` | `OUTPUTS_RESTORE_OK` |

Los temporales se eliminaron (`CLEANUP_OK`). El primer intento con `python` del sistema falló con
`ModuleNotFoundError: No module named 'm2_cad'`; por eso el runbook usa
`uv run --no-sync python`, que sí resuelve el paquete dentro de la imagen.

## Pytest

Con `frontend/dist` compilado y `M2_DOWNLOAD_SECRET` ficticio:

```powershell
$env:M2_DOWNLOAD_SECRET='dummy_secret_for_local_tests_20261125'
uv run --no-sync pytest -q
```

Resultado: `5 failed, 413 passed, 26 warnings in 52.98s`. Los cinco fallos son ajenos al cambio
(documentación) y dependientes del entorno local Windows:

1. `test_ac1_80_solicitudes_simultaneas_sin_perdidas`: `OSError: [Errno 36] Resource deadlock avoided`
   en `msvcrt.locking` bajo 16 hilos.
2. `test_ac1_duplicados_concurrentes_son_idempotentes`: mismo error con 12 hilos.
3. `test_ac4_no_sigue_enlaces_simbolicos`: `OSError: [WinError 1314] El cliente no dispone de un
   privilegio requerido` al crear symlink.
4. `test_ac4_no_borra_directorio_con_enlace_interno`: mismo WinError 1314.
5. `test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`: `p95=154.1 ms` frente al umbral de
   50 ms, por carga local de MLflow en este equipo.

Repetición excluyendo solo esos cinco casos:

```powershell
uv run --no-sync pytest -q --deselect tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas --deselect tests/test_hu30_registro.py::test_ac1_duplicados_concurrentes_son_idempotentes --deselect tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos --deselect tests/test_hu30_retencion.py::test_ac4_no_borra_directorio_con_enlace_interno --deselect tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms
```

Resultado: `413 passed, 5 deselected, 26 warnings in 34.35s`.

No se ejecutó `make check` literalmente en Windows por los sdists nativos indicados arriba; se
ejecutaron sus componentes equivalentes (Ruff, tipos OpenAPI, Vitest, TypeScript, build y
pytest). `make security-secrets` sigue pendiente de `gitleaks` en CI, sin relación con HU-29.

## Limpieza

Los contenedores de validación se detuvieron con:

```powershell
$env:M2_DOWNLOAD_SECRET='dummy_secret_for_local_tests_20261125'
docker compose -p hu29validate -f docker-compose.yml -f <override> down
```

El trabajo de HU-28 se conserva intacto en su workspace y worktree; este PR no lo modifica.
