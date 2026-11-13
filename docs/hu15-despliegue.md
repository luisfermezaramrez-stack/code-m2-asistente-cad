# HU-15 / #39 · Integración y evidencia de despliegue

## Contrato operativo

- Vue 3 se construye con Vite y se sirve desde FastAPI en `/`; assets con hash
  en `/assets/`. No hay fallback HTML global: rutas API inexistentes responden
  JSON 404/405. Si falta el build, `/` responde 503 JSON; `/health` sigue disponible.
- CORS permite solo orígenes HTTP(S) exactos de `M2_CORS_ORIGINS`, sin comodines ni
  credenciales. Por defecto: localhost y 127.0.0.1 en 8000. Lista vacía: únicamente
  solicitudes de navegador del mismo origen. No sustituye autenticación.
- JSON existente, SSE y GET/DELETE de trabajos se conservan. GET/HEAD de archivos
  siguen limitados a un resultado verificado y al directorio de salidas.
- No se introduce proxy, compresión ni acumulación de streams. SSE mantiene
  `X-Accel-Buffering: no`, `Cache-Control: no-cache, no-transform` y entrega incremental.
- Un solo worker de Uvicorn, porque el registro de trabajos es local al proceso.
  Cancelar es cooperativo; ni cerrar la conexión ni un 202 confirman detención
  completa. Un terminal `cancelado` confirma únicamente salida segura local.

## Imagen y Compose

Dockerfile multietapa: Node 24 ejecuta `npm ci`, TypeScript y build; otra etapa
obtiene el vendor fijado por `scripts/vendor-constraint-kit.sh`; la imagen final
Python 3.12 instala con `uv sync --frozen --no-dev` y contiene solo el build del
frontend. No depende de `node_modules`, vendor ni `dist` preparados en el host.
Se mantiene C17 para las extensiones nativas y se incorpora un healthcheck de API.
Se comprobó que el script vendor tiene CRLF en este checkout Windows; la etapa
Docker normaliza su copia a LF antes de ejecutarla con Bash.

`docker compose up --build` arranca `llama` y `m2-cad`. Solo `m2-cad` sirve la UI
y API al usuario en 8000. El puerto de diagnóstico 8080 del modelo se liga solo
a loopback; no forma parte del cliente. Se eliminaron el servicio Gradio, su
dependencia directa/transitiva y el puerto 7860. Pesos y credenciales del backend
siguen siendo requisitos de inferencia, no se empaquetan en el frontend.

El archivo independiente `docker-compose.gpu-remote.yml` mantiene el túnel del
modelo remoto y los volúmenes `data/` y `outputs/`, también con un único servicio
web en 8000. Ningún Compose monta un proxy con buffering SSE.

## Migración de los 23 casos de HU-08 antes de retirar código

La suite anterior contenía 21 funciones y 23 casos por parametrización de la
entrada inválida. Se ejecutaron las pruebas SPA/API ampliadas antes de eliminar
`interfaz.py` y `test_interfaz.py`. El catálogo original se conserva en Git y en
la especificación histórica HU-08; no se reescribe su evidencia pasada.

| Función anterior (sin prefijo `test_`) | Destino y contrato útil conservado |
| --- | --- |
| `rechaza_entrada_invalida` (3 casos) | `App.test.ts`: vacío, espacios y >1000 caracteres; sin POST, error asociado y foco |
| `solicitud_declinada` | SPA: motivo visible, modelo y descargas ausentes |
| `generacion_con_archivos` | SPA: visor y tres enlaces independientes; API: bytes GET/HEAD |
| `error_de_conexion` | SPA: mensaje comprensible, sin falso terminal ni archivos |
| `respuesta_desconocida` | `api.test.ts`: contrato desconocido rechazado; nunca éxito |
| `archivo_fuera_de_outputs` | `test_sse.py`: rechazo de rutas ajenas/traversal |
| `archivo_con_extension_incorrecta` | API: extensión debe corresponder al formato solicitado |
| `archivo_inexistente` | API devuelve 404; SPA no ofrece el enlace tras HEAD |
| `consultar_api_respuesta_exitosa` | SPA: método POST, cuerpo, cabeceras y AbortSignal; recepción SSE válida |
| `consultar_api_error_http` | SPA: detalle HTTP público visible, sin archivos |
| `consultar_api_error_de_red` | SPA: fallo de red explícito, sin inferir una etapa |
| `creacion_de_interfaz` | Montaje Vue y aviso profesional; API sirve índice/assets construidos |
| `sin_glb_con_step_disponible` | SPA: STEP/CSV se mantienen aunque falte GLB |
| `glb_disponible_sin_step` | SPA: visor y aviso de ausencia STEP; enlaces independientes |
| `error_muestra_url_configurada` | Sustituido por cliente same-origin y mensajes sin direcciones/secretos del modelo; preserva aviso de indisponibilidad, no expone configuración privada |
| `crear_interfaz_crea_outputs` | Responsabilidad movida al pipeline/exportador: pruebas CAD crean subcarpetas de solicitud inexistentes; servir la UI ya no necesita crear salidas |
| `rechaza_nombre_archivo_invalido` | API: nulo, vacío, ajeno y extensión incorrecta nunca entregan archivo |
| `error_http_con_detalle_estructurado` | SPA: 422 estructurado se convierte en mensaje legible |
| `respuesta_real_pipeline` | SPA y API aceptan `bom_csv`; prueba adicional de alias `csv` |
| `declinacion_real_http_422` | SSE distingue declinación de dominio de error 422 genérico; motivo y limpieza de descargas |
| `consultar_api_timeout_configurable` | SPA: timeout configurable aborta espera real; no simula avance ni asegura detención |

