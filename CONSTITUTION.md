# CONSTITUTION — M2 Asistente CAD

> **Verdad central del proyecto.** Este documento define el propósito, el stack, la
> estructura, las convenciones y el flujo de trabajo de `M2 Asistente CAD`. Si algo aquí
> contradice al código, el código manda **y este archivo se actualiza**.

> ⚠️ **Directiva de mantenimiento:** cada vez que se realicen cambios significativos
> (nuevas funcionalidades, cambios arquitectónicos, adición de clases/módulos o ajustes
> de tecnologías), **se debe actualizar este archivo en el mismo commit** para mantener
> la verdad central del proyecto bien documentada.

---

## 0. Identidad del proyecto

| Campo | Valor |
|-------|-------|
| **Nombre** | M2 Asistente CAD |
| **Descripción** | Asistente CAD para el diseño preliminar de componentes metálicos auxiliares. |
| **Repositorio** | <https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad> |
| **Licencia** | MIT (código propio); ver §12 para terceros |
| **Rama de integración** | `develop` (toda rama de trabajo sale de aquí y vuelve por PR) |
| **Rama de entregas** | `main` (solo recibe entregas) |
| **Estado** | En construcción 🚧 — HU-01, 03, 04, 06, 08 y 09 implementadas; 05 y 11 pendientes |

## 1. Propósito y no-propósito

### Propósito

Convertir la descripción **en español** de un componente metálico auxiliar en un
modelo CAD **preliminar verificado** (STEP, GLB y lista de materiales en CSV) en
minutos — o **declinar con un motivo** cuando la pieza no se puede construir — sin
que el usuario tenga que redactar prompts en inglés ni usar la consola.

### No-propósito

- No es una herramienta de cálculo estructural ni de verificación normativa
  (NSR-10, RETIE): toda salida es **preliminar** y exige revisión de un profesional
  responsable.
- No reemplaza un CAD comercial ni busca competir con Revit/BIM.
- No reentrena modelos ni sirve como plataforma de fine-tuning.
- No es un servicio multiusuario: sin autenticación, sin concurrencia garantizada.

## 2. Alcance

### Dentro del alcance

- Catálogo cerrado de 8 familias: `plate`, `sheet_bracket`, `adapter`, `flange`,
  `spacer`, `tornillería`, `extrusion` y `pipe`.
- Pipeline: traducción ES→EN → generación DSL (Gemma 4 12B ConstraintKit vía
  llama.cpp) → verificación geométrica determinista → construcción B-rep →
  entrega STEP/GLB/CSV.
- API REST (`POST /generar`, `GET /health`) y UI web (Gradio) con resultados
  descargables.
- Registro trazable de solicitudes (texto, resultado, latencia, error, versión)
  con exclusión de datos personales (Ley 1581 de 2012).
- Plan B documentado: DeepSeek por API.

### Fuera del alcance (por ahora)

- Entrada por imagen o voz; ensamblajes multi-pieza complejos.
- Cálculo de resistencia, fatiga o cumplimiento normativo.
- Reentrenamiento del modelo; despliegue multi-tenant; autenticación.

## 3. Stack técnico

