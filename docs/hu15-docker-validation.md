# HU-15 · Validación Docker aislada, 2026-11-13

> Evidencia histórica anterior a integrar HU-14. El contrato actual elimina la
> traducción; resultados posteriores en [integración HU-14](hu15-integracion-hu14.md).

## Resultado y alcance

Imagen construida desde el Dockerfile multietapa y los lockfiles de `7bce006`,
sin cambios en código de aplicación, Dockerfile ni arranque normal. Docker Engine
29.9.2 / Compose 5.6.1, Linux amd64 sobre Docker Desktop/WSL 2.

Imagen local: `hu15-validation-m2-cad:latest`.
ID observado: `sha256:c7ed717fd03963b88863dda20abb8997cb458072046e14acae0433df9cdc68a5`.

Se validó la sintaxis de Compose base, remoto y de prueba. Solo se construyó la
aplicación. No se arrancó llama.cpp ni se descargaron pesos ni se utilizaron
proveedores de pago. El build instaló las dependencias fijadas, incluida la
biblioteca `llama-cpp-python`; esto no ejecuta un servidor ni inferencia.

## Configuración y reproducción

`docker-compose.hu15-validation.yml` se selecciona explícitamente: no es un
override automático. Proyecto exclusivo `hu15-validation`, sin `depends_on`,
sin credenciales heredadas y sin montajes sobre `data/` u `outputs/` del host.
`web` ejecuta el CMD original, sin simulaciones, y publica solo loopback 18015.
`smoke`, perfil `verification`, usa la misma imagen y el script existente montado
en solo lectura; su red es interna, sin acceso a proveedores. No requiere otros
servicios. El script inicia un Uvicorn propio en loopback dentro del contenedor,
lo comprueba por HTTP y lo termina, con salidas CAD en un directorio temporal.

```powershell
docker compose -p hu15-validation config --quiet
docker compose -f docker-compose.gpu-remote.yml config --quiet
docker compose -p hu15-validation build m2-cad
docker compose -p hu15-validation -f docker-compose.hu15-validation.yml config --quiet
docker compose -p hu15-validation -f docker-compose.hu15-validation.yml up -d --no-deps --wait --wait-timeout 90 web
docker compose -p hu15-validation -f docker-compose.hu15-validation.yml run --rm --no-deps smoke
docker compose -p hu15-validation -f docker-compose.hu15-validation.yml --profile verification down
```

El último comando no lleva `--volumes` y solo afecta al proyecto de validación.
No se crearon volúmenes en este Compose; los existentes se conservan.

## Comprobaciones ejecutadas

### Arranque normal: sin dobles

Contenedor `web` saludable con el healthcheck de la imagen. Cliente HTTP real desde
Windows a `http://127.0.0.1:18015`, sin proxy:

| Recurso / acción | Resultado comprobado |
| --- | --- |
| `GET /health` | 200, JSON `{"status":"ok"}` |
| `GET /` | 200, HTML Vue con `div#app` |
| `/assets/index-DRPrKn61.js` | 200, JavaScript, 82700 bytes |
| `/assets/index-BAhN6r_W.css` | 200, CSS, 6146 bytes |
| `/assets/GlbViewer-BgYchP2c.js` | 200, JavaScript diferido, 644339 bytes |
| `GET /api/no-existe` | 404 JSON |
| `GET /generar` | 405 JSON |
| `POST /generar`, texto vacío | 422 JSON |
| `POST /generar`, texto válido sin proveedor configurado | 503 JSON, sin llamada remota |
| `GET /generaciones/desconocido` | 404 JSON |
| `GET /generaciones/desconocido/archivos/step` | 404 JSON |
| `GET /assets/no-existe.js` | 404 JSON |

Se comprobaron estado y tipo de contenido; ninguno de los errores devolvió HTML.
Los estáticos devolvieron bytes y tipos correspondientes, sin fallback HTML.
No se ejecutó un navegador en esta validación Docker; servir Vue no demuestra
por sí solo renderizado WebGL ni accesibilidad.

### Smoke dentro de la imagen: dobles explícitos y CAD real

Salida del comando `run --rm --no-deps smoke`, código 0:

```json
{
  "servicios": "traductor y modelo SIMULADOS",
  "archivos_bytes": {"step": 12150, "glb": 32496, "csv": 77},
  "arranque_nativo": "OK",
  "sse_incremental": "OK",
  "cancelacion_local": "OK"
}
```

`arranque_nativo` es el nombre heredado del campo del script: en esta ejecución
el proceso comprobado vive **dentro del contenedor Linux**, no en el host.

Comprobaciones reales del script:

- FastAPI sirve índice Vue y assets construidos, `/health` y errores API JSON.
- SSE entrega `validando → generando → verificado`, CORS de origen exacto,
  `X-Accel-Buffering: no`, `no-transform` y ausencia de compresión.
- Entrega incremental comprobada mientras la planificación simulada bloquea:
  DELETE devuelve 202 no terminal antes de la salida cooperativa local.
- Terminal `cancelado` con `pipeline_detenido: true` y confirmación remota falsa.
- Desconexión de SSE seguida de consulta GET alcanza cancelación local.
- Declinación y error de proveedor simulado generan sus terminales distintos;
  el mensaje público no expone la dirección del proveedor de prueba.
- Pipeline CAD, construcción, verificación geométrica y exportación reales;
  GET y HEAD correctos para STEP, GLB y CSV. GLB contiene la cabecera `glTF`.

Únicamente traducción y planificación/modelo se sustituyen en el proceso smoke.
El arranque normal nunca importa ese script. No se confirma inferencia real ni
detención de un proveedor remoto; el alcance pendiente de AC3 se mantiene.

## Fallos observados y resolución

- Primer intento HTTP desde Windows: `WinError 10061`, aunque `web` estaba
  saludable. La primera configuración conectaba también `web` a una red
  `internal: true`; el puerto publicado no era accesible desde el host.
  Se corrigió solo el Compose de prueba: `web` usa una red bridge propia y
  `smoke` conserva la red interna. Se recreó `web` y todas las comprobaciones
  HTTP externas pasaron. No se cambió la aplicación para resolverlo.
- CadQuery emitió un `FutureWarning` por `save` obsoleto. No impidió exportación
  ni descargas. No se observó ningún fallo de build o del smoke CAD.

## Pendientes y cierre

Pendientes: CI remota, instalación limpia Windows con MSVC, inferencia real,
cancelación remota y arranque completo del Compose con GPU/modelo. Esta evidencia
prueba la imagen y el despliegue aislado de FastAPI/Vue, no esos escenarios.

Validación terminada: `web` detenido y eliminado; el smoke salió con código 0 y
se eliminó con `--rm`. `down` con el perfil `verification` retiró ambas redes
del proyecto; sin el perfil quedaba la red interna del smoke. Las consultas por
etiqueta de proyecto devolvieron cero contenedores y cero redes restantes. No se
borraron volúmenes; la imagen construida se conserva.

`git diff --check` pasó. Solo cambian el Compose aislado y estos documentos de
evidencia. HEAD sigue en `7bce006`; stash HU-07 presente y sin aplicar/eliminar.
No se hicieron commits ni push. No hubo correcciones de código que requirieran
volver a ejecutar las suites unitarias; se ejecutaron build, TypeScript y los
controles HTTP/SSE/CAD descritos arriba.
