# m2-asistente-cad

Asistente CAD que convierte la descripción **en español** de un componente
metálico auxiliar en un modelo CAD **preliminar verificado** (STEP, GLB y lista
de materiales) en minutos — o que **declina con un motivo** cuando no puede
construirlo.

> ⚠️ **Toda salida es preliminar.** La verificación es solo geométrica; la
> resistencia y el cumplimiento de normas (NSR-10, RETIE) exigen revisión de un
> profesional responsable.

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

## Cómo funciona

1. **Traducción** ES→EN conservando números y unidades.
2. **Generación** condicionada con Gemma 4 12B ConstraintKit (GGUF Q6_K sobre
   llama.cpp).
3. **Verificación** geométrica determinista (constraint-kit / CadQuery /
   build123d / OpenCascade): aprueba o declina cada pieza.
4. **Entrega** por Vue 3 + FastAPI, con etapas reales mediante SSE y registro trazable (texto, resultado,
   latencia y versión del modelo). Plan B: DeepSeek por API.

## Estructura

    m2-asistente-cad/
    ├── src/m2_cad/          traduccion.py · pipeline.py · api.py · trabajos.py · web.py · registro.py
    ├── frontend/            Vue 3 · Composition API · TypeScript · Vite · Vitest
    ├── design/              referencia validada y tokens únicos
    ├── tests/               test_dataset.py · test_translate.py · test_pipeline.py · test_api.py
    ├── data/test_cases.csv  banco de 40 solicitudes
    ├── docs/                manuales y reporte del banco
    ├── Dockerfile · docker-compose.yml
    ├── pyproject.toml · uv.lock
    └── .pre-commit-config.yaml · .github/workflows/ci.yml

## Requisitos

- **Python 3.11+** (contenedor en 3.12) con `uv`.
- **Node 24** para desarrollar/compilar localmente; Docker lo usa solo durante el build.
- **GPU**: 16 GB de VRAM mín. (recomendado 24 GB); el modelo ocupa ~12 GB.
- **Modelo**: `gemma-4-12b-constraintkit-GGUF` (Q6_K, ~9,8 GB), no versionado.
- **Docker** + NVIDIA Container Toolkit para el despliegue.

> La evidencia HU-15 distingue pruebas nativas, servicios simulados e inferencia
> real. Docker no pudo arrancar en la validación local más reciente; véase
> [evidencia de despliegue](docs/hu15-despliegue.md).

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
bash scripts/vendor-constraint-kit.sh
uv sync --locked --dev
make frontend-install
make check        # Ruff + Vitest + TypeScript + build + pytest/cobertura
uv run --locked uvicorn m2_cad.api:app --app-dir src --host 127.0.0.1 --port 8000 --workers 1
```

Abrir **http://127.0.0.1:8000/**: FastAPI sirve el build, API, SSE y descargas en
el mismo origen. No se inicia otro servidor frontend. El desarrollo con HMR
se explica en [frontend/README.md](frontend/README.md).

Con Docker, sin compilar Vue ni preparar el vendor manualmente en el host:

```bash
docker compose up --build
```

Requiere pesos del modelo en `models/`, GPU/NVIDIA Container Toolkit y
`GEMINI_API_KEY` definida únicamente en el entorno del backend (o `.env` local
ignorado). API/UI publicadas en **8000**; el modelo tiene diagnóstico local en
`127.0.0.1:8080`. Gradio y su puerto se retiraron. El volumen `outputs/` conserva
los archivos generados. Para GPU remota se usa el archivo independiente
`docker-compose.gpu-remote.yml`; mantiene el mismo origen web y volumen de salidas.

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

## Entorno en la nube (Lambda)

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
docker compose up -d --build
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

## Licencias

Código propio: **MIT**. Modelo y motor (Gemma, constraint-kit, CadQuery,
build123d, Z3): **Apache 2.0 / MIT**; OpenCascade **LGPL 2.1**;
python-solvespace **GPL-3.0** (obliga solo al distribuir).

## Referencias

- Modelo: <https://huggingface.co/jajmangold/gemma-4-12b-constraintkit-GGUF>
- Motor geométrico: <https://github.com/jajmangold/constraint-kit>
