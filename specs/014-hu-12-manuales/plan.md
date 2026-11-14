# SPEC-014 · HU-12 — Plan de documentación

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #41). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-014
- **Historia**: #12
- **Responsable**: Carlos Eduardo Trujillo (backlog); PR #41 de `JuanC0319`
- **Rama**: `feature/hu-12-manuales-y-readme`
- **PR**: #41, fusionado 2026-11-13 (`7a28040`), 26 archivos
- **Estado**: Fusionada con brechas
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Diseño técnico

La documentación se organizó en capas en lugar de dos manuales separados:

| Capa | Archivo(s) del PR #41 | Rol |
|---|---|---|
| Fuente única de verdad | `CONSTITUTION.md` (+262) | Propósito, alcance, stack, estructura, convenciones, calidad, Git, historial de decisiones |
| Entrada del repositorio | `README.md` (+72 −6) | Badges, índice, arquitectura, estructura, requisitos, instalación, variables de entorno, contribución |
| Arquitectura | `docs/arquitectura.html` (+14900), `docs/arquitectura.json`, `docs/arquitectura.delivery.json`, `docs/arquitectura.browser-check.json` | Diagrama Archify de runtime y su fuente versionada |
| Índice de docs | `docs/README.md` | Convenciones de la carpeta `docs/` |
| Gobernanza | `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/*` | Flujo `develop`, plantillas |
| Agentes | `AGENTS.md`, `.opencode/rules/tgrep.md` | Contexto para asistentes LLM |
| Configuración | `.env.example`, `.editorconfig`, `.pre-commit-config.yaml`, `.gitignore` | Variables sin secretos, higiene |

También incluye higiene de fin de línea en archivos existentes y un cambio de formato
en `tests/test_api.py` (+1 −3, sin lógica).

## Decisiones

| Decisión | Porqué |
|---|---|
| `CONSTITUTION.md` como fuente única | Evita duplicar la verdad técnica entre README y manuales (cuerpo del PR #41). |
| Diagrama generado con Archify desde JSON | El HTML es artefacto generado; se regenera desde la fuente y se excluye de pre-commit. |
| `.env.example` con valores vacíos | Documenta la configuración sin versionar secretos. |
| Validación por CI | El autor no pudo completar `uv sync` en macOS Intel (`nlopt` sin wheel `x86_64`); la suite completa la ejecutó la CI del PR. |

## Contratos (estructura documental)

- `README.md` § Instalación y uso (en `7a28040`): `uv sync --dev`, `make check`,
  `make up`; alternativa `docker compose up --build`.
- `CONSTITUTION.md` §§ 0–12: identidad, propósito, alcance, stack, estructura,
  convenciones, calidad, Git, flujo diario, decisiones, pendientes, configuración
  local, licencias.
- `docs/README.md`: tabla de documentos y reglas (un documento, un tema; fechas ISO).

## Riesgos

- **Sin manual de usuario ni capturas** (AC1): el usuario final no tiene guía paso a
  paso de las 3 tareas.
- **Endpoints sin contrato documentado** (AC2): solo se nombran.
- **Paso `vendor` omitido** en el README del PR #41: en un checkout limpio `uv sync`
  depende de `vendor/constraint-kit`. Corregido en el README actual.
- **Desfase rápido**: el mismo día, HU-14, HU-15 y HU-16 cambiaron modelo, UI y
  despliegue; el README del PR #41 ya describía Gemma, Gemini y Gradio, hoy reemplazados.
- **AC4 sin medir**: no hay evidencia de una instalación cronometrada por un tercero.

## Alternativas descartadas

El PR #41 no documenta alternativas consideradas. No se añaden aquí.

## Estrategia de pruebas

Declarada en el PR #41 (no reejecutada para esta especificación):

- `ruff check src tests` y `pre-commit run --all-files` en verde.
- 30 pruebas sin kernel en local; la suite completa en la CI del PR.
- Validación de YAML/JSON de plantillas y de `docs/arquitectura.json`.
- `make up`: N/A según el PR.

Pendiente para cerrar AC4: una persona ajena sigue solo el README desde un checkout
limpio y se cronometra el tiempo hasta `GET /health` = 200.
