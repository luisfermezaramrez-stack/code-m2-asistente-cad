# 🤝 Guía de contribución

¡Gracias por tu interés en contribuir a **M2 Asistente CAD**!

La documentación central del proyecto vive en [`CONSTITUTION.md`](./CONSTITUTION.md).

> 📘 **Antes de tu primera contribución**, lee [`CONSTITUTION.md`](./CONSTITUTION.md)
> (stack, decisiones y convenciones) y el [Código de conducta](./CODE_OF_CONDUCT.md).

---

## 📑 Tabla de contenidos

- [Requisitos previos](#-requisitos-previos)
- [Configuración del entorno](#-configuración-del-entorno)
- [Flujo de trabajo con Git](#-flujo-de-trabajo-con-git)
- [Estándares de código](#-estándares-de-código)
- [Mensajes de commit](#-mensajes-de-commit)
- [Pull Requests](#-pull-requests)
- [Reportar issues](#-reportar-issues)
- [Regla de oro: mantener la constitución](#-regla-de-oro-mantener-la-constitución)

---

## ✅ Requisitos previos

| Herramienta | Versión | Notas |
|-------------|---------|-------|
| [Python](https://www.python.org/downloads/) | 3.12 | Fijada en `.python-version` (local, Docker y CI) |
| [`uv`](https://docs.astral.sh/uv/getting-started/installation/) | Última estable | Gestor de paquetes y entornos |
| [Git](https://git-scm.com/) | Última estable | Control de versiones |
| [GitHub CLI](https://cli.github.com/) | Opcional | Facilita issues y PRs |
| [Docker](https://www.docker.com/) | Con NVIDIA Container Toolkit | Solo para despliegue y `make kernel-test` |

> ⚠️ **Regla del proyecto:** está **prohibido** usar `pip` o `requirements.txt`.
> Toda gestión de dependencias pasa por `uv`.

## ⚙️ Configuración del entorno

```bash
git clone git@github.com:luisfermezaramrez-stack/code-m2-asistente-cad.git
cd code-m2-asistente-cad

make vendor              # restaura vendor/constraint-kit (gitignored) — requerido antes de uv sync
make install             # uv sync --dev
make precommit-install   # hooks de Ruff y bloqueo de pesos
make check
```

> 💡 Los secretos (`DEEPSEEK_API_KEY`, …) van en `.env` (gitignored); nunca en el
> código ni en el commit.

## 🌿 Flujo de trabajo con Git

La rama **`develop`** es la rama de integración: **toda rama de trabajo sale de
`develop`** y vuelve por pull request. `main` solo recibe entregas.

1. Actualiza `develop`:
   ```bash
   git switch develop && git pull
   ```
2. Crea una rama descriptiva (una por historia de usuario):
   ```bash
   git switch -c feature/hu-XX-tema
   ```
   | Prefijo | Uso |
   |---------|-----|
   | `feature/hu-XX-tema` | Nueva funcionalidad (historia de usuario) |
   | `fix/` | Corrección de bug |
   | `docs/` | Documentación |
   | `refactor/` | Refactorización |
   | `test/` | Pruebas |
   | `chore/` | Mantenimiento o configuración |
3. Desarrolla en commits pequeños y atómicos.
4. Abre un Pull Request hacia `develop`.

> 💡 **Regla de oro:** nunca hagas `push` directo a `develop` "para ver si
> funciona". Verifica localmente con `make check` antes de abrir el PR.

## 🧹 Estándares de código

- **Estilo:** [PEP 8](https://peps.python.org/pep-0008/) y [PEP 257](https://peps.python.org/pep-0257/).
- **Tipado:** anotaciones en funciones y firmas públicas.
- **Nomenclatura:** `snake_case`, `PascalCase` (clases), `UPPER_CASE` (constantes).
- **Pruebas:** `pytest` con patrón **AAA** (*Arrange · Act · Assert*); la cobertura
  de `src/m2_cad` no baja de **70 %** (umbral en `pyproject.toml`).
- **Lint y formato:** Ruff (reglas `E, F, I, B`).

```bash
make lint     # uv run ruff check src tests
make format   # uv run ruff format src tests
make test     # uv run pytest
make cov      # pytest + reporte de cobertura
```

> ❌ **Nunca** subas secretos (`.env`, tokens, llaves), datos pesados ni entornos
> virtuales. Respeta el [`.gitignore`](./.gitignore).

## 📝 Mensajes de commit

Se usa la especificación de [Conventional Commits](https://www.conventionalcommits.org/):

```text
<tipo>(<ámbito opcional>): <descripción breve en imperativo>
```

| Tipo | Uso |
|------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Documentación |
| `refactor` | Refactorización sin cambio de comportamiento |
| `style` | Formato, linting (sin cambio de lógica) |
| `test` | Pruebas |
| `chore` | Mantenimiento o configuración |

## 🔀 Pull Requests

1. Verifica que tu rama esté actualizada respecto a `develop`.
2. Abre el PR hacia `develop` y completa la plantilla oficial.
3. Usa un título con prefijo convencional y mantén el PR **acotado a un solo propósito**.
4. Marca los checklist aplicables (pruebas, lint, cobertura, `CONSTITUTION.md`, etc.).
5. La CI de `.github/workflows/ci.yml` debe estar en verde; `develop` exige CI verde
   **y una aprobación** antes de fusionar (protección de rama).

## 🐞 Reportar issues

Usa las plantillas disponibles en `.github/ISSUE_TEMPLATE/` (bug, funcionalidad, spike)
e incluye contexto, pasos para reproducir y evidencia cuando aplique.

## 🏛️ Regla de oro: mantener la constitución

> Cualquier cambio **arquitectónico, tecnológico o de proceso** debe reflejarse en
> [`CONSTITUTION.md`](./CONSTITUTION.md). El checklist del PR lo verifica de forma explícita.

---

## 📄 Licencia

Al contribuir, aceptas que tus aportes se distribuyan bajo la [Licencia MIT](./LICENSE).
