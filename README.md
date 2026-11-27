# m2-asistente-cad

[![CI](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad/actions/workflows/ci.yml)
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
- [Sistema de diseño](#sistema-de-diseño)
- [Cómo funciona](#cómo-funciona)
- [Estructura](#estructura)
- [Requisitos](#requisitos)
- [Versiones](#versiones)
- [Instalación y uso](#instalación-y-uso)
- [Control de costo, límites e idempotencia](#control-de-costo-límites-e-idempotencia-hu-32)
- [Acceso y usuarios (HU-53)](#acceso-y-usuarios-hu-53)
- [Entorno en la nube (Lambda)](#entorno-en-la-nube-lambda)
- [Metas (objetivos 1–4)](#metas-objetivos-14)
- [Informe final](docs/informe-final.md)
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
de una solicitud — de la SPA en Vue, por `POST /generar` con progreso SSE, al
pipeline, la verificación y los entregables STEP/GLB/CSV — los dos contenedores de
Docker Compose (`m2-cad` y `mlflow`) y la API externa de DeepSeek. Cada componente
cita su código en una revisión fija; se regenera con Archify
([SPEC-020](specs/020-diagrama-arquitectura/spec.md)).

## Sistema de diseño

Los tokens, la escala tipográfica y los temas claro/oscuro están documentados en
[`docs/diseno-v2.md`](docs/diseno-v2.md). La fuente única es
`frontend/src/design/tokens.css`; la preferencia de tema se guarda en el navegador
y respeta `prefers-color-scheme` cuando no hay elección explícita.

La gestión del proyecto vive en el
[tablero Kanban de GitHub Projects](https://github.com/users/luisfermezaramrez-stack/projects/1/views/1)
(Backlog, In Progress, In Review y Done), y cada historia enlaza su especificación en
[`specs/`](specs/README.md) y su pull request.

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
4. **Navegación** por URLs propias (`/nueva-solicitud`, `/historial` y `/ajustes`),
   con borrador y tema recuperables al abrir la vista en otra pestaña (HU-38).
5. **Historial** de solicitudes reales desde el registro persistente: listado con
   filtros por resultado y por descripción, y reapertura que descarga el STEP de una
   solicitud anterior aunque el servidor se haya reiniciado (HU-37).

## Estructura

    m2-asistente-cad/
    ├── src/m2_cad/          pipeline.py · banco.py · api.py · trabajos.py · web.py · registro.py
    ├── frontend/            Vue 3 · Composition API · TypeScript · Vite · Vitest
    ├── design/              referencia histórica de HU-15 (no importada por la app)
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
make check        # Ruff + contratos + Vitest + TypeScript + build + pytest/cobertura
uv run --locked uvicorn m2_cad.api:app --app-dir src --host 127.0.0.1 --port 8000 --workers 1
```

En otra terminal, para que los flujos SSE sobrevivan a un reinicio, arrancar el
worker (HU-45):

```bash
make worker    # python -m m2_cad.worker; comparte data/cola.json con la API
```

Si el worker no está corriendo, la API encola la solicitud y el cliente SSE espera
hasta que un worker la procese. El apagado ordenado del worker deja de aceptar
trabajos nuevos y termina el trabajo en curso antes de salir.

Abrir **http://127.0.0.1:8000/**: FastAPI sirve el build, API, SSE y descargas en
el mismo origen. No se inicia otro servidor frontend. El desarrollo con HMR
se explica en [frontend/README.md](frontend/README.md).

### Acceso y usuarios (HU-53)

La autenticación está **activa por defecto** (`M2_AUTH_ENABLED=1`). La SPA muestra
un formulario de acceso, envía `POST /v1/auth/login` y conserva la sesión en una cookie
`HttpOnly` / `SameSite=Lax` firmada con HMAC-SHA256; `GET /v1/auth/me` informa si hay
sesión y `POST /v1/auth/logout` la cierra. `/v1/health` y `/v1/ready` siguen abiertos para
monitoreo; el resto de rutas de datos (generar, consultar, cancelar, descargar,
registros y `/v1/uso`) devuelve 401 sin sesión y 404 cuando el recurso pertenece a otro
usuario, también para los trabajos que ejecuta el worker de la cola (HU-45). El token de
descarga de HU-36 se exige además de la sesión.

Protecciones de la sesión:

- Tras `M2_AUTH_MAX_INTENTOS` inicios fallidos (5 por defecto) contra un usuario desde
  un mismo cliente, o 4 veces ese valor desde el cliente contra cualquier usuario, en
  `M2_AUTH_VENTANA_INTENTOS_SEGUNDOS` (300), se responde `429` con `Retry-After`, incluso
  con la clave correcta. Cada intento se anota antes de verificar la clave, así las
  peticiones simultáneas no esquivan el límite, y entrar con otra cuenta no borra los
  fallos acumulados. El contador vive en el proceso (`--workers 1`) y usa la IP que ve
  uvicorn: detrás de un proxy inverso hay que habilitar `--proxy-headers` con
  `--forwarded-allow-ips`, o todos los clientes compartirían el mismo contador.
- Un recurso de otro usuario responde el mismo `404` que uno inexistente. Sin sesión,
  `POST /v1/generar` responde `401` aunque el cuerpo sea inválido, y no escribe en el
  registro.
- Un usuario inexistente cuesta lo mismo que una clave errónea: el tiempo de respuesta
  no revela qué usuarios existen.
- La firma de la cookie depende del hash vigente del usuario: quitarlo de
  `M2_AUTH_USERS` o cambiar su clave invalida sus sesiones. `POST /v1/auth/logout` borra
  la cookie del navegador; un token copiado antes sigue valiendo hasta su expiración
  (`M2_AUTH_TTL_SECONDS`).
- Con la autenticación activa, una configuración inválida impide arrancar la API.
- Los topes y la idempotencia de HU-32 se asocian al usuario: `X-Session-ID` y la IP
  sólo se usan en modo local.

Los usuarios se definen en `M2_AUTH_USERS` con hashes PBKDF2-SHA256, nunca en el
repositorio. Para generar uno:

```bash
make hash-clave          # pide la clave por prompt oculto
# M2_CLAVE_NUEVA='mi-clave' make hash-clave   # sólo para automatización local
```

Copie el hash resultante en `M2_AUTH_USERS` como
`'{"ana":"pbkdf2_sha256$..."}'` y defina `M2_AUTH_SECRET` con un secreto aleatorio
de al menos 32 bytes. Para desarrollo local sin sesión, fijar explícitamente
`M2_AUTH_ENABLED=0`; en ese modo las solicitudes se registran como `anónimo`.
El CSV de registro incorpora la columna `usuario`; los archivos anteriores se
migran automáticamente sin borrar filas. Plan y decisiones:
[SPEC-054](specs/054-hu-53-autenticacion/plan.md).

### Contrato de la API (HU-27 y HU-31)

Después de modificar el contrato FastAPI, ejecutar `make api-types` y versionar
`frontend/src/generated/api.ts` con el cambio. El esquema se obtiene de
`app.openapi()` (el mismo que `/openapi.json`), sin arrancar el servidor, usar
claves, GPU ni red una vez instaladas las dependencias Python/npm.

`make api-types-check` compara los tipos sin modificarlos; también se ejecuta en
`make check` y en CI. Si detecta una diferencia, falla e indica `make api-types`.
`api.ts` consume los tipos generados y conserva `parseJob` para validar datos
HTTP/SSE en ejecución. Plan y alcance: [SPEC-028](specs/028-hu-27-tipos-openapi/plan.md).

La API pública se sirve bajo `/v1` (por ejemplo `/v1/health` y `/v1/generar`). El
esquema de esa versión está congelado en [`contracts/openapi-v1.json`](contracts/openapi-v1.json):
`make api-contract` lo regenera y `make api-contract-check` falla si un campo o una ruta
cambia sin actualizarlo; ambos forman parte de `make check` y de CI. Las rutas planas
siguen funcionando como redirecciones `307` con cabeceras `Deprecation`, `Sunset` y
`Link` durante 90 días. Los clientes deben seguir la redirección `307`
(`curl -L`, o `follow_redirects=True` en `httpx`); política completa:
[versionado de la API](docs/versionado-api.md) · [SPEC-032](specs/032-hu-31-api-v1/plan.md).

Variables del modelo:

| Variable | Uso | Valor por defecto |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | API key de DeepSeek (obligatoria) | — |
| `LLM_MODEL` | Modelo de DeepSeek | `deepseek-v4-pro` |
| `LLM_BASE_URL` | Otro servidor compatible con OpenAI (por ejemplo, llama.cpp) | `https://api.deepseek.com` |
| `LLM_MAX_RETRIES` | Reintentos adicionales ante 500/502/503/504, timeout o conexión (0–5) | `2` |
| `LLM_RETRY_BASE_SECONDS` / `LLM_RETRY_MAX_SECONDS` | Base y tope del backoff exponencial | `0.25` / `3` |
| `LLM_CACHE_TTL_SECONDS` / `LLM_CACHE_MAX_ITEMS` | TTL y capacidad de la caché de respuestas (0 desactiva) | `1800` / `256` |

Sin API key, `/generar` responde 503 con «El modelo no está configurado: falta
DEEPSEEK_API_KEY.». Los errores 401, 402, 429 y los tiempos de espera de DeepSeek se
informan en español y nunca incluyen la key. Los 500/502/503/504, los timeouts y los
fallos de conexión se reintentan hasta 2 veces dentro de un plazo total de 120 s; una
respuesta idéntica se reutiliza desde la caché local durante 30 min sin volver a pagar
tokens.

Banco HU-02 contra el modelo real (HU-14, AC6 y AC7; gasta tokens):

```bash
make bench IDS=HU02-P01,HU02-P06,HU02-P11,HU02-P21,HU02-P26   # AC6: 5 solicitudes
make bench                                                      # AC7: las 40
```

HU-07 añade `make bench-report`: evaluación HTTP de las 40 solicitudes con reporte
por familia y enlaces de trazabilidad, sin cambiar `make bench`. Ambos consumen
tokens si apuntan al modelo real. La [evidencia auditada HU-07](docs/hu07/README.md)
registra 30/30 conformes y 10/10 declinaciones; la revisión humana de forma sigue pendiente.

`make bench` deja en `outputs/banco/` un CSV por caso y un resumen JSON con acierto, tasa de
`/dsl/check`, latencia media y tokens. Con `--precio-entrada` y `--precio-salida`
(USD por millón de tokens) también calcula el costo estimado.

### Seguimiento de experimentos (MLflow, HU-16)

Cada solicitud y cada corrida del banco queda en MLflow (params, métricas y
artefactos paso a paso), así dos modelos se comparan en la UI sin revisar casos a mano:

```bash
make mlflow                         # solo el servidor (UI en http://127.0.0.1:5000)
docker compose up --build           # m2-cad apunta a http://mlflow:5000
# El banco corre en el host: sin MLFLOW_TRACKING_URI escribe en ./mlruns y no aparece en la UI.
# Los precios (USD por 1M tokens) solo se leen de las opciones; make bench no las reenvía.
MLFLOW_TRACKING_URI=http://127.0.0.1:5000 uv run python -m m2_cad.banco \
  --ids HU02-P01,HU02-P06,HU02-P11,HU02-P21,HU02-P26 --precio-entrada 0.1 --precio-salida 0.4
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

### Control de costo, límites e idempotencia (HU-32)

`POST /v1/generar` acepta dos cabeceras opcionales:

| Cabecera | Efecto |
| --- | --- |
| `Idempotency-Key` | Reenviar la misma clave devuelve la generación original (JSON o estado SSE) sin crear otro trabajo ni sumar costo. Reutilizarla con otro texto/sesión/transporte da `409`. |
| `X-Session-ID` | Identifica la sesión para el tope por ventana; si no se envía se usa la IP del cliente. Con autenticación activa (HU-53) se ignora y cuenta el usuario. |

`GET /v1/uso` publica el gasto acumulado del día en UTC, sin datos personales:

```json
{
  "fecha": "2026-11-25",
  "costo_usd": 0.0004,
  "moneda": "USD",
  "generaciones": 2,
  "presupuesto_diario_usd": 0,
  "limite_solicitudes_ventana": 0,
  "ventana_segundos": 60
}
```

Los topes se configuran con `M2_LIMITE_SOLICITUDES_VENTANA`, `M2_VENTANA_SEGUNDOS` y
`M2_PRESUPUESTO_DIARIO_USD`. Cero desactiva cada control, así que sin variables nuevas
el comportamiento es el de siempre. Los rechazos son `429` con `X-Limite-Tipo:
ventana|presupuesto` (y `Retry-After` cuando aplica); el límite de capacidad de 128
trabajos sigue siendo un `503` distinto. El estado vive en el proceso (`--workers 1`);
al escalar se migraría a un almacén compartido sin cambiar la API.

Ejemplo con un tope de 2 solicitudes por minuto y presupuesto de 0,10 USD:

```bash
export M2_LIMITE_SOLICITUDES_VENTANA=2 M2_VENTANA_SEGUNDOS=60
export M2_PRESUPUESTO_DIARIO_USD=0.10
curl -H 'X-Session-ID: disenador-1' -H 'Idempotency-Key: pedido-42' \
  -H 'Content-Type: application/json' -d '{"texto":"Espaciador de 14 mm"}' \
  http://127.0.0.1:8000/v1/generar
curl http://127.0.0.1:8000/v1/uso
```

Detalle, decisiones y evidencia: [SPEC-033](specs/033-hu-32-costo-limites-idempotencia/).


### Despliegue local con Docker Compose (HU-10)

Requisitos: **Docker** con Compose v2 y `DEEPSEEK_API_KEY` en `.env` (ignorado por Git).
No hace falta GPU, pesos, Node ni preparar el vendor en el host: la imagen lo resuelve.

```bash
echo "DEEPSEEK_API_KEY=sk-..." > .env
make up            # docker compose up: m2-cad (API + SPA), worker y MLflow
make down          # en otra terminal: detiene y elimina todos los contenedores
```

La primera vez usar `docker compose up --build` para construir la imagen (requiere
memoria holgada: el build compila dependencias CAD).

| URL | Servicio |
| --- | --- |
| http://localhost:8000 | SPA en Vue (mismo origen que la API) |
| http://localhost:8000/v1/health | Salud de la API (`{"status": "ok"}`) |
| http://localhost:8000/v1/uso | Gasto acumulado del día (HU-32) |
| http://localhost:8000/docs | Contrato OpenAPI |
| http://127.0.0.1:5000 | UI de MLflow |
| `m2-cad-worker` | Worker SSE separado; consume `/app/data/cola.json` |

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
alguna solicitud no devuelve pieza ni declinación con motivo. Con la autenticación activa
(HU-53) inicia sesión con `--usuario` (o `M2_SMOKE_USUARIO`) y la clave de `M2_SMOKE_CLAVE`,
que conviene leer sin eco (`read -rs M2_SMOKE_CLAVE && export M2_SMOKE_CLAVE`); sin
credenciales válidas termina con código 2 antes de generar. Evidencia de HU-10:
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

HU-45 conserva la cola de trabajos en `data/cola.json` con escritura atómica
(SPEC-031). La API sólo encola; el worker publica cada etapa como un evento SSE
completo. Tras un reinicio, los trabajos no terminados se reanudan y el registro
conserva una sola fila por `solicitud_id`. El flag `M2_COLA_HABILITADA=0` existe
sólo para la batería de pruebas SSE heredada, que ejecuta en proceso.

Con la cola activa, el costo de cada generación SSE lo mide el worker y queda en la
cola. La API lo suma una sola vez al presupuesto diario de HU-32, en el día UTC en que
terminó el trabajo, antes de aceptar otra solicitud y al consultar `GET /v1/uso`.
Repetir una `Idempotency-Key` devuelve el estado del trabajo encolado.
Contrato completo: [HU-15/SSE](docs/hu15-sse.md). Gobernanza arquitectónica:
[CONSTITUTION.md](CONSTITUTION.md).

### Operación e incidentes

Ante una falla del proveedor, credenciales, rollback o restauración de datos, seguir el
[runbook operativo](docs/runbook-operativo.md). No incluye secretos y sus comandos se ejecutan
desde la raíz del repositorio.

### Variables de entorno

| Variable | La usa | Valor local | En Docker la fija |
| --- | --- | --- | --- |
| `DEEPSEEK_API_KEY` | Pipeline → API de DeepSeek (HU-14) | tu clave de [DeepSeek](https://platform.deepseek.com/api_keys) | el `${DEEPSEEK_API_KEY}` del entorno |
| `LLM_MODEL` | Modelo que pide el pipeline | `deepseek-v4-pro` | `deepseek-v4-pro` (salvo override) |
| `LLM_BASE_URL` | Pipeline → servidor compatible con OpenAI | `https://api.deepseek.com` | — (valor por defecto del código) |
| `M2_FRONTEND_DIST` | FastAPI → build Vue | `frontend/dist` | `/app/frontend/dist` |
| `M2_CORS_ORIGINS` | CORS exacto de FastAPI | localhost/127.0.0.1 en 8000 | mismo valor por defecto |
| `M2_DOWNLOAD_SECRET` | Firma de tokens de descarga (HU-36) | secreto aleatorio local | `${M2_DOWNLOAD_SECRET:?}` |
| `M2_AUTH_ENABLED` | Activa la sesión HU-53 | `1` (fijar `0` para el modo local sin sesión) | `1` |
| `M2_AUTH_SECRET` | Firma HMAC de la cookie de sesión; obligatorio con la autenticación activa (la API no arranca sin él) | sin valor | `${M2_AUTH_SECRET:-}` |
| `M2_AUTH_USERS` | JSON usuario → hash PBKDF2 (HU-53); obligatorio con la autenticación activa | sin valor | `${M2_AUTH_USERS:-}` |
| `M2_AUTH_COOKIE_SECURE` | Exige HTTPS para la cookie | `0` en HTTP local | `1` |
| `M2_AUTH_TTL_SECONDS` | Vigencia de la sesión | `86400` | `86400` (o el valor del entorno) |
| `M2_AUTH_MAX_INTENTOS` | Inicios de sesión fallidos permitidos por cliente antes del `429` | `5` | `5` |
| `M2_AUTH_VENTANA_INTENTOS_SEGUNDOS` | Ventana del límite de intentos | `300` | `300` |
| `MLFLOW_TRACKING_URI` | Seguimiento → servidor MLflow o file store (HU-16) | `file:./mlruns` | `http://mlflow:5000` |
| `MLFLOW_TRACKING_ENABLED` | `0` apaga el seguimiento (no-op) | `1` | `${MLFLOW_TRACKING_ENABLED:-1}` |
| `MLFLOW_EXPERIMENT_NAME` / `MLFLOW_EXPERIMENT_BANCO` | Nombres de experimento | `m2-cad-generacion` / `m2-cad-banco` | igual |
| `MLFLOW_PRECIO_ENTRADA` / `MLFLOW_PRECIO_SALIDA` | USD por millón de tokens para `costo_usd` (HU-32 lo agrega en `/v1/uso`) | `0` | `0` |
| `M2_LIMITE_SOLICITUDES_VENTANA` | Solicitudes permitidas por sesión y ventana (HU-32; `0` desactiva) | `0` | `0` |
| `M2_VENTANA_SEGUNDOS` | Duración de la ventana de uso (HU-32) | `60` | `60` |
| `M2_PRESUPUESTO_DIARIO_USD` | Presupuesto UTC en USD (`0` desactiva; HU-32) | `0` | `0` |
| `LLM_MODEL_VERSION` | Versión publicada por el proveedor (AC7) | id del modelo servido | id del modelo servido |
| `M2_LOG_LEVEL` | Nivel del logging JSON de `m2_cad` (HU-24) | `INFO` | `INFO` (o el valor del entorno) |
| `M2_COLA_HABILITADA` | `1` usa cola + worker; `0` ejecuta SSE en proceso (HU-45) | `1` | `1` |
| `M2_COLA_PATH` | JSON compartido por API y worker (HU-45) | `data/cola.json` | `/app/data/cola.json` |
| `LLM_MAX_RETRIES` | Reintentos del LLM ante 5xx transitorios/timeout (HU-25) | `2` | `2` |
| `LLM_RETRY_BASE_SECONDS` / `LLM_RETRY_MAX_SECONDS` | Backoff exponencial (HU-25) | `0.25` / `3` | igual |
| `LLM_CACHE_TTL_SECONDS` / `LLM_CACHE_MAX_ITEMS` | Caché de respuestas del LLM (HU-25) | `1800` / `256` | igual |

Copia `.env.example` a `.env` para ejecutar fuera de Docker.

Los registros del paquete `m2_cad` se emiten en JSON con `nivel`, `modulo`, `mensaje`,
`marca_tiempo` y, cuando aplica, `request_id` y `job_id`. El `request_id` se reutiliza del
encabezado `X-Request-ID` cuando es un UUID válido y, si no, se genera uno nuevo. Ese mismo
id se etiqueta en la corrida de MLflow, de modo que una sola búsqueda reconstruye la
solicitud. Las claves, tokens Bearer, cabeceras `Authorization` y datos personales se
redactan antes de escribir el log.

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
bash scripts/cloud/lambda-bootstrap.sh   # Docker + NVIDIA Container Toolkit + smoke test
make model-fetch                         # AC1: descarga 9,8 GB y verifica el SHA-256
docker compose -f docker-compose.yml -f docker-compose.gemma.yml up -d llama
make verify-serve                        # AC2: n_ctx=8192 y VRAM <= 16 GB
```

4. Comprobar desde tu máquina: `curl http://<IP-pública>:8000/v1/health`.
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

El [informe final](docs/informe-final.md) consolida la meta, el valor medido, el
estado y la evidencia de cada objetivo (HU-13).

## Flujo de ramas e integración continua

`main` es la única rama de integración: **toda rama de trabajo sale de `main`** y vuelve por pull
request con `Closes #N`, que cierra la issue al fusionar. Las entregas son etiquetas sobre `main`.

```bash
git switch main && git pull             # 1. partir siempre de main
git switch -c feature/hu-XX-tema       # 2. una rama por historia de usuario
make precommit-install                 # 3. una vez: hooks de Ruff y bloqueo de pesos
make check                             # 4. antes de abrir el PR: Ruff + pytest + cobertura
```

Cada pull request a `main` dispara `.github/workflows/ci.yml`: Python 3.12
(`.python-version`), Node 24, `uv sync --locked --dev`, `npm ci` y `make check`.
Exige Ruff limpio, pruebas Vitest, TypeScript, build y pytest con cobertura ≥70 %
de `src/`. El build se genera antes de probar las rutas estáticas integradas.
Las pruebas útiles de la UI anterior se migraron a SPA/API; la trazabilidad de
los 23 casos está en [HU-15/despliegue](docs/hu15-despliegue.md).

La política de `main` es exigir la CI en verde y una aprobación antes de fusionar; se activa
con la protección de rama del repositorio (Configuración → Branches). pre-commit es
la primera barrera local: bloquea errores de Ruff y archivos de pesos (`.gguf`, `.safetensors`),
que nunca se versionan.

## Contribución

`main` es la única rama de integración: toda contribución entra por pull request
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
