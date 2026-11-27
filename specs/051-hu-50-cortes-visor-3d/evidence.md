# Evidencia · HU-50 (SPEC-051)

- **Rama**: `feature/hu-50-cortes-visor-3d` (creada desde `origin/main` @ `042adfb`).
- **Issue**: [#110](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/110) · **PR**: [#155](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/155) (`Closes #110`), abierto para revisión, sin fusionar.
- **Fecha**: 2026-11-27.
- **Worktree**: `C:\Users\cetd9\AppData\Local\Temp\opencode\hu50-cortes`; se copiaron `vendor/` y `frontend/node_modules/` del checkout principal.
- **Entorno**: checkout local Windows; `make check` con `UV_PROJECT_ENVIRONMENT` apuntando al `.venv` principal, `UV_NO_SYNC=1`, `PYTHONPATH=src` y `M2_DOWNLOAD_SECRET` efímero de 32 bytes.

## Condición de entrada

- PR #148 (HU-39/SPEC-040) está **fusionado** en `main`: `mergedAt=2026-11-27T14:56:24Z`, `mergeCommit=eb99715e2cb5a736bc88d24ebe755d0de3242945`; `git merge-base --is-ancestor eb99715… origin/main` devuelve `0`.
- #110 sigue **abierta** y asignada a `cetrujillo`; no había rama ni PR previos de HU-50.
- Auditoría de `jan-project-standard` sin `--force`: `✓ OK: 4 · ≠ DIFIERE: 21 · ✖ FALTA: 0`.

## Criterios de aceptación

| AC | Verificación |
|----|--------------|
| AC1 · Corte por eje | `frontend/tests/GlbViewer.test.ts` activa «Cortar Z (alto)» sobre la caja simulada 40×30×5: el `Plane` queda con normal `(0,0,1)` y constante `0`, `localClippingEnabled=true`, el material recibe un plano y la cara de sección con `stencilFunc=517` queda visible. `frontend/tests/viewerCortes.test.ts` comprueba ejes X/Y/Z, posición media, normales y constantes. |
| AC2 · Ajuste y desactivación | Mover el deslizador a `4` cambia la constante a `-1.5` sin nuevo `fetch`; «Invertir corte» da normal `-Z` y constante `+1.5`; «Desactivar corte» vacía `clippingPlanes` y oculta la tapa. El helper acota posiciones fuera de la caja y convierte `-0` en `0`. |
| AC3 · Accesibilidad | El grupo «Cortes y secciones» expone botones con nombre y `aria-pressed`, un `input[type=range]` con `aria-valuetext` y una región `role=status aria-live=polite`. Con foco en `.model-canvas`, `6` activa Z y anuncia `2.50 mm`, `C` desactiva, `4` activa X y `]` mueve a `20.40 mm`. |

## Requisitos adicionales

- RF-2: dos pasadas de stencil sobre la geometría cargada y una malla de relleno con `NotEqualStencilFunc` + `ReplaceStencilOp`; `onAfterRender` limpia el stencil. La comprobación visual de agujeros atravesando la sección queda para revisión manual/E2E con un GLB real.
- RF-4: el corte convive con `OrthographicCamera`, vistas, cotas y PNG; `capturar()` sigue haciendo `render()` antes de `toDataURL`.
- RF-5/RNF: `viewerCortes.ts` es puro y no importa `three`; las pruebas simulan `three`, `GLTFLoader`, `OrbitControls`, `RoomEnvironment`, `fetch` y `ResizeObserver`, sin GPU, red, API key ni modelo remoto.
- La referencia a `PerspectiveCamera` en el contexto de SPEC-051 quedó corregida: la base ya usa `OrthographicCamera` desde SPEC-040.
- El aviso de chunk grande de `GlbViewer` en `vite build` ya existía en HU-38/HU-39 y no cambia con esta HU.

## Comandos ejecutados

```text
npm --prefix frontend test
  Test Files 14 passed (14)
  Tests 116 passed (116)

npm --prefix frontend run typecheck
  vue-tsc --noEmit → sin errores

npm --prefix frontend run build
  ✓ built in 1.64 s (651.96 kB GlbViewer; aviso de chunk >500 kB)

make check  (con las variables temporales indicadas)
  Ruff: All checks passed!
  verify_prompts.py: 2 versión(es) verificadas
  generate_api_contract.py --check: Contrato OpenAPI v1 actualizado.
  generate_api_types.py --check: Tipos OpenAPI actualizados.
  frontend-test: 14 archivos / 116 pruebas OK
  frontend-typecheck: OK
  frontend-build: ✓ built in 450 ms
  pytest: 733 passed, 5 failed, 92.17 % de cobertura (umbral 70 % superado)

uv run pre-commit run --files <archivos de HU-50>
  tailwhitespace / end-of-file / large-files: Passed
```

## Fallos locales no atribuibles a HU-50

`make check` termina con error por cinco pruebas backend dependientes del checkout Windows. Se repitieron sobre un worktree limpio de `origin/main` (`042adfb`) y fallan idénticamente, así que son preexistentes y no tocan este cambio:

1. `tests/test_corpus_dorado.py::test_runner_sale_cero_sin_divergencias_y_uno_con_divergencia` — 7 huellas STEP distintas por la versión local de OpenCascade.
2. `tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas` — `msvcrt.locking` → `OSError [Errno 36] Resource deadlock avoided`.
3. `tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos` — `OSError [WinError 1314]`, sin privilegio para symlinks.
4. `tests/test_hu30_retencion.py::test_ac4_no_borra_directorio_con_enlace_interno` — misma causa `WinError 1314`.
5. `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms` — `p95=189.4 ms` local frente al objetivo ≤ 50 ms.

`make precommit` sobre todo el repo reformateó 7 archivos Python y 5 specs ajenos a HU-50; se revirtieron esos cambios y se volvió a ejecutar pre-commit sólo sobre los archivos de esta HU, con resultado limpio.

## CI del PR #155

Sobre el commit de código `b7b23c42441a6e9e05e7c3fee82c02b60a99fad9` (el registro de esta evidencia se añadió en un commit documental posterior):

- `test`: pass (2 m 1 s) — [run](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46033682926/job/140623583789).
- `e2e`: pass (40 s) — [run](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46033682926/job/140623584739).
- `dependencias`: pass (19 s) — [run](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46033682894/job/140623583535).
- `secretos`: pass (13 s) — [run](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46033682894/job/140623583980).
- `espejo`: pass (5 s) — [run](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/runs/46033650040/job/140623472721).

Revisión solicitada a `luisfermezaramrez-stack`. El PR queda abierto; no se fusiona ni se crean tags/releases.
