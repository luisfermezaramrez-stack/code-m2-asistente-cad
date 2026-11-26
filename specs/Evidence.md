# Evidencia · HU-34 Sistema de diseño v2 y modo oscuro

- **Fecha:** 2026-11-25
- **Spec:** [SPEC-035](035-hu-34-sistema-diseno-v2/spec.md)
- **Historia:** [#94](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/issues/94)
- **Rama:** `feature/hu-34-sistema-diseno-v2`
- **Worktree:** `C:\Users\cetd9\AppData\Local\Temp\opencode\hu34-design-v2`
- **Base:** `origin/main` en `cf7e908ff4cf69e61844a850f846d7807c3d3c2c`
- **PR:** [#137](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/pull/137)

## Criterios de aceptación

| AC | Resultado | Evidencia |
| --- | --- | --- |
| AC1 — Contraste en ambos temas | Cumplido | `frontend/tests/tokens.test.ts` recalcula 12 pares texto/fondo y 5 pares de foco/borde/visor desde el CSS; umbral 4.5:1 y 3:1. Valores en `docs/diseno-v2.md`. |
| AC2 — Cambiar un token no toca componentes | Cumplido | Los 63 tokens siguen en un único archivo importado una vez desde `main.ts`. La prueba verifica que `style.css` y `App.vue` no contienen colores hexadecimales; el cambio de tema solo redefine variables. |
| AC3 — Selección de tema | Cumplido | `theme.test.ts` cubre sistema oscuro sin preferencia, preferencia explícita que gana al sistema, persistencia y cambios del sistema en caliente; `App.test.ts` cubre el botón de la cabecera. |
| AC4 — Tokens dentro del frontend | Cumplido | `frontend/src/design/tokens.css` sustituye a `../../design/tokens.css`; se retiró la copia del `Dockerfile` y `fs.allow: ['..']` de `vite.config.ts`. |

## Estandarización `jan-project-standard`

Skill cargada antes de tocar el repositorio; modo no destructivo, sin `--force` ni scaffolder
sobre archivos existentes.

```powershell
$env:PYTHONIOENCODING='utf-8'
python "C:\Users\cetd9\.agents\skills\jan-project-standard\scripts\new_project.py" --path . --audit
```

Resultado: `✓ OK: 4 · ≠ DIFIERE: 21 · ✖ FALTA: 0`. Los 21 `DIFIERE` son personalizaciones ya
declaradas del proyecto (stack, gobernanza y convenciones propias), no ausencias. `CONSTITUTION.md`
se actualiza en el mismo commit con la nueva fuente de tokens y la regla de resolución de tema.
No se solicitó identidad Git automática, por lo que no se tocó `~/.gitconfig`.

## Decisión de implementación

- `frontend/src/design/tokens.css`: mismos nombres de HU-15, `:root` claro, bloque
  `@media (prefers-color-scheme: dark)` para ausencia de `data-theme`, y
  `:root[data-theme='dark']` para la elección explícita.
- `frontend/src/design/theme.ts`: `localStorage` → `matchMedia` → claro. Aplica `data-theme` a
  `<html>`, persiste `setTheme()` y permite `clearThemePreference()`. Escucha cambios del sistema
  solo sin preferencia guardada.
- `App.vue`: único botón de tema en la cabecera, con etiqueta accesible; usa solo tokens.
- `GlbViewer.vue`: relee `--color-viewer-background` al cambiar de tema para conservar RNF-3.
- `docs/diseno-v2.md`: documentación de tokens, escala tipográfica, precedencia y contrastes.
- `design/` queda como referencia histórica de HU-15; se añadió el aviso en sus dos documentos.
- `@types/node` se añadió al frontend porque en Vitest `import '*.css?raw'` devuelve una cadena
  vacía; las pruebas leen el CSS desde disco con `node:fs`.

## Validación frontend

| Comando | Resultado |
| --- | --- |
| `npm --prefix frontend ci` | 175 paquetes instalados; 9 avisos de auditoría ajenos al cambio |
| `npm --prefix frontend install --save-dev @types/node@24` | 2 paquetes añadidos; lockfile actualizado |
| `npm --prefix frontend test` | 5 archivos, 61 pruebas pasadas |
| `npm --prefix frontend run typecheck` | `vue-tsc --noEmit` sin errores |
| `npm --prefix frontend run build` | Build Vite correcto; aviso conocido de chunk GlbViewer > 500 kB |

Las pruebas nuevas son 8: 6 de tokens/contraste y 2 de preferencia de tema dentro de la suite
existente (61 en total). Ninguna usa red, API key ni GPU.

## Contraste medido

El test calcula la luminancia relativa WCAG desde los valores hexadecimales del CSS. Los mínimos
observados por tema son:

| Categoría | Claro | Oscuro | Umbral |
| --- | --- | --- | --- |
| Texto sobre fondo | 6.31:1 | 8.30:1 | 4.5:1 |
| Foco / borde sobre superficie | 3.82:1 | 5.79:1 | 3:1 |
| Fondo del visor frente a pieza `#d9d9d9` | 7.74:1 | 7.74:1 | 3:1 |

La tabla completa de 17 pares por tema está en `docs/diseno-v2.md`.

## Validación Python

Entorno temporal creado con `uv` y
`--no-install-package python-solvespace --no-install-package llama-cpp-python`, porque en Windows
esos sdists requieren MSVC/`nmake`. `M2_DOWNLOAD_SECRET` usado solo con valor ficticio.

| Comando | Resultado |
| --- | --- |
| `bash scripts/vendor-constraint-kit.sh` | `OK: constraint-kit vendoreado y parchado (rev 2ed27db)` |
| `uv run --no-sync ruff check ...` | `All checks passed!` |
| `uv run --no-sync python scripts/generate_api_types.py --check` | `Tipos OpenAPI actualizados.` |
| `uv run --no-sync pytest -q` | `4 failed, 414 passed, 26 warnings in 62.81s` |
| `uv run --no-sync pytest -q --deselect ...` (4 casos) | `414 passed, 4 deselected, 26 warnings in 37.46s` |
| `git diff --check` | Sin errores de whitespace |
| Pre-commit sobre los archivos de HU-34 | Todos los hooks aplicables en verde |

Los cuatro fallos de la ejecución completa son ajenos al cambio y dependientes del entorno local
Windows/carga de este equipo:

1. `tests/test_hu30_registro.py::test_ac1_80_solicitudes_simultaneas_sin_perdidas`:
   `OSError: [Errno 36] Resource deadlock avoided` en `msvcrt.locking` bajo concurrencia.
2. `tests/test_hu30_retencion.py::test_ac4_no_sigue_enlaces_simbolicos`:
   `OSError: [WinError 1314] El cliente no dispone de un privilegio requerido` al crear symlink.
3. `tests/test_hu30_retencion.py::test_ac4_no_borra_directorio_con_enlace_interno`: mismo WinError 1314.
4. `tests/test_seguimiento.py::test_sobrecarga_del_seguimiento_local_es_menor_a_50_ms`:
   `p95=145.3 ms` frente al umbral de 50 ms por carga local de MLflow.

No se ejecutó `make check` literalmente en Windows por los sdists nativos citados; se ejecutaron
sus componentes equivalentes. CI ejecutará el `make check` completo en Linux.
