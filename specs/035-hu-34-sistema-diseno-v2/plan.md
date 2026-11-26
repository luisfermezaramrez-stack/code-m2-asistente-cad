# Plan · SPEC-035 / HU-34

## Decisión de arquitectura

Los tokens pasan a `frontend/src/design/tokens.css`: único archivo de paleta, importado una sola
vez desde `frontend/src/main.ts`. Los valores de tema claro y oscuro viven en el mismo archivo;
los componentes siguen consumiendo `var(--...)` y no conocen la preferencia del usuario.

La preferencia se resuelve en `frontend/src/design/theme.ts`: `localStorage` manda; si no hay
valor guardado, se usa `matchMedia('(prefers-color-scheme: dark)')`. El módulo aplica
`data-theme` a `<html>` y reacciona a cambios del sistema solo mientras no exista elección
explícita. La selección visible es un único botón en la cabecera, sin navegación ni ajustes.

`docs/diseno-v2.md` documenta tokens, escala tipográfica, precedencia de temas y pares de
contraste. `design/` queda como referencia histórica de HU-15; ya no es fuente importada.

## Alcance

- RF-1: mover los 63 tokens al paquete frontend sin renombrarlos; eliminar la copia del build
  Docker que solo existía por el import externo.
- RF-2: documentar `--text-small` / `--text-body` / `--text-heading` / `--text-title`, sus
  proporciones (0.875 / 1 / 1.25 / 1.75 rem), interlineados y usos.
- RF-3: tema oscuro por `prefers-color-scheme` y preferencia explícita persistida que gana al
  sistema; el selector usa los tokens existentes.
- RF-4: verificar por código los pares texto/fondo y foco/fondo en ambos temas (AA ≥ 4.5:1 y
  ≥ 3:1), más el fondo del visor frente a `#d9d9d9`.
- RF-5: documentación del sistema y actualización de README, frontend y constitución.

## No incluido

- Rediseño visual, app shell/navegación (SPEC-039), WCAG fuera de contraste (SPEC-041),
  historial (SPEC-038) ni fuentes remotas.

## Verificación

1. `npm --prefix frontend ci`
2. `npm --prefix frontend test`
3. `npm --prefix frontend run typecheck`
4. `npm --prefix frontend run build`
5. `uv run --no-sync ruff check src tests scripts/verify_hu15_deployment.py scripts/generate_api_types.py`
6. `uv run --no-sync pytest -q` con `M2_DOWNLOAD_SECRET` ficticio y `frontend/dist` compilado.
7. `git diff --check` y pre-commit sobre los archivos del cambio.

La evidencia se registra en `specs/Evidence.md`.
