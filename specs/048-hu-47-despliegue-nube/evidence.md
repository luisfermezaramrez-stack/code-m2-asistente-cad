# Evidencia · HU-47 (SPEC-048)

- **Rama**: `feature/hu-47-despliegue-nube` (creada desde `origin/main` @ `fcac0ce`).
- **Issue**: [#107](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/107) · **PR**: pendiente de apertura.
- **Fecha**: 2026-11-27.
- **Worktree**: `C:\Users\cetd9\AppData\Local\Temp\opencode\hu47-cloud`; se copiaron `vendor/` y `frontend/node_modules/` del worktree HU-50.
- **Entorno**: checkout local Windows; `make check` con `UV_PROJECT_ENVIRONMENT` apuntando al `.venv` principal, `UV_NO_SYNC=1`, `PYTHONPATH=src` y `M2_DOWNLOAD_SECRET` efímero.

## Condición de entrada

- #107 sigue **abierta** y asignada a `cetrujillo`; no había rama ni PR previos de HU-47.
- Dependencias fusionadas en `main`: #131 (SPEC-033, `a68ba88`), #124 (SPEC-037, `a87bdcd`), #132 (SPEC-046, `2621414`) y #133 (SPEC-054, `ec24917`). `git merge-base --is-ancestor` devuelve `0` para los cuatro merge commits.
- Auditoría de `jan-project-standard` sin `--force`: `✓ OK: 4 · ≠ DIFIERE: 21 · ✖ FALTA: 0`; las diferencias son personalizaciones legítimas ya documentadas.
- `plan.md` y `tasks.md` se redactaron antes de crear `docker-compose.cloud.yml`, `deploy/Caddyfile`, el validador y el runbook.

## Criterios de aceptación

| AC | Verificación local | Pendiente con autorización |
|----|--------------------|----------------------------|
| AC1 · HTTPS | `verify_hu47_cloud_config.py` comprueba Caddy con `{$M2_DOMAIN}`, HTTPS automático, `flush_interval -1`, ausencia de `ports` en la API y sonda `/v1/health`. `docker compose -f docker-compose.cloud.yml config --quiet` devuelve `0` con valores simulados. | Resolver DNS, emitir certificado y comprobar `https://$M2_DOMAIN/v1/health`. |
| AC2 · Punta a punta | El runbook parametriza `scripts/smoke_deploy.py --base-url "https://$M2_DOMAIN"`, sin ejecutarlo. Las pruebas no gastan tokens ni abren red. | Enviar una solicitud real desde la UI o el banco con credenciales y presupuesto. |
| AC3 · Reinicio | Compose usa volúmenes con nombre `m2-cad-data` y `m2-cad-outputs`; el worker espera `condition: service_healthy` de la API. El validador y `tests/test_hu47_cloud_config.py` lo comprueban. | Reiniciar la API con una solicitud en curso y verificar reanudación o estado informado. |
| AC4 · Rollback | El runbook fija imagen inmutable anterior, recreate ordenado API → worker, sonda y cronómetro de 15 minutos. | Cronometrar un rollback real y registrar el resultado. |

## Requisitos adicionales

- RF-1/RF-2: se elige VPS en la nube con Docker Compose y Caddy. El proveedor concreto no se contrató; la configuración no depende de una marca y no modifica el `Dockerfile`.
- RF-3/FRN-2: los secretos se inyectan desde el gestor del proveedor; autenticación, cookie `Secure` y CORS exacto están forzados. El validador no imprime valores secretos.
- RF-4: los volúmenes con nombre conservan cola, registro, respaldos y entregables; la API no publica puerto de host.
- RF-5: `docs/runbook-cloud.md` cubre despliegue, AC1–AC4, respaldos, rotación y rollback; está enlazado desde el runbook operativo, `docs/README.md`, `mkdocs.yml` y el README.
- RNF-3: las pruebas y el validador usan archivos versionados y variables simuladas; no hay red, Docker remoto, API key, GPU ni tokens.
- SPEC-048 se actualizó: ruta real `/v1/health`, dependencias ya fusionadas y referencia correcta a `src/m2_cad/web.py:16`.

## Comandos ejecutados

```text
uv run --no-project python -B scripts/verify_hu47_cloud_config.py --modo plantilla
  Configuración cloud consistente; pendiente: proveedor, DNS, certificado, imagen y AC1-AC4

docker compose -f docker-compose.cloud.yml config --quiet
  código 0

uv run --locked pytest tests/test_hu47_cloud_config.py tests/test_ci_parity.py -q
  22 passed

make lint
  All checks passed!

make check
  Ruff: All checks passed!
  prompts: 3 versión(es) verificadas
  cloud-config-check: configuración consistente
  api-contract-check / api-types-check: actualizados
  frontend: 14 archivos / 116 pruebas OK; typecheck OK; build OK (aviso de chunk grande conocido)
  docs-build: 212 Markdown, strict OK
  pytest: 772 passed, 5 failed, 90.95 % de cobertura (umbral 70 % superado)
```

## Fallos locales no atribuibles a HU-47

`make check` termina con error por cinco pruebas backend dependientes del checkout Windows. Se repitieron sobre un worktree limpio de `origin/main` (`fcac0ce`, `C:\Users\cetd9\AppData\Local\Temp\opencode\hu47-base`) y fallan idénticamente, así que son preexistentes y no tocan este cambio:

1. `tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia` — 7 huellas STEP distintas por la versión local de OpenCascade.
2. `tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas` — `msvcrt.locking` → `OSError [Errno 36] Resource deadlock avoided`.
3. `tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos` — `OSError [WinError 1314]`, sin privilegio para symlinks.
4. `tests/test_hu30_retencion.py::test_ac4_no_borra_directorio_con_enlace_interno` — misma causa `WinError 1314`.
5. `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms` — p95 de 91,2 ms local frente al objetivo ≤ 50 ms.

No se fijó `PYTHONIOENCODING=utf-8` en la corrida final: en Windows esa variable hace que `subprocess(text=True)` decode mal la salida de `verify_banco_replay.py` y añade un sexto fallo de codificación ajeno a esta HU.

## Lo que falta exactamente para publicar

1. Proveedor y cuenta autorizados; no se ha contratado ninguno.
2. Dominio propio bajo control DNS y correo de administración para ACME.
3. Imagen publicada en un registro accesible, con etiqueta o digest inmutable.
4. Valores reales de `DEEPSEEK_API_KEY`, `M2_DOWNLOAD_SECRET`, `M2_AUTH_SECRET` y `M2_AUTH_USERS` en el gestor del proveedor.
5. Credenciales de usuario y presupuesto autorizado para la prueba de generación real.

No se crearon cuentas, dominios, certificados, secretos reales ni despliegues; no se fusionó esta rama ni se crearon etiquetas o releases.