| Categoría | Tecnología |
|-----------|------------|
| **Lenguaje** | Python **3.12** (fijado en `.python-version`, contenedor `python:3.12-slim`) |
| **Gestor de paquetes y entorno** | [`uv`](https://docs.astral.sh/uv/) — prohibido `pip` y `requirements.txt` |
| **Build backend** | `hatchling` (wheel desde `src/m2_cad`) |
| **API** | [FastAPI](https://fastapi.tiangolo.com/) + `uvicorn` |
| **UI** | [Gradio](https://www.gradio.app/) ≥ 4, < 7 |
| **Kernel CAD** | `constraint-kit` (vendoreado en `vendor/`) con CadQuery 2.7.0, build123d 0.10.0, bd_warehouse 0.2.0, Z3, python-solvespace, OpenCascade (LGPL 2.1) |
| **LLM local** | `gemma-4-12b-constraintkit` GGUF Q6_K (~9,8 GB) servido por llama.cpp (`:8080`, CUDA) |
| **Traducción ES→EN** | API Gemini (`gemini-3.5-flash-lite`), requiere `GEMINI_API_KEY` |
| **Testing** | `pytest` + cobertura **≥ 70 %** de `src/m2_cad` (umbral en `pyproject.toml`) |
| **Lint / Formato** | [Ruff](https://docs.astral.sh/ruff/) — reglas `E, F, I, B`, `line-length = 100` |
| **Pre-commit** | Ruff + higiene de archivos + bloqueo de pesos (`.gguf`, `.safetensors`, …) |
| **CI/CD** | GitHub Actions (`.github/workflows/ci.yml`) en PRs y pushes a `develop` |
| **Dependencias automáticas** | [Dependabot](.github/dependabot.yml) (target `develop`) |
| **Despliegue** | Docker Compose: `llama` + `m2-cad` (FastAPI `:8000`) + `m2-cad-ui` (Gradio `:7860`) |

> ⚠️ **Regla dura:** toda gestión de dependencias y entornos pasa por `uv`.
> Dependencias nuevas con `uv add` / `uv add --dev`; `uv.lock` se versiona.

### Desviaciones documentadas del estándar `jan-project-standard`

| Desviación | Justificación |
|------------|---------------|
| Python 3.12 (no 3.13) | El contenedor `cadkit` del autor de constraint-kit y `python-solvespace` (sdist compilado en C17) fijan 3.12; `.python-version` es la única fuente de verdad para local, Docker y CI. |
| Build backend `hatchling` (no `uv_build`) | El source local `vendor/constraint-kit` en `[tool.uv.sources]` y el wheel de `src/m2_cad` ya operan con hatchling sin fricción; el cambio de backend no aporta valor aquí. |

## 4. Estructura del repositorio

```text
code-m2-asistente-cad/
├── src/m2_cad/                 # paquete propio (src-layout)
│   ├── api.py                  # FastAPI: POST /generar, GET /health (HU-06)
│   ├── pipeline.py             # orquesta traducción→DSL→verificación→B-rep (HU-04)
│   ├── traduccion.py           # ES→EN con protección de cantidades (HU-03)
│   ├── registro.py             # registro CSV con exclusión de PII (HU-06)
│   └── interfaz.py             # UI Gradio: texto → descargas (HU-08)
├── tests/                      # pytest: dataset, translate, pipeline, api, registro, interfaz
├── data/
│   ├── test_cases.csv          # banco de 40 solicitudes
│   └── registro.csv            # registro de solicitudes (ignorado en git)
├── outputs/                    # entregables por solicitud (uuid/; ignorado en git)
├── specs/                      # especificaciones Spec Kit (001–007): spec, plan, tasks
├── scripts/                    # fetch-model, verify-serve, vendor, cloud (Lambda/Vast.ai)
├── docs/                       # documentación y diagrama de arquitectura
├── vendor/                     # constraint-kit (gitignored; restaurar con `make vendor`)
├── .github/                    # CI, labels, Dependabot, plantillas de PR e issues
├── .opencode/rules/            # reglas para agentes (tgrep)
├── AGENTS.md                   # contexto para agentes LLM
├── CONSTITUTION.md             # este archivo — verdad central
├── README.md                   # puerta de entrada pública
├── CONTRIBUTING.md             # guía de contribución
├── CODE_OF_CONDUCT.md          # código de conducta
├── Makefile                    # interfaz de comandos (`make help`)
├── pyproject.toml              # metadatos y dependencias (uv)
├── uv.lock                     # lockfile determinista (versionado)
├── .python-version             # versión de Python fijada (3.12)
├── .editorconfig               # convenciones de estilo entre editores
├── .pre-commit-config.yaml     # hooks de calidad
├── Dockerfile                  # imagen base python:3.12-slim + uv
└── docker-compose.yml          # llama + m2-cad + m2-cad-ui
```

## 5. Convenciones de código

- **Estilo:** [PEP 8](https://peps.python.org/pep-0008/) y
  [PEP 257](https://peps.python.org/pep-0257/), impuesto por **Ruff**
  (`line-length = 100`, reglas `E, F, I, B`).
- **Tipado:** anotaciones en funciones y firmas públicas; imports agrupados
  (ruff `I`).
- **Nomenclatura:** `snake_case` (funciones/variables), `PascalCase` (clases),
  `UPPER_CASE` (constantes de módulo).
- **Docstrings:** en español, en módulos, clases y funciones públicas; cada módulo
  cita su especificación (`specs/XXX-.../spec.md`) y sus AC cuando aplica.
- **Pruebas:** `pytest` con el patrón **AAA** (*Arrange · Act · Assert*); tests de
  integración no requieren GPU ni red (el pipeline se inyecta por `Callable`).
- **Idioma:** UI, mensajes de error para el usuario, comentarios y commits en
  español; identificadores de código en inglés.
- **Reglas propias del dominio:**
  - Toda respuesta de éxito **declara que la salida es preliminar**; nunca se
    presenta como apta para fabricación.
  - Ante una pieza fuera del catálogo, el sistema **declina con motivo** —
    prohibido inventar geometría sustituta.
  - El registro excluye correos y nombres declarados (Ley 1581 de 2012);
    campos sin valor conocen un marcador explícito (`ninguno`, `desconocida`),
    nunca vacíos.
  - Los pesos del modelo (`.gguf`, `.safetensors`, …) **nunca se versionan**;
    `vendor/` está gitignored y se restaura con `make vendor`.
  - Cada solicitud escribe sus entregables en `outputs/<uuid>/`, sin colisiones.

## 6. Calidad y automatización

| Herramienta | Rol | Comando |
|-------------|-----|---------|
| `uv` | Entornos y dependencias | `make install` (`uv sync --dev`) |
| Ruff | Lint + formato | `make lint` / `make format` |
| `pytest` | Pruebas | `make test` |
| Cobertura | Umbral ≥ 70 % de `src/m2_cad` | `make cov` (falla si baja) |
| `pre-commit` | Hooks antes de cada commit | `make precommit-install` / `make precommit` |
| GitHub Actions | CI en PRs a `develop` | `.github/workflows/ci.yml` |
| Kernel del autor | 113 pruebas dentro del contenedor `cadkit:0.1` | `make kernel-image` + `make kernel-test` |
| Servicio | llama.cpp + FastAPI + Gradio | `make up` / `make down` |

- Ningún commit se salta los hooks (`--no-verify` prohibido salvo causa
  justificada y documentada).
- La **CI debe estar en verde** y con una aprobación antes de fusionar un PR a
  `develop` (protección de rama).
- `vendor/constraint-kit` debe existir antes de `uv sync` (source local en
  `[tool.uv.sources]`): en un checkout limpio, correr `make vendor` primero; la CI
  lo hace automáticamente cuando el pyproject declara ese source.
- **macOS Intel:** `uv sync` / `make check` no concluyen localmente (`nlopt`
  no publica wheel para macOS `x86_64`); la verificación completa se corre en el
  contenedor Docker o en la CI.

## 7. Repositorio y Git

- **Remoto:** `git@github.com:luisfermezaramrez-stack/code-m2-asistente-cad.git`
  (HTTPS también válido; preferir SSH).
- **Estrategia:** `develop` es la rama de integración; **toda rama de trabajo sale
  de `develop`** y vuelve por pull request. `main` solo recibe entregas.
- **Nombres de rama:** `feature/hu-XX-tema` (una rama por historia de usuario);
  utilidades con `fix/...`, `docs/...`, `chore/...`.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat:`, `fix:`, `docs:`, `refactor:`, `style:`, `test:`, `chore:` (con ámbito
  `hu-XX` cuando aplica; descripciones en imperativo, un solo idioma).
- **Identidad git:** cada colaborador configura nombre y correo localmente
  (`git config user.name / user.email`); no se comparte configuración por repo.

## 8. Flujo diario (commit + push)

```bash
# 1. Ver cambios
git status

# 2. Verificación completa (lint + pruebas + cobertura)
make check

# 3. Agregar y commitear (los hooks de pre-commit se ejecutan solos)
git add -A
git commit -m "tipo(hu-XX): mensaje descriptivo"

# 4. Subir y abrir PR a develop
git push -u origin feature/hu-XX-tema
```

## 9. Historial de decisiones técnicas

| Fecha | Decisión | Motivo |
|-------|----------|--------|
| 2026-11-03 | Instalar constraint-kit por git y generar `uv.lock` | Reproducibilidad del kernel CAD desde el primer commit |
| 2026-11-04 | **Vendorear** constraint-kit en `vendor/` (gitignored) y construirlo desde el path local | Parchear sin tocar el repo del autor; `make vendor` lo restaura |
| 2026-11-04 | Validar HU-01 en GPU remota (Lambda A10 24 GB) | La GPU local de 4 GB no soporta el GGUF Q6_K de ~9,8 GB |
| 2026-11-09 | CI con cobertura ≥ 70 % y pre-commit bloqueante (HU-09) | Calidad verificada en cada PR a `develop` |
| 2026-11-09 | Dependabot ignora `build123d`/`cadquery`/`bd-warehouse` | Kernel CAD fijado al vendor `cadkit:0.1`; su upgrade es coordinado |
| 2026-11-09 | Registro de solicitudes con exclusión de PII | Ley 1581 de 2012 (AC4 de HU-06) |
| 2026-11-09 | Traducción ES→EN con Gemini + protección de cantidades | Traducción técnica sin alterar medidas (HU-03) |
| 2026-11-10 | Pipeline verificado: DSL → dsl.check → STEP/GLB/CSV (HU-04) | Verificación geométrica determinista antes de entregar |
| 2026-11-10 | Importación diferida del kernel CAD en la API | Cargar CadQuery/OCP solo al generar (arranque ligero) |
| 2026-11-11 | UI Gradio que consume la API (HU-08) | Usuarios sin consola; `archivo_seguro` limita descargas a `outputs/` |
| 2026-11-12 | Adoptar `CONSTITUTION.md` como fuente única de verdad y completar la gobernanza (CONTRIBUTING, CoC, plantillas, `.editorconfig`, `AGENTS.md`, `docs/`) | Estándar `jan-project-standard`: documento vivo y PR verificables |
| 2026-11-12 | Diagrama de arquitectura con Archify en `docs/arquitectura.html` (fuente `docs/arquitectura.json`) | Documentación viva del runtime enlazada desde el README |
| 2026-11-12 | Excluir `.agents/` (skills vendoreados) de pre-commit y `docs/arquitectura.html` de `trailing-whitespace` | Son terceros/plantillas con marcadores `{{...}}` y un artefacto generado: la higiene la da su fuente |
| 2026-11-12 | Añadir `.env.example` y documentar las variables de entorno en el README | Configuración reproducible sin versionar secretos |

## 10. Notas y tareas pendientes

- [x] Crear `CONSTITUTION.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, plantillas de PR/issues, `.editorconfig`.
- [ ] Proteger `develop` (CI verde + 1 aprobación) y `main` en GitHub.
- [ ] HU-05 y HU-11 pendientes (ver `specs/`).
- [ ] Sustituir el marcador `version="desconocida"` del registro por la versión real del modelo servido.
- [ ] Inyectar `GEMINI_API_KEY` en el contenedor `m2-cad` (`env_file` en compose) para que la traducción funcione en Docker.
- [ ] Mantener la cobertura ≥ 70 % al añadir módulos.
- [ ] Evaluar el plan B (DeepSeek por API) cuando no haya GPU disponible.

## 11. Configuración local (no trackear)

> Configuración específica de cada máquina. **NO incluir en commits.**

Cada colaborador fija su identidad en su entorno:

```bash
git config --global user.name  "Tu Nombre"
git config --global user.email "tu-correo@example.com"
```

Si usas una llave SSH dedicada para GitHub, declárala en `~/.ssh/config` con
`IdentitiesOnly yes` (guía completa en `jan-project-standard` →
`references/git-identity.md`). Los secretos (`GEMINI_API_KEY`, claves de nube)
viven en `.env` (gitignored); copia el ejemplo versionado
[`.env.example`](./.env.example) y completa los valores.

## 12. Licencias

Código propio: **MIT**. Terceros: modelo y motor (Gemma, constraint-kit,
CadQuery, build123d, Z3) **Apache 2.0 / MIT**; OpenCascade **LGPL 2.1**;
python-solvespace **GPL-3.0** (obliga solo al distribuir). Ver README §Licencias.
