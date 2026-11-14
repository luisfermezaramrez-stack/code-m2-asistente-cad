# m2-asistente-cad

[![CI](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](.python-version)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v1.json)](https://docs.astral.sh/ruff/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v1.json)](https://docs.astral.sh/uv/)
[![Cobertura mínima: 70 %](https://img.shields.io/badge/Cobertura-%E2%89%A5%2070%25-green.svg)](pyproject.toml)

Asistente CAD que convierte la descripción **en español** de un componente
metálico auxiliar en un modelo CAD **preliminar verificado** (STEP, GLB y lista
de materiales) en minutos — o que **declina con un motivo** cuando no puede
construirlo.

> ⚠️ **Toda salida es preliminar.** La verificación es solo geométrica; la
> resistencia y el cumplimiento de normas (NSR-10, RETIE) exigen revisión de un
> profesional responsable.

## Tabla de contenidos

- [Qué resuelve](#qué-resuelve)
- [Alcance](#alcance)
- [Arquitectura](#arquitectura)
- [Cómo funciona](#cómo-funciona)
- [Estructura](#estructura)
- [Requisitos](#requisitos)
- [Versiones](#versiones)
- [Instalación y uso](#instalación-y-uso)
- [Entorno en la nube (Lambda)](#entorno-en-la-nube-lambda)
- [Metas (objetivos 1–4)](#metas-objetivos-14)
- [Flujo de ramas e integración continua](#flujo-de-ramas-e-integración-continua)
- [Contribución](#contribución)
- [Licencias](#licencias)
- [Referencias](#referencias)

## Qué resuelve

Un diseñador CAD o ingeniero describe la pieza en lenguaje natural, por ejemplo:

> "placa de 120 × 120 mm, 6 mm de espesor, 4 agujeros de 12 mm en un círculo
> de 90 mm"

y obtiene, sin redactar prompts en inglés ni usar la consola:

| Salida | Formato | Uso |
| --- | --- | --- |
| Modelo | STEP (ISO 10303) | Abrir en cualquier CAD |
| Vista 3D | GLB | Visualizar en el navegador |
| Lista de materiales | CSV | Corte / compra |

Si la pieza no se puede construir, el asistente declina con un motivo en
español en vez de inventar geometría.

## Alcance

Catálogo cerrado de 8 familias: `plate`, `sheet_bracket`, `adapter`, `flange`,
`spacer`, `tornillería`, `extrusion` y `pipe`.

Fuera de alcance: cálculo estructural, verificación NSR-10/RETIE, Revit/BIM,
reentrenamiento, entrada por imagen, ensamblajes, autenticación y concurrencia.

## Arquitectura

El diagrama interactivo de arquitectura de runtime vive en
[`docs/arquitectura.html`](docs/arquitectura.html) (fuente versionada:
[`docs/arquitectura.json`](docs/arquitectura.json)). Muestra el camino principal
de una solicitud — del diseñador CAD a los entregables STEP/GLB/CSV — los tres
contenedores de Docker Compose y los dos servicios externos (API Gemini y
llama.cpp con GPU).

> **Pendiente (HU-14):** el diagrama todavía muestra la API Gemini y llama.cpp.
> El runtime actual usa DeepSeek por API y un único servicio Compose
> (`m2-cad`, Vue/FastAPI); falta regenerarlo con Archify.

La [Model Card](docs/model-card.md) documenta el modelo servido (`deepseek-v4-pro`) y la
línea base heredada de Hugging Face: origen, métricas medidas, limitaciones, sesgos y
licencia.

## Cómo funciona

1. **Generación** condicionada a partir de la solicitud en español, sin
   traducción previa (HU-14), con DeepSeek (`deepseek-v4-pro`) por API.
   Gemma 4 12B ConstraintKit sobre llama.cpp queda como línea base heredada.
2. **Verificación** geométrica determinista (constraint-kit / CadQuery /
   build123d / OpenCascade): aprueba o declina cada pieza.
3. **Entrega** por Vue 3 + FastAPI, con etapas reales mediante SSE y registro
   trazable (texto, resultado, latencia y versión del modelo).

## Estructura

    m2-asistente-cad/
    ├── src/m2_cad/          pipeline.py · banco.py · api.py · trabajos.py · web.py · registro.py
    ├── frontend/            Vue 3 · Composition API · TypeScript · Vite · Vitest
    ├── design/              referencia validada y tokens únicos
    ├── tests/               test_dataset.py · test_pipeline.py · test_banco.py ·
    │                        test_api.py · test_registro.py · test_sse.py · test_web.py
    ├── data/test_cases.csv  banco de 40 solicitudes
    ├── specs/               especificaciones SDD (001–017, índice en specs/README.md)
    ├── scripts/             fetch-model · verify-serve · vendor · cloud (Lambda/Vast.ai)
    ├── docs/                arquitectura.{html,json} y documentación
    ├── Dockerfile · docker-compose.yml · docker-compose.gemma.yml ·
    │                        docker-compose.gpu-remote.yml
    ├── pyproject.toml · uv.lock · .python-version
    ├── Makefile · .pre-commit-config.yaml · .editorconfig
    ├── CONSTITUTION.md      fuente única de verdad del proyecto
    ├── AGENTS.md · CONTRIBUTING.md · CODE_OF_CONDUCT.md
    └── .github/             ci.yml · labels · Dependabot · plantillas de PR e issues

## Requisitos

- **Python 3.11+** (contenedor en 3.12) con `uv`.
- **Node 24** para desarrollar/compilar localmente; Docker lo usa solo durante el build.
- **API key de DeepSeek** en `DEEPSEEK_API_KEY` (entorno o `.env`, ignorado por git).
  No hace falta GPU.
- **Docker** para el despliegue.
- Solo para la línea base heredada (HU-01): GPU con 16 GB de VRAM, NVIDIA Container
  Toolkit y el GGUF `gemma-4-12b-constraintkit` (Q6_K, ~9,8 GB, no versionado).

> El entorno de referencia es el contenedor Docker. La evidencia distingue
> modelo simulado e inferencia real: [integración HU-14/HU-15](docs/hu15-integracion-hu14.md).
> En **macOS
> Intel** la sincronización completa no concluye: `nlopt` no publica wheel para
> `x86_64` de macOS — usa Docker o la CI.

## Versiones

| Componente | Versión |
| --- | --- |
| Modelo | DeepSeek `deepseek-v4-pro` por API (HU-14) |
| Modelo heredado | `gemma-4-12b-constraintkit-GGUF` (Q6_K, ~9,8 GB) |
| Python | 3.12 (contenedor Docker) |
| cadquery | 2.7.0 |
| build123d | 0.10.0 |
| bd_warehouse | 0.2.0 |
| z3-solver | ≥ 4.12 |
| python-solvespace | ≥ 3.0 |
| llama.cpp (heredado) | 0.9.0-dev (commit f4777f9, backend CUDA) — servidor GGUF (Q6_K) |
| constraint-kit | repositorio del autor (sin modificar) |

## Instalación y uso

```bash
bash scripts/vendor-constraint-kit.sh
uv sync --locked --dev
make frontend-install
make check        # Ruff + Vitest + TypeScript + build + pytest/cobertura
uv run --locked uvicorn m2_cad.api:app --app-dir src --host 127.0.0.1 --port 8000 --workers 1
```

Abrir **http://127.0.0.1:8000/**: FastAPI sirve el build, API, SSE y descargas en
el mismo origen. No se inicia otro servidor frontend. El desarrollo con HMR
se explica en [frontend/README.md](frontend/README.md).

Variables del modelo:

| Variable | Uso | Valor por defecto |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | API key de DeepSeek (obligatoria) | — |
| `LLM_MODEL` | Modelo de DeepSeek | `deepseek-v4-pro` |
| `LLM_BASE_URL` | Otro servidor compatible con OpenAI (por ejemplo, llama.cpp) | `https://api.deepseek.com` |

Sin API key, `/generar` responde 503 con «El modelo no está configurado: falta
DEEPSEEK_API_KEY.». Los errores 401, 402, 429 y los tiempos de espera de DeepSeek se
informan en español y nunca incluyen la key.

Banco HU-02 contra el modelo real (HU-14, AC6 y AC7; gasta tokens):

```bash
make bench IDS=HU02-P01,HU02-P06,HU02-P11,HU02-P21,HU02-P26   # AC6: 5 solicitudes
make bench                                                      # AC7: las 40
```

Deja en `outputs/banco/` un CSV por caso y un resumen JSON con acierto, tasa de
`/dsl/check`, latencia media y tokens. Con `--precio-entrada` y `--precio-salida`
(USD por millón de tokens) también calcula el costo estimado.

### Seguimiento de experimentos (MLflow, HU-16)

Cada solicitud y cada corrida del banco queda en MLflow (params, métricas y
artefactos paso a paso), así dos modelos se comparan en la UI sin revisar casos a mano:

```bash
make mlflow                         # solo el servidor (UI en http://127.0.0.1:5000)
docker compose up --build           # m2-cad apunta a http://mlflow:5000
make bench IDS=HU02-P01,HU02-P06,HU02-P11,HU02-P21,HU02-P26 --precio-entrada 0.1 --precio-salida 0.4
```

- `m2-cad-generacion`: una corrida por solicitud con `modelo`, `version_modelo`,
  `familia`, `temperatura`, `latencia_ms`, tokens, `costo_usd`, `verificacion_ok`,
  los tags `solicitud_id`/`estado` (`entregada`, `declinada`, `error`, y `cancelada` en
  SSE) y los artefactos
  `programa.json`, `step`, `glb` y `csv`. Declinaciones y fallos cierran la corrida con
  su motivo; nunca queda en `RUNNING`. Las solicitudes SSE (HU-15) también generan su
  corrida, con el tag `transporte=sse`, al alcanzar el estado terminal.
- `m2-cad-banco`: una corrida padre por modelo con el resumen (acierto, latencia media,
  tokens y costo) y una hija por caso con `acierto`, `dsl_check_ok` y `error_relativo_pct`.
- Cada configuración servida queda como versión de modelo en el registro de MLflow
  (`LLM_MODEL_VERSION` o el id del modelo) y la corrida del CSV de registro ya no dice
  `desconocida`.

Sin servidor (o con `MLFLOW_TRACKING_ENABLED=0`) la generación concluye igual y el fallo
del seguimiento se emite como advertencia en el log: es observabilidad, no criterio de
aceptación de la pieza. `mlruns/`, `mlflow.db` y `mlflow-artifacts/` están en `.gitignore`.


### Despliegue local con Docker Compose (HU-10)

Requisitos: **Docker** con Compose v2 y `DEEPSEEK_API_KEY` en `.env` (ignorado por Git).
No hace falta GPU, pesos, Node ni preparar el vendor en el host: la imagen lo resuelve.

```bash
echo "DEEPSEEK_API_KEY=sk-..." > .env
make up            # docker compose up: m2-cad (API + SPA) y MLflow, en primer plano
make down          # en otra terminal: detiene y elimina todos los contenedores
```

La primera vez usar `docker compose up --build` para construir la imagen (requiere
memoria holgada: el build compila dependencias CAD).

| URL | Servicio |
| --- | --- |
| http://localhost:8000 | SPA en Vue (mismo origen que la API) |
| http://localhost:8000/health | Salud de la API (`{"status": "ok"}`) |
| http://localhost:8000/docs | Contrato OpenAPI |
| http://127.0.0.1:5000 | UI de MLflow |

Ambos puertos se publican solo en `127.0.0.1`; nada queda expuesto en la red.
Si un puerto está ocupado, liberarlo o cambiar el lado izquierdo del mapeo en
`docker-compose.yml` (por ejemplo `127.0.0.1:8001:8000`).

Prueba de humo y latencia contra el servicio levantado (gasta tokens de DeepSeek):

```bash
uv run python scripts/smoke_deploy.py --n 5     # AC4: una solicitud por familia
uv run python scripts/smoke_deploy.py --n 40    # AC3: p50/p90 sobre el banco completo
```

Escribe `smoke.csv` (id, familia, estado HTTP, resultado y latencia) y `smoke.json`
(p50/p90) en `outputs/smoke/` (`--salida` para cambiarlo) y termina con código 1 si
alguna solicitud no devuelve pieza ni declinación con motivo. Evidencia de HU-10:
[evidence.md](specs/010-hu-10-despliegue-local/evidence.md).

Gradio y su puerto `7860` se retiraron con HU-15.
El volumen `outputs/` conserva los archivos generados. La línea base Gemma y el
archivo independiente `docker-compose.gpu-remote.yml` son opciones heredadas;
no se activan en el arranque normal.

`M2_FRONTEND_DIST` permite ubicar el build (Docker: `/app/frontend/dist`).
`M2_CORS_ORIGINS` es una lista separada por comas de orígenes exactos HTTP(S), sin
comodines; por defecto admite `http://localhost:8000,http://127.0.0.1:8000`.
Para una URL de despliegue distinta, configurar su origen explícito. Una lista
vacía no autoriza llamadas cross-origin; la SPA del mismo origen sigue funcionando.
Las rutas API desconocidas devuelven JSON 404/405 y no HTML. Los assets del build
se sirven en `/assets/`; la SPA actual solo necesita `/`.

SSE no tiene middleware de compresión/buffering y devuelve `no-cache, no-transform`
y `X-Accel-Buffering: no`. No se deben añadir proxies que acumulen eventos.
Cancelar pide una detención cooperativa local: una llamada bloqueante al modelo o
CAD puede continuar hasta retornar; no confirma detención remota.
Contrato completo: [HU-15/SSE](docs/hu15-sse.md). Gobernanza arquitectónica:
[CONSTITUTION.md](CONSTITUTION.md).

### Variables de entorno

| Variable | La usa | Valor local | En Docker la fija |
| --- | --- | --- | --- |
| `DEEPSEEK_API_KEY` | Pipeline → API de DeepSeek (HU-14) | tu clave de [DeepSeek](https://platform.deepseek.com/api_keys) | el `${DEEPSEEK_API_KEY}` del entorno |
| `LLM_MODEL` | Modelo que pide el pipeline | `deepseek-v4-pro` | `deepseek-v4-pro` (salvo override) |
| `LLM_BASE_URL` | Pipeline → servidor compatible con OpenAI | `https://api.deepseek.com` | — (valor por defecto del código) |
| `M2_FRONTEND_DIST` | FastAPI → build Vue | `frontend/dist` | `/app/frontend/dist` |
| `M2_CORS_ORIGINS` | CORS exacto de FastAPI | localhost/127.0.0.1 en 8000 | mismo valor por defecto |
| `MLFLOW_TRACKING_URI` | Seguimiento → servidor MLflow o file store (HU-16) | `file:./mlruns` | `http://mlflow:5000` |
| `MLFLOW_TRACKING_ENABLED` | `0` apaga el seguimiento (no-op) | `1` | `${MLFLOW_TRACKING_ENABLED:-1}` |
| `MLFLOW_EXPERIMENT_NAME` / `MLFLOW_EXPERIMENT_BANCO` | Nombres de experimento | `m2-cad-generacion` / `m2-cad-banco` | igual |
| `MLFLOW_PRECIO_ENTRADA` / `MLFLOW_PRECIO_SALIDA` | USD por millón de tokens para `costo_usd` | `0` | `0` |
| `LLM_MODEL_VERSION` | Versión publicada por el proveedor (AC7) | id del modelo servido | id del modelo servido |

Copia `.env.example` a `.env` para ejecutar fuera de Docker.

> **Nota:** para la línea base heredada con Gemma, `LLM_BASE_URL` apunta al servidor
> llama.cpp (`http://llama:8080` dentro de Compose) y hace falta el GGUF; ver abajo.

## Entorno en la nube (Lambda) — heredado

> **Heredado (HU-01).** Desde HU-14 el modelo es la API de DeepSeek y no hace falta GPU.
> Esta sección solo sirve para reproducir la línea base con Gemma
> (`docker compose -f docker-compose.yml -f docker-compose.gemma.yml up`).

La validación de HU-01 corre en una instancia de [Lambda](https://lambda.ai) con GPU NVIDIA
(una **A10 de 24 GB** ya cumple el AC2 de ≤ 16 GB de VRAM). La GPU local de 4 GB no alcanza
para el GGUF Q6_K de ~9,8 GB: el modelo no entra.

1. Dashboard de Lambda → *Launch instance* → imagen **Lambda Stack (Ubuntu 22.04)** →
   1× A10 (24 GB) → tu clave SSH → *Launch*.
2. **Exponer el servicio**: *Firewall rules* → agregar TCP **8000** (Vue/FastAPI)
   restringido a tu IP. Sin esa regla el puerto no queda accesible desde afuera.
3. En la instancia:

```bash
git clone https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad.git
cd code-m2-asistente-cad
git switch develop
bash scripts/cloud/lambda-bootstrap.sh   # Docker + NVIDIA Container Toolkit + smoke test
make model-fetch                         # AC1: descarga 9,8 GB y verifica el SHA-256
docker compose -f docker-compose.yml -f docker-compose.gemma.yml up -d llama
make verify-serve                        # AC2: n_ctx=8192 y VRAM <= 16 GB
```

4. Comprobar desde tu máquina: `curl http://<IP-pública>:8000/health`.
   La verificación del modelo en 8080 se ejecuta dentro de la instancia, no desde el navegador.
5. Terminar la instancia (se factura por hora) cuando cierres la validación.

El AC3 (113 pruebas del kernel) no necesita GPU: se corre con `make kernel-test`, que
construye el contenedor del autor y ejecuta su suite dentro.

## Metas (objetivos 1–4)

| Indicador | Meta |
| --- | --- |
| Construcción conforme (±2 % volumen / caja) | ≥ 26/30 (85 %) |
| Declinación correcta | ≥ 8/10 |
| Latencia p90 (solicitud → STEP) | ≤ 60 s |
| Autonomía de usuarios (tareas sin ayuda) | ≥ 7/9 |
| Reproducibilidad | 1 comando, CI en verde |

## Flujo de ramas e integración continua

`develop` es la rama de integración: **toda rama de trabajo sale de `develop`** y vuelve por pull
request. `main` solo recibe entregas.

```bash
git switch develop && git pull          # 1. partir siempre de develop
git switch -c feature/hu-XX-tema       # 2. una rama por historia de usuario
make precommit-install                 # 3. una vez: hooks de Ruff y bloqueo de pesos
make check                             # 4. antes de abrir el PR: Ruff + pytest + cobertura
```

Cada pull request a `develop` dispara `.github/workflows/ci.yml`: Python 3.12
(`.python-version`), Node 24, `uv sync --locked --dev`, `npm ci` y `make check`.
Exige Ruff limpio, pruebas Vitest, TypeScript, build y pytest con cobertura ≥70 %
de `src/`. El build se genera antes de probar las rutas estáticas integradas.
Las pruebas útiles de la UI anterior se migraron a SPA/API; la trazabilidad de
los 23 casos está en [HU-15/despliegue](docs/hu15-despliegue.md).

La política de `develop` es exigir la CI en verde y una aprobación antes de fusionar; se activa
con la protección de rama del repositorio (Configuración → Branches). pre-commit es
la primera barrera local: bloquea errores de Ruff y archivos de pesos (`.gguf`, `.safetensors`),
que nunca se versionan.

## Contribución

`develop` es la rama de integración: toda contribución entra por pull request
con CI en verde y una aprobación. Lee [`CONTRIBUTING.md`](CONTRIBUTING.md)
(entorno, flujo de ramas y estándares), [`CONSTITUTION.md`](CONSTITUTION.md)
(verdad central del proyecto) y el
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Los issues usan plantillas de bug,
funcionalidad y spike en `.github/ISSUE_TEMPLATE/`.

## Licencias

Código propio: **MIT**. Modelo y motor (Gemma, constraint-kit, CadQuery,
build123d, Z3): **Apache 2.0 / MIT**; OpenCascade **LGPL 2.1**;
python-solvespace **GPL-3.0** (obliga solo al distribuir).

## Referencias

- Modelo: <https://huggingface.co/jajmangold/gemma-4-12b-constraintkit-GGUF>
- Motor geométrico: <https://github.com/jajmangold/constraint-kit>