El aviso «Diseño preliminar: requiere revisión profesional» también se comprueba
en el montaje SPA, además de la marca del STEP en las pruebas de pipeline.

## Reproducción y clasificación de verificaciones

Tras instalar dependencias desde ambos lockfiles: `make check` ejecuta los mismos
objetivos que CI. El build precede a pytest, porque la prueba de integración
requiere assets reales y falla si falta el build.

```bash
uv run --no-sync python scripts/verify_hu15_deployment.py --simulate-model
```

Este smoke arranca Uvicorn y sirve la SPA real sin Vite. Solo traductor y modelo
se sustituyen explícitamente: API, CORS, SSE, pipeline CAD, exportación, archivos
y red HTTP son reales. Comprueba raíz/assets, errores JSON, cabeceras y entrega
incremental mientras una operación simulada sigue bloqueada, cancelación 202
seguida de terminal local y desconexión seguida de consulta. Descarga STEP/GLB/CSV
y verifica cabecera binaria GLB. **No prueba Docker ni inferencia real.**

Las pruebas Vitest usan FastAPI/WebGL simulados identificados en `frontend/tests/`;
las pruebas Python no llaman al proveedor real. Las comprobaciones anteriores de
Chrome a 1280/768 y teclado están descritas en `frontend/README.md`.

## Bloqueos de entorno observados

- **Docker, bloqueo inicial resuelto:** tras abrir Docker Desktop, Engine 29.9.2
  responde con contenedores Linux. Build de la aplicación, FastAPI/Vue y smoke
  SSE/CAD en Compose aislado comprobados; véase [evidencia Docker](hu15-docker-validation.md).
  No se probaron arranque completo con llama/GPU ni volúmenes de producción.
- **Instalación limpia Windows bloqueada:** `uv lock` se regeneró y `uv lock --check`
  es válido; `uv sync --locked --dev` falla compilando `python-solvespace==3.0.8`
  por ausencia de Microsoft Visual C++ 14+. No se omite ese paquete del lockfile
  ni se presenta esa instalación como correcta. Las pruebas locales usan el
  entorno Python CAD previamente disponible. CI/Docker declaran toolchain Linux,
  pero su build no se considera probado por las pruebas nativas.
- **Inferencia real pendiente:** no se llamó a Gemini ni a llama.cpp con pesos/GPU.
  La cancelación del proveedor remoto sigue sin confirmación de extremo a extremo.

## Resultados ejecutados

| Verificación | Resultado observado |
| --- | --- |
| npm ci y lockfile frontend | Correctos |
| Vitest | 39 casos aprobados; servicios de prueba identificados como simulados |
| TypeScript y build | Correctos; visor Three.js diferido, aprox. 161 kB gzip |
| Pytest | 231 casos aprobados en el entorno CAD existente |
| Cobertura Python | 95.90 %, superior al 95.33 % anterior a esta integración; `web.py` 100 % |
| Ruff | Limpio en `src`, `tests` y el script de smoke nuevo |
| uv lock --check | Correcto; Gradio y dependencias exclusivas retirados del lockfile |
| Compose base y remoto | Configuración válida; servicios base `llama`/`m2-cad`, remoto solo `m2-cad` |
| Arranque integrado nativo HTTP | Correcto; FastAPI sirve build, API y archivos sin Vite |
| SSE nativo por red | Incremental, sin compresión; DELETE devuelve 202 mientras el modelo simulado aún bloquea |
| Archivos generados reales | STEP 12446 bytes, GLB 32496 bytes, CSV 77 bytes; GET/HEAD correctos |
| Chrome, mismo origen FastAPI | 1280/768 sin desbordamientos; teclado/foco/visor y descargas reales correctos |
| Docker build/arranque aislado | Correctos; FastAPI/Vue y smoke SSE con CAD real dentro de Linux; traductor/modelo simulados. Véase evidencia Docker |
| Compose completo con modelo y CI remota | Pendientes; sin arranque llama/GPU, sin push ni ejecución remota de CI |
| Instalación limpia Windows | Bloqueada por compilador MSVC ausente; no se confunde con las pruebas del entorno existente |
| Inferencia real | No ejecutada; traductor/modelo simulados, CAD/exportación y transporte reales |

El descenso del número de tests Python refleja la retirada de los 23 casos UI
anteriores, migrados a SPA/API, y la incorporación de pruebas de despliegue y
seguridad de rutas. No se redujo el umbral de cobertura ni se excluyeron módulos
para hacer pasar la medición. La configuración de CI reproduce estos controles,
pero no se afirma que una ejecución remota haya pasado.
