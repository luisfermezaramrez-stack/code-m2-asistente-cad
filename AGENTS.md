# AGENTS — M2 Asistente CAD

> Contexto del proyecto para sesiones con asistentes LLM (OpenCode, Antigravity,
> GitHub Copilot CLI, Claude Code, etc.). Trackeado al repositorio.

## Proyecto

Asistente CAD para el diseño preliminar de componentes metálicos auxiliares.
Pipeline: descripción en español → traducción (Gemini) → programa DSL (Gemma 4 12B
ConstraintKit vía llama.cpp) → verificación geométrica determinista → pieza B-rep
entregada como STEP, GLB y CSV — o declinación con motivo.

> 📘 La verdad técnica central —propósito, stack, estructura, convenciones, decisiones y
> flujo de trabajo— vive en [`CONSTITUTION.md`](./CONSTITUTION.md). **Léela antes de
> operar.** Ante cualquier cambio arquitectónico, tecnológico o de proceso, actualízala
> en el mismo commit.

---

## Flujo Diario (commit + push)

```bash
# 1. Ver cambios
git status

# 2. Verificación completa (lint + pruebas + cobertura ≥ 70 %)
make check

# 3. Agregar y commitear (los hooks de pre-commit se ejecutan solos)
git add -A
git commit -m "tipo(hu-XX): mensaje descriptivo"

# 4. Subir y abrir PR hacia develop (rama de integración)
git push -u origin feature/hu-XX-tema
```

**Convención de commits:** [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — nueva funcionalidad
- `fix:` — corrección de bug
- `docs:` — documentación
- `refactor:` — refactorización
- `style:` — formato, linting (sin cambio de lógica)
- `test:` — pruebas
- `chore:` — mantenimiento o configuración

---

## Comandos del proyecto (`make`)

```bash
make help              # lista todos los objetivos disponibles
make install           # uv sync --dev (dependencias)
make vendor            # clona/parchea constraint-kit (necesario antes de uv sync en checkout limpio)
make check             # lint + pytest (lo que corre la CI)
make cov               # pytest con cobertura (falla si < 70 %)
make precommit-install # instala los hooks de pre-commit
make up / make down    # levanta o detiene llama + FastAPI + Gradio con Docker
make model-fetch       # descarga y verifica el modelo GGUF (HU-01)
make kernel-test       # 113 pruebas del kernel dentro del contenedor del autor (AC3)
```

> ⚠️ **Regla dura:** toda gestión de dependencias y entornos pasa por `uv`. Está
> **prohibido** `pip` y `requirements.txt`. Los pesos del modelo (`.gguf`,
> `.safetensors`, …) nunca se versionan; `vendor/` está gitignored y se restaura
> con `make vendor`.

---

## Búsqueda de código: `tgrep`

Si [`tgrep`](https://github.com/microsoft/tgrep) está instalado, úsalo para búsquedas de
código en lugar de `grep` o `find` (índice de trigramas en `.tgrep/`, ignorado por Git):

```bash
tgrep -- "patrón" .            # búsqueda regex (usa -- antes del patrón)
tgrep -F -- "simbolo" .        # coincidencia literal
tgrep -t py -- "def " .        # filtrar por tipo de archivo
tgrep -g "src/**" -- "kw" .    # filtrar por ruta
tgrep -l -- "import torch" .   # listar archivos coincidentes
tgrep index .                  # (re)indexar
```

En OpenCode la preferencia se aplica automáticamente mediante la regla
[`.opencode/rules/tgrep.md`](./.opencode/rules/tgrep.md).

---

## Estructura y convenciones

- `src/m2_cad/` — paquete propio (src-layout): `api.py` (FastAPI), `pipeline.py`,
  `banco.py` (banco de solicitudes), `registro.py`, `interfaz.py` (Gradio).
- `tests/` — pruebas con `pytest` (patrón AAA); sin GPU ni red real.
- `specs/` — especificaciones Spec Kit (001–007); cada módulo cita su spec y AC.
- `docs/` — documentación y diagrama de arquitectura (Archify).
- `vendor/` — constraint-kit vendoreado (gitignored; `make vendor`).
- `CONSTITUTION.md` — fuente única de verdad.
- Estilo impuesto por **Ruff** (`line-length = 100`, reglas `E, F, I, B`).
- Idioma: UI, comentarios y commits en español; identificadores en inglés.
