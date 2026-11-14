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
| **Estado** | En construcción 🚧 — HU-01, 03, 04, 06, 08, 09 y 14 implementadas; HU-16 (seguimiento MLflow) implementada en `feature/hu-16-mlflow`; 05, 07, 10–13 y 15 pendientes |

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
- Pipeline: solicitud en español → generación DSL (DeepSeek por API, HU-14,
  sin traducción) → verificación geométrica determinista → construcción B-rep →
  entrega STEP/GLB/CSV.
- API REST (`POST /generar`, `GET /health`), progreso SSE, consulta/cancelación
  en `/generaciones/{id}` y Vue 3 con resultados descargables (HU-15).
- Registro trazable de solicitudes (texto, resultado, latencia, error, versión)
  con exclusión de datos personales (Ley 1581 de 2012).
- Línea base heredada Gemma/llama.cpp solo con overlay explícito.

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
| **UI** | Vue 3 Composition API + TypeScript + Vite, Node 24, npm lockfile |
| **Kernel CAD** | `constraint-kit` (vendoreado en `vendor/`) con CadQuery 2.7.0, build123d 0.10.0, bd_warehouse 0.2.0, Z3, python-solvespace, OpenCascade (LGPL 2.1) |
| **LLM** | DeepSeek `deepseek-v4-pro` por API (`https://api.deepseek.com`), requiere `DEEPSEEK_API_KEY` (HU-14) |
| **LLM heredado** | `gemma-4-12b-constraintkit` GGUF Q6_K (~9,8 GB) por llama.cpp (`:8080`, CUDA); solo línea base HU-01 (`docker-compose.gemma.yml`) |
| **Seguimiento** | [MLflow](https://mlflow.org/) 3.18 (`mlflow-skinny`): experimentos `m2-cad-generacion` y `m2-cad-banco`; servidor con backend SQLite (`mlflow.db`) y artefactos en volumen, UI en `127.0.0.1:5000` sin autenticación (HU-16) |
| **Testing** | `pytest` + cobertura **≥ 70 %** de `src/m2_cad` (umbral en `pyproject.toml`) |
| **Lint / Formato** | [Ruff](https://docs.astral.sh/ruff/) — reglas `E, F, I, B`, `line-length = 100` |
| **Pre-commit** | Ruff + higiene de archivos + bloqueo de pesos (`.gguf`, `.safetensors`, …) |
| **CI/CD** | GitHub Actions (`.github/workflows/ci.yml`) en PRs y pushes a `develop` |
| **Dependencias automáticas** | [Dependabot](.github/dependabot.yml) (target `develop`) |
| **Despliegue** | Docker multietapa Node/vendor/Python; Compose: `mlflow` (`:5000`) + `m2-cad` (Vue + FastAPI `:8000`), DeepSeek externo |

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
│   ├── pipeline.py             # orquesta solicitud→DSL→verificación→B-rep (HU-04)
│   ├── banco.py                # banco de 40 solicitudes contra el modelo (HU-14)
│   ├── evaluacion.py           # evaluador HTTP HU-07: reporte por familia y enlaces CSV/STEP
│   ├── registro.py             # registro CSV con exclusión de PII (HU-06)
│   ├── trabajos.py             # SSE, registro en memoria y cancelación cooperativa
│   ├── control.py              # puntos seguros de cancelación del pipeline (HU-15)
│   ├── seguimiento.py          # MLflow: una corrida por solicitud y por caso del banco (HU-16)
│   └── web.py                  # Vue/estáticos, CORS restringido y errores JSON
├── frontend/                   # Vue, TypeScript, Vite y pruebas Vitest
├── design/                     # referencia y fuente única de tokens (tokens.css)
├── tests/                      # pytest: dataset, banco, pipeline, API, registro, seguimiento, SSE, web
├── data/
│   ├── test_cases.csv          # banco de 40 solicitudes
│   └── registro.csv            # registro de solicitudes (ignorado en git)
├── outputs/                    # entregables por solicitud (uuid/; ignorado en git)
├── mlruns/ · mlflow.db         # seguimiento local de MLflow (ignorados en git)
├── specs/                      # especificaciones Spec Kit (001–009): spec, plan, tasks
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
└── docker-compose.yml          # mlflow + m2-cad (Vue/FastAPI) + DeepSeek externo (sin GPU)
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
| Frontend | Vitest, TypeScript y build | `make frontend-check` |
| Servicio | Vue/FastAPI + DeepSeek externo | `make up` / `make down` |

`make check` ejecuta Ruff, Vitest, TypeScript, build y pytest con cobertura;
CI reproduce estos controles desde lockfiles. Las pruebas con dobles se
identifican como simuladas y no prueban inferencia real.

FastAPI sirve HTML/assets, JSON, SSE y archivos desde un mismo origen; las rutas
API desconocidas devuelven JSON, nunca el índice Vue. CORS admite solo orígenes
HTTP(S) exactos. Las claves y URLs del modelo permanecen en el backend. Un único
worker mantiene hasta 128 trabajos en memoria, sin persistencia tras reinicio.
La cancelación es cooperativa entre operaciones bloqueantes: DELETE 202 no
confirma detención; `cancelado` confirma solo la salida local segura, nunca la
detención de un proveedor remoto. No hay rollback garantizado de archivos.

La recuperación HU-07 añade trazabilidad persistente sin cambiar el cuerpo
JSON de `/generar`: la cabecera `X-Request-ID` admite un UUID para ese transporte; `X-Registro-ID` y
`X-Registro-URL` enlazan la única fila CSV; `X-Step-URL` enlaza el STEP cuando
se declara. `/registros/{id}` y `/registros/{id}/step` permiten consultar esas
salidas fuera del registro temporal de trabajos, limitando STEP a `outputs/`.
JSON comparte ID entre CSV y MLflow; SSE conserva el ID de trabajo para ambos.
Se conserva DeepSeek en español y `no aplica` en traducción. El evaluador HTTP
genera reportes en `docs/hu07/`, sin sustituir el runner `banco` ni sus referencias.
La corrida real única HU-07 dejó 30/30 conformes y 10/10 declinaciones correctas,
sin errores silenciosos; conserva 40 registros/MLflow y 30 STEP con hashes del
banco y código evaluado. La revisión de aceptación sigue pendiente;
ver `docs/hu07/README.md` para el reporte y sus límites.
`make bench-report` expone la evaluación HTTP de 40 casos sin alterar `make bench`.
Según SPEC-016 RNF-2 se versiona solo la evidencia Markdown; registros JSON/CSV,
STEP y código archivado permanecen locales con hashes consignados en el reporte.
Volumen/caja conformes no garantizan equivalencia completa de forma; queda
pendiente la revisión humana de geometría y aceptación de la historia.
`scripts/smoke_hu07.py` prepara un único positivo HU02-P01 por HTTP, sin cambiar
el banco ni el prompt: conserva registro/STEP/métricas y enlaza la corrida
MLflow existente por `solicitud_id`, sin una segunda corrida de seguimiento.
Ejecutarlo realiza una llamada al proveedor; sus pruebas son simuladas.
El servidor MLflow admite explícitamente los hosts `mlflow:5000`,
`127.0.0.1:5000` y `localhost:5000`: sin el host interno, MLflow 3.18 puede
rechazar con 403 al cliente de la API aunque `/health` responda correctamente.

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
| 2026-11-13 | Integrar HU-14: DeepSeek recibe español directamente, sin Gemini/traducción; registro `no aplica` | Conservar el contrato actual del modelo al añadir SSE |
| 2026-11-13 | HU-15/#39 sustituye Gradio por Vue; FastAPI sirve el build y SSE con cancelación cooperativa | Un solo origen y servicio web, sin progreso ficticio ni confirmación remota inventada |
| 2026-11-13 | Validación Docker aislada y smoke con modelo simulado, geometría/exportación reales | Evidencia reproducible sin servicios de pago; ver `docs/hu15-integracion-hu14.md` |
| 2026-11-13 | Seguimiento de experimentos con MLflow (`seguimiento.py`, servicio `mlflow`, `make mlflow`); versión de modelo registrada y fin de `version="desconocida"` (HU-16) | Comparar DeepSeek contra la línea base Gemma sin revisar casos a mano y ligar cada evidencia al modelo que la produjo; el seguimiento es best-effort y nunca bloquea la respuesta |
| 2026-11-14 | Integrar HU-16 en HU-15: el control de cancelación pasa a `control.py` y `seguimiento.py` queda para MLflow; la ruta SSE abre y cierra su corrida en el hilo del trabajo | Evitar el choque de nombres entre ambas HU y medir también las solicitudes SSE; MLflow guarda la corrida activa por hilo |

## 10. Notas y tareas pendientes

- [x] Crear `CONSTITUTION.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, plantillas de PR/issues, `.editorconfig`.
- [ ] Proteger `develop` (CI verde + 1 aprobación) y `main` en GitHub.
- [x] HU-16 (seguimiento con MLflow, responsable Luis Meza) implementada en
  `specs/009-hu-16-mlflow/`.
- [x] Sustituir el marcador `version="desconocida"` del registro por la versión real del modelo servido.
- [ ] HU-05, 07, 10–13 y 15 pendientes (ver `specs/`).
- [x] Inyectar la configuración del modelo en el contenedor `m2-cad` (`DEEPSEEK_API_KEY`, `LLM_MODEL`; HU-14).
- [ ] Mantener la cobertura ≥ 70 % al añadir módulos.
- [ ] Regenerar el diagrama de arquitectura (`docs/arquitectura.*`) con Archify: todavía muestra la API Gemini y llama.cpp (HU-14).

## 11. Configuración local (no trackear)

> Configuración específica de cada máquina. **NO incluir en commits.**

Cada colaborador fija su identidad en su entorno:

```bash
git config --global user.name  "Tu Nombre"
git config --global user.email "tu-correo@example.com"
```

Si usas una llave SSH dedicada para GitHub, declárala en `~/.ssh/config` con
`IdentitiesOnly yes` (guía completa en `jan-project-standard` →
`references/git-identity.md`). Los secretos (`DEEPSEEK_API_KEY`, claves de nube)
viven en `.env` (gitignored); copia el ejemplo versionado
[`.env.example`](./.env.example) y completa los valores.

## 12. Licencias

Código propio: **MIT**. Terceros: modelo y motor (Gemma, constraint-kit,
CadQuery, build123d, Z3) **Apache 2.0 / MIT**; OpenCascade **LGPL 2.1**;
python-solvespace **GPL-3.0** (obliga solo al distribuir). Ver README §Licencias.
