# Plan de implementación · HU-55 (SPEC-056)

## Decisión de arquitectura

Los releases se cortan desde `main` cuando un push a esa rama supera los jobs `test` y
`e2e` de CI, cumpliendo la decisión ya tomada en SPEC-058 (HU-57). No se reactiva
`develop` ni se publica desde forks o pull requests.

La lógica determinista vive en `src/m2_cad/releases.py` (biblioteca estándar) y se expone
por `scripts/generar_release.py`:

- Analiza Conventional Commits desde la última etiqueta `v*`.
- `feat` → versión menor, `fix`/`perf` → parche, `BREAKING CHANGE` o `!:` → mayor.
- Un cambio incompatible del contrato `/v1` (`contracts/openapi-v1.json` o los tipos
  generados) fuerza versión mayor y destaca el aviso en las notas (SPEC-032).
- Genera o actualiza `CHANGELOG.md` agrupado por tipo de commit.
- Sincroniza `pyproject.toml` con la etiqueta publicada.
- Modo `--dry-run` por defecto: imprime la propuesta y no escribe archivos, crea etiquetas
  ni publica releases. `--verificar` comprueba la coherencia en CI; `--preparar` escribe
  changelog y versión para el job automático; `--titulo` valida el título de la PR antes
  de fusionar (RNF-3).

El workflow `release` se añade a `.github/workflows/ci.yml` con `needs: [test, e2e]`,
disparador limitado a `push` en `main`, `contents: write` sólo en ese job y `gh release
create` con las notas generadas. La validación de esta HU se hace en seco: no se ejecuta
el job real ni se crea ninguna etiqueta.

## Componentes

| Archivo | Responsabilidad |
| --- | --- |
| `src/m2_cad/releases.py` | Parseo de commits, cálculo semántico, render del changelog y coherencia de versión. |
| `scripts/generar_release.py` | CLI `--dry-run`, `--verificar`, `--preparar`, `--titulo` y `--version`. |
| `tests/test_releases_automaticos.py` | AC1, AC2, AC3, agrupación del changelog y rechazo de títulos no convencionales. |
| `.github/workflows/ci.yml` | Validación del título de PR y job `release` posterior a `test`/`e2e`. |
| `CHANGELOG.md` | Historial generado, empezando por `v1.0.1`. |
| `Makefile` | `release-dry-run`, `release-check`, `release-version`. |
| `README.md`, `CONSTITUTION.md`, `specs/README.md` | Documentación del flujo y decisión. |

## Compatibilidad y seguridad

- Sin dependencias nuevas: Python 3.12, `subprocess`, `re`, `datetime` y `pathlib`.
- Sin red, API key ni GPU en pruebas ni en modo seco (RNF-2).
- Los commits de merge y los mensajes no convencionales no alteran el cálculo; el título
  de cada PR se valida aparte.
- La etiqueta publicada es inmutable: `--preparar` nunca reescribe una entrada ya
  publicada del changelog, sólo inserta la nueva.
- La publicación real sigue sujeta a la protección de `main`; el token del workflow debe
  poder actualizar `CHANGELOG.md` y `pyproject.toml` antes de crear la etiqueta.

## Verificación

1. `make release-dry-run` sobre el historial real: propuesta, notas y sin etiquetas nuevas.
2. `make release-check`: versión de `pyproject.toml`, etiqueta alcanzable y sección del
   changelog coherentes.
3. `make check`, pre-commit y auditoría `jan-project-standard`.
