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

## Cómo funciona

1. **Traducción** ES→EN conservando números y unidades.
2. **Generación** condicionada con Gemma 4 12B ConstraintKit (GGUF Q6_K sobre
   llama.cpp).
3. **Verificación** geométrica determinista (constraint-kit / CadQuery /
   build123d / OpenCascade): aprueba o declina cada pieza.
4. **Entrega** por FastAPI + Gradio, con registro trazable (texto, resultado,
   latencia y versión del modelo). Plan B: DeepSeek por API.

## Estructura

    m2-asistente-cad/
    ├── src/m2_cad/          traduccion.py · pipeline.py · api.py · interfaz.py · registro.py
    ├── tests/               test_dataset.py · test_translate.py · test_pipeline.py ·
    │                        test_api.py · test_registro.py · test_interfaz.py
    ├── data/test_cases.csv  banco de 40 solicitudes
    ├── specs/               especificaciones Spec Kit (001–007): spec · plan · tasks
    ├── scripts/             fetch-model · verify-serve · vendor · cloud (Lambda/Vast.ai)
    ├── docs/                arquitectura.{html,json} y documentación
    ├── Dockerfile · docker-compose.yml · docker-compose.gpu-remote.yml
    ├── pyproject.toml · uv.lock · .python-version
    ├── Makefile · .pre-commit-config.yaml · .editorconfig
    ├── CONSTITUTION.md      fuente única de verdad del proyecto
    ├── AGENTS.md · CONTRIBUTING.md · CODE_OF_CONDUCT.md
    └── .github/             ci.yml · labels · Dependabot · plantillas de PR e issues

## Requisitos

- **Python 3.11+** (contenedor en 3.12) con `uv`.
- **GPU**: 16 GB de VRAM mín. (recomendado 24 GB); el modelo ocupa ~12 GB.
- **Modelo**: `gemma-4-12b-constraintkit-GGUF` (Q6_K, ~9,8 GB), no versionado.
- **Docker** + NVIDIA Container Toolkit para el despliegue.

> El entorno de referencia es el contenedor Docker (único probado). En **macOS
> Intel** la sincronización completa no concluye: `nlopt` no publica wheel para
> `x86_64` de macOS — usa Docker o la CI.

## Versiones

| Componente | Versión |
| --- | --- |
| Modelo | `gemma-4-12b-constraintkit-GGUF` (Q6_K, ~9,8 GB) |
| Python | 3.12 (contenedor Docker) |
| cadquery | 2.7.0 |
| build123d | 0.10.0 |
| bd_warehouse | 0.2.0 |
| z3-solver | ≥ 4.12 |
| python-solvespace | ≥ 3.0 |
| llama.cpp | 0.9.0-dev (commit f4777f9, backend CUDA) — servidor GGUF (Q6_K) |
| constraint-kit | repositorio del autor (sin modificar) |

## Instalación y uso

```bash
uv sync --dev     # 1. dependencias (sin pip install)
make check        # 2. Ruff + pytest
make up           # 3. FastAPI (:8000) y Gradio (:7860) con GPU
```

O con Docker:

```bash
docker compose up --build
```

## Entorno en la nube (Lambda)

La validación de HU-01 corre en una instancia de [Lambda](https://lambda.ai) con GPU NVIDIA
(una **A10 de 24 GB** ya cumple el AC2 de ≤ 16 GB de VRAM). La GPU local de 4 GB no alcanza
para el GGUF Q6_K de ~9,8 GB: el modelo no entra.

1. Dashboard de Lambda → *Launch instance* → imagen **Lambda Stack (Ubuntu 22.04)** →
   1× A10 (24 GB) → tu clave SSH → *Launch*.
2. **Exponer el servicio**: *Firewall rules* → agregar TCP **8080** (llama.cpp) y **8000**
   (FastAPI), restringidos a tu IP. Sin esa regla el puerto no queda accesible desde afuera.
3. En la instancia:

```bash
git clone https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad.git
cd code-m2-asistente-cad
git switch feature/hu-01-gemma-constraintkit-serve
bash scripts/cloud/lambda-bootstrap.sh   # Docker + NVIDIA Container Toolkit + smoke test
make model-fetch                         # AC1: descarga 9,8 GB y verifica el SHA-256
docker compose up -d llama
make verify-serve                        # AC2: n_ctx=8192 y VRAM <= 16 GB
```

4. Comprobar desde tu máquina: `curl http://<IP-pública>:8080/health`.
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

Cada pull request a `develop` dispara `.github/workflows/ci.yml`, que corre en Python 3.12 (el
de `.python-version`) y exige tres cosas: **Ruff** limpio con las reglas E, F, I y B, **pytest con
cobertura ≥ 70 %** de `src/` (umbral en `[tool.coverage.report]` de `pyproject.toml`) y el
despliegue de ese entorno con `uv sync --dev` (sin `pip install` ni `requirements.txt`).

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
