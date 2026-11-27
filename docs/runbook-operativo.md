# Runbook operativo

Este documento describe incidentes previsibles del servicio y su respuesta. Complementa la
puesta en marcha de [HU-15/despliegue](hu15-despliegue.md), el
[despliegue en la nube](runbook-cloud.md) y el [README](../README.md). Cada escenario tiene
síntoma, diagnóstico, acción, verificación de recuperación y escalado. Si un comando muestra
una clave, una URL privada o un token, detén la ejecución y escala: el servicio está diseñado
para no hacerlo.

Convenciones:

- Ejecutar los comandos desde la raíz del repositorio. Los bloques `bash` están listos para
  Git Bash; en Windows PowerShell usar `curl.exe` donde se indica `curl`.
- `docker compose` interpola `M2_DOWNLOAD_SECRET` y, con la autenticación activa (HU-53, por
  defecto), `M2_AUTH_SECRET` y `M2_AUTH_USERS` (`docker-compose.yml`); en operación deben
  existir en `.env` y no mostrarse. Si faltan o son inválidos, la API no arranca. No escribir
  secretos reales en la línea de comandos.
- Hay dos servicios de aplicación con la misma imagen: `m2-cad` (API y SPA) y
  `m2-cad-worker`, que ejecuta las generaciones SSE de la SPA desde la cola `data/cola.json`
  (HU-45). La clave, el modelo y la imagen afectan a ambos: se diagnostican y se recrean
  juntos.
- Después de cualquier `docker compose up -d --force-recreate m2-cad m2-cad-worker`, comprobar
  el worker. Al detenerse, el worker anterior marca la cola como cerrada y sólo el arranque
  de `m2-cad` la reabre; si el worker nuevo arranca antes, termina con `Exited (0)` y el log
  `worker: 0 trabajos procesados`. Con `m2-cad` ya `healthy`, levantarlo de nuevo:

  ```bash
  docker compose ps -a m2-cad-worker
  docker compose up -d m2-cad-worker
  ```

  No reiniciar sólo el worker (`docker compose restart m2-cad-worker`): deja la cola cerrada
  y la API rechaza las generaciones SSE hasta que se recrea `m2-cad`.
- Los comandos de diagnóstico no piden la clave ni llaman al modelo, salvo que se diga
  explícitamente «gasta tokens».
- `m2-cad` publica `127.0.0.1:8000`. La API pública es `/v1` (HU-31): `/v1/health` es vida del
  proceso; `/v1/ready` es disponibilidad local de modelo y registro, sin consultar al
  proveedor. Ambas responden sin sesión. Las rutas planas (`/health`, `/ready`) sólo
  redirigen con `307` hasta su retiro y no sirven para diagnosticar.
- Los respaldos se guardan en `data/backups/`, que dentro del contenedor es
  `/app/data/backups/` (volumen `./data`): sobreviven a `--force-recreate`. Está ignorado por
  Git; no versionarlos ni pegarlos en un ticket. Respaldo rutinario:

  ```bash
  docker compose exec -T m2-cad sh -c 'MARCA=$(date +%Y%m%d-%H%M%S); mkdir -p /app/data/backups; uv run --no-sync python -m m2_cad.persistencia_registro backup --registro data/registro.csv --destino data/backups/registro-$MARCA.csv; tar -czf /app/data/backups/outputs-$MARCA.tar.gz -C /app outputs && echo "outputs: outputs-$MARCA.tar.gz"'
  ```

  Cada respaldo lleva fecha y hora (`AAAAMMDD-HHMMSS`), así nunca pisa uno anterior: la CLI
  del registro se niega a sobrescribir (`El backup ya existe`). Los dos pasos son
  independientes: si el registro todavía no existe, su paso informa el error y el de
  `outputs/` se hace igual.

- La prueba de humo (`scripts/smoke_deploy.py`) inicia sesión cuando la API la exige. Define
  el usuario y lee la clave sin eco, así no queda en el historial:

  ```bash
  export M2_SMOKE_USUARIO=operador
  read -rs M2_SMOKE_CLAVE && export M2_SMOKE_CLAVE
  ```

  Al terminar, `unset M2_SMOKE_CLAVE`. Sin credenciales válidas termina con código 2 antes de
  generar, sin gastar tokens. El humo
  usa `POST /v1/generar` en JSON, que corre en `m2-cad`; las generaciones de la SPA (SSE)
  corren en `m2-cad-worker`, cuyos logs se revisan aparte.
- Un HTTP 422 con `Pieza declinada:` no es un incidente: es una declinación válida del catálogo.
  Sí lo es un 422 con un mensaje de validación de la salida del modelo (por ejemplo `La salida
  del modelo no contiene un programa JSON.`). Las clases `ErrorGeneracion` /
  `ErrorVerificacion` sólo figuran en MLflow; la respuesta y los logs muestran el mensaje.
- Códigos de la propia API que no vienen del proveedor: `401` con `Inicia sesión para
  continuar.` es falta de sesión (HU-53); `429` con cabecera `X-Limite-Tipo: ventana` o
  `presupuesto` es un tope local de uso (HU-32); `429` en `POST /v1/auth/login` es el límite
  de intentos fallidos. Ninguno se resuelve rotando la clave del proveedor.

## Modelo caído o sin respuesta

### Síntoma

- La SPA muestra `El servicio no está disponible. Vuelve a intentarlo.` o, en SSE,
  `No se pudo completar la solicitud. Vuelve a intentarlo.` / `Se perdió la conexión.`
  (`frontend/src/useGeneration.ts`).
- Una generación JSON devuelve HTTP 503 con el motivo concreto, por ejemplo `El modelo no está
  configurado: falta DEEPSEEK_API_KEY.`, `No fue posible conectar con el modelo.` o `El modelo
  no respondió dentro del plazo total de 120 s.` En SSE el evento terminal `error` muestra el
  texto genérico `El servicio de generación no está disponible.` (`src/m2_cad/api.py`).
- `docker compose ps` no muestra `m2-cad` como `Up (healthy)`, o `/v1/health` no devuelve
  HTTP 200.
- Las generaciones de la SPA se quedan en la primera etapa sin avanzar: `m2-cad-worker` no
  está levantado y los trabajos esperan en la cola.

No son este escenario: un rechazo del proveedor con HTTP 401 (clave), 402 (sin crédito) o 429
(límite del proveedor), ni un programa inválido. Esos se tratan en sus propias secciones. Los
401 y 429 de la propia API se explican en las convenciones.

### Diagnóstico

1. Confirmar que el contenedor existe y está levantado:

   ```bash
   docker compose ps
   ```

   Salida esperada en funcionamiento: fila `m2-cad` con `STATUS` `Up ... (healthy)` y `PORTS`
   `127.0.0.1:8000->8000/tcp`, y fila `m2-cad-worker` con `Up`. Si alguna no existe o dice
   `Exited`, es caída de la aplicación; sin `m2-cad-worker`, la API acepta generaciones SSE
   pero nadie las ejecuta. Un `m2-cad-worker` en `Exited (0)` tras recrear se recupera como
   indican las convenciones.

2. Comprobar la vida del proceso, sin modelo ni clave:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/health
   ```

   Salida esperada: `{"status":"ok"}` y `HTTP 200`. Si falla la conexión o el cuerpo no es ese
   JSON, es caída de la aplicación o el puerto está ocupado por otro proceso. No continuar con
   el proveedor hasta corregir el puerto.

3. Comprobar dependencias locales sin consultar al proveedor:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
   ```

   Salida esperada: `HTTP 200` con
   `{"status":"ok","dependencias":{"modelo":"ok","registro":"ok"}}`. Si devuelve `HTTP 503` con
   `"modelo":"no_disponible"`, la configuración local no tiene `DEEPSEEK_API_KEY`,
   `LLM_API_KEY` ni `LLM_BASE_URL`; es fallo de configuración, no de salud del proceso.

4. Verificar la presencia de la clave sin mostrarla:

   ```bash
   for S in m2-cad m2-cad-worker; do printf '%s: ' "$S"; docker compose exec -T "$S" uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"; done
   ```

   Salida esperada: `m2-cad: configurada` y `m2-cad-worker: configurada`. Un `ausente`
   confirma configuración incompleta en ese servicio. Este comando nunca imprime el valor.

5. Leer los mensajes ya redactados del proveedor:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
   ```

   Buscar `proveedor respondió HTTP 401/402/429`,
   `El modelo no respondió dentro del plazo total de 120 s.` o
   `No fue posible conectar con el modelo.` (`src/m2_cad/pipeline.py`). No copiar la clave al
   ticket: los logs redactan secretos (`src/m2_cad/observabilidad.py`).

### Acción

**A. Caída de la aplicación** (falla `docker compose ps` o `/v1/health`):

```bash
make up
```

`make up` ejecuta `docker compose up` en primer plano (`Makefile`). Para dejarlo en segundo
plano, usar:

```bash
docker compose up -d
```

Si el puerto está ocupado, liberarlo o ajustar el mapeo `127.0.0.1:8000:8000` en
`docker-compose.yml` según el README; no matar un proceso ajeno sin confirmarlo.

**B. Aplicación sana pero proveedor o configuración fallida** (`/v1/health` 200 y `/v1/ready` o logs
con problema de entrega/modelo):

- Si `/v1/ready` dice `modelo: no_disponible` o la clave está `ausente`: no escribir la clave en
  la línea de comandos (`echo` con la key queda en el historial). Ir a «Rotación de la clave
  DeepSeek» y escalar al responsable.
- Si los logs muestran `HTTP 401` o `HTTP 402`: no reintentar en bucle. Ir a «Rotación de la
  clave DeepSeek» o «Cuenta sin crédito»; escalar con `request_id` si está disponible.
- Si muestran `HTTP 429`: esperar y reintentar una sola vez; si vuelve, escalar por límite de
  solicitudes.
- Si muestran timeout, 5xx o fallo de conexión tras los reintentos automáticos (2 adicionales,
  plazo total de 120 s; README y `src/m2_cad/llm_resiliente.py`), verificar conectividad de
  salida y escalar como incidente del proveedor.

### Verificación de recuperación

1. Aplicación:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/health
   docker compose ps
   ```

   Esperado: `HTTP 200` con `{"status":"ok"}`, `m2-cad` `Up (healthy)` y `m2-cad-worker` `Up`.

2. Configuración local, sin llamar al modelo:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
   ```

   Esperado: `HTTP 200` con `modelo: ok` y `registro: ok`.

3. Proveedor, solo con autorización; **gasta tokens**:

   ```bash
   uv run python scripts/smoke_deploy.py --n 1
   ```

   Esperado: línea `[1/1] ... pieza (200)` o `declinada (422)` con motivo; `resultado` distinto
   de `error` y resumen `Válidas 1/1`. Un `error` con 503 confirma que el proveedor sigue caído.

### Escalado

Escalar al responsable de la HU u operador senior si:

- `/v1/health` sigue sin responder después de `make up`, o `docker compose ps` muestra reinicios.
- `/v1/ready` mantiene `modelo: no_disponible` y la rotación de clave no está autorizada.
- Aparece 401, 402 o 429 repetido, o timeout/5xx después de los reintentos automáticos.
- El puerto 8000 responde con un cuerpo ajeno, por ejemplo
  `{"status":"ok","service":"mantenimientos"}`.

Incluir en el escalado: hora, `request_id` visible en logs o respuesta, último mensaje
redactado y resultados de `/v1/health` y `/v1/ready`. Nunca incluir la API key.

## Cuenta sin crédito

### Síntoma

- `POST /v1/generar` devuelve HTTP 503 con `La cuenta de DeepSeek no tiene saldo suficiente
  (HTTP 402).` En SSE el evento terminal es `error` con el texto genérico
  `El servicio de generación no está disponible.`
- Los logs contienen `proveedor respondió HTTP 402: ...` (`src/m2_cad/pipeline.py`).
- `/v1/health` sigue en 200: la cuenta no afecta a la vida del proceso.

### Diagnóstico

1. Confirmar que el fallo es de proveedor y no de configuración local:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/health
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
   ```

2. Confirmar que la clave existe, sin imprimirla:

   ```bash
   for S in m2-cad m2-cad-worker; do printf '%s: ' "$S"; docker compose exec -T "$S" uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"; done
   ```

3. Buscar el código original en los logs redactados:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
   ```

4. Reproducir con una sola solicitud; **gasta tokens** si la cuenta aún tiene saldo:

   ```bash
   uv run python scripts/smoke_deploy.py --n 1
   ```

### Acción

1. No reintentar en bucle: el sistema no reintenta HTTP 402
   (`src/m2_cad/llm_resiliente.py`) y cada intento con saldo consumiría tokens.
2. Solicitar la recarga o el cambio de plan al responsable de la cuenta DeepSeek. No poner la
   clave ni datos de facturación en `.env`, logs ni tickets.
3. Confirmada la recarga, recrear el contenedor para descartar estado local:

   ```bash
   docker compose up -d --force-recreate m2-cad m2-cad-worker
   ```

### Verificación de recuperación

```bash
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/health
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `/v1/health` 200 y el humo con `pieza` o `declinada`, nunca `error` ni HTTP 402.

### Escalado

Escalar si el 402 persiste después de confirmar la recarga, o si aparece junto con 401/429.
Incluir hora, `request_id` y el mensaje redactado. Nunca incluir la clave ni datos de pago.

## Respuesta inválida del modelo

### Síntoma

- `POST /v1/generar` devuelve HTTP 422 con `La salida del modelo no contiene un programa JSON.`,
  `Respuesta del modelo sin contenido.`, `Respuesta del modelo sin contenido de texto.` u otro
  mensaje de validación del programa o de la verificación geométrica.
- En SSE, el evento terminal es `error` con ese mismo detalle antes de construir la pieza.
- Los logs muestran `generación terminada en error`. Si el modelo respondió prosa, no aparece
  `pipeline: programa generado`: la salida se valida al recibirla, antes de ese mensaje.

No es este escenario un HTTP 422 con `Pieza declinada: ...`: esa respuesta es una declinación
correcta del catálogo (`frontend/src/useGeneration.ts`).

### Diagnóstico

1. Verificar que la API está viva y que el modelo está configurado:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/health
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
   ```

2. Leer el error exacto y el `request_id`:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
   ```

3. Revisar los últimos programas guardados; cada respuesta válida escribe `programa.json`:

   ```bash
   docker compose exec -T m2-cad sh -c 'ls -1t /app/outputs/*/programa.json 2>/dev/null | head -n 3'
   ```

4. Reproducir una vez; **gasta tokens**:

   ```bash
   uv run python scripts/smoke_deploy.py --n 1
   ```

Las respuestas inválidas **no** entran en la caché: el validador se ejecuta antes de guardar
(`src/m2_cad/llm_resiliente.py`). No hace falta limpiar caché.

### Acción

1. Reintentar una sola vez tras 60 s para descartar una respuesta transitoria:

   ```bash
   sleep 60; uv run python scripts/smoke_deploy.py --n 1
   ```

   En PowerShell: `Start-Sleep -Seconds 60; uv run python scripts/smoke_deploy.py --n 1`.

2. Si vuelve a fallar, volver a la versión de modelo conocida según «Rollback de la versión de
   modelo» y recrear:

   ```bash
   docker compose up -d --force-recreate m2-cad m2-cad-worker
   ```

3. Si el fallo empezó tras un cambio de imagen, aplicar «Rollback de la imagen del servicio».

### Verificación de recuperación

```bash
docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: el humo termina en `pieza` o en `declinada` con motivo, nunca en `error`, y en los
logs no aparecen nuevas líneas `generación terminada en error` ni los mensajes del síntoma.

### Escalado

Escalar con el mensaje exacto, `request_id`, versión devuelta por el proveedor y los últimos
`programa.json`. No pegar el contenido completo si incluye texto del usuario.

## Rotación de la clave DeepSeek

### Síntoma

- `POST /v1/generar` devuelve HTTP 503 con `DeepSeek rechazó la API key (HTTP 401). Revisa
  DEEPSEEK_API_KEY.`
- Los logs muestran `proveedor respondió HTTP 401: ...` redactado.
- La clave anterior quedó expuesta, venció o debe revocarse por política.

### Diagnóstico

1. Comprobar presencia actual, sin imprimir el valor:

   ```bash
   for S in m2-cad m2-cad-worker; do printf '%s: ' "$S"; docker compose exec -T "$S" uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"; done
   ```

2. Leer los mensajes del proveedor:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
   ```

3. Confirmar que no hay secretos en los logs:

   ```bash
   N=$(docker compose logs --no-color --tail=200 m2-cad m2-cad-worker | grep -c -i -E 'sk-|authorization|api[_-]?key'); [ "$N" -eq 0 ] && echo SIN_SECRETOS_EN_LOGS || echo "REVISAR: $N lineas sospechosas (no se muestran)"
   ```

### Acción

1. Revocar la clave anterior en el proveedor y generar una nueva. No pegarla en chat, ticket,
   terminal compartida ni `.env` versionado.
2. Actualizar `DEEPSEEK_API_KEY` en `.env` con un editor local. No usar `echo "DEEPSEEK_API_KEY=..." > .env`:
   el valor queda en el historial de la shell.
3. Recrear el contenedor para que Compose inyecte la nueva clave:

   ```bash
   docker compose up -d --force-recreate m2-cad m2-cad-worker
   ```

### Verificación de recuperación

```bash
for S in m2-cad m2-cad-worker; do printf '%s: ' "$S"; docker compose exec -T "$S" uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"; done
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
N=$(docker compose logs --no-color --tail=200 m2-cad m2-cad-worker | grep -c -i -E 'sk-|authorization|api[_-]?key'); [ "$N" -eq 0 ] && echo SIN_SECRETOS_EN_LOGS || echo "REVISAR: $N lineas sospechosas (no se muestran)"
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `configurada` en ambos servicios, `/v1/ready` 200, `SIN_SECRETOS_EN_LOGS` y humo
sin `error`.

### Escalado

Escalar al responsable de credenciales si el 401 persiste tras la rotación o si aparece cualquier
secreto en logs. Incluir solo hora y `request_id`; nunca la clave antigua ni la nueva.

## Rollback de la versión de modelo

### Síntoma

- Tras cambiar `LLM_MODEL`, aumentan las declinaciones, cambia el formato de salida o el
  campo `version` del registro deja de ser el esperado.
- El proveedor publicó una versión nueva incompatible con el prompt del catálogo cerrado.

### Diagnóstico

1. Leer la configuración efectiva dentro del contenedor, sin secretos:

   ```bash
   for S in m2-cad m2-cad-worker; do echo "== $S"; docker compose exec -T "$S" uv run --no-sync python -c "import os; print('LLM_MODEL=' + (os.getenv('LLM_MODEL') or 'no-fijado')); print('LLM_MODEL_VERSION=' + (os.getenv('LLM_MODEL_VERSION') or 'no-fijado'))"; done
   ```

   `LLM_MODEL_VERSION=no-fijado` es esperable: `docker-compose.yml` no interpola esa variable;
   el código la usa solo si el proceso la recibe (`src/m2_cad/seguimiento.py`).

2. Comparar con la versión que figura en los logs y en `data/registro.csv`:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
   docker compose exec -T m2-cad sh -c 'tail -n 5 /app/data/registro.csv'
   ```

### Acción

1. Fijar en `.env` la versión conocida, por ejemplo `LLM_MODEL=deepseek-v4-pro`. No tocar la
   clave. Recrear el contenedor:

   ```bash
   docker compose up -d --force-recreate m2-cad m2-cad-worker
   ```

2. Si el servicio corre sin Docker (README, «Instalación y uso»), levantarlo con la variable
   explícita:

   ```bash
   LLM_MODEL=deepseek-v4-pro uv run uvicorn m2_cad.api:app --app-dir src --host 127.0.0.1 --port 8000 --workers 1
   ```

   y, en otra terminal, el worker con la misma variable:

   ```bash
   LLM_MODEL=deepseek-v4-pro uv run python -m m2_cad.worker
   ```

3. Para forzar `LLM_MODEL_VERSION` en Docker hace falta añadir
   `LLM_MODEL_VERSION: ${LLM_MODEL_VERSION:-}` a los servicios `m2-cad` y `m2-cad-worker` de
   `docker-compose.yml` o usar un override; no se logra editando solo `.env`.

### Verificación de recuperación

```bash
for S in m2-cad m2-cad-worker; do echo "== $S"; docker compose exec -T "$S" uv run --no-sync python -c "import os; print('LLM_MODEL=' + (os.getenv('LLM_MODEL') or 'no-fijado')); print('LLM_MODEL_VERSION=' + (os.getenv('LLM_MODEL_VERSION') or 'no-fijado'))"; done
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `LLM_MODEL` con el valor conocido en ambos servicios, `/v1/ready` 200 y humo sin
`error`.

### Escalado

Escalar si el modelo conocido también falla, o si el proveedor cambió el contrato sin aviso.
Incluir modelo anterior y nuevo, `request_id` y ejemplos de salida sanitizada.

## Rollback de la imagen del servicio

### Síntoma

- Después de `make build` o un cambio de `Dockerfile`, el contenedor no pasa el healthcheck,
  reinicia o la SPA/API deja de responder.
- `docker compose ps` muestra `Exited`, `Restarting` o `Up (unhealthy)` para `m2-cad` o
  `m2-cad-worker`.

### Diagnóstico

1. Identificar la imagen que Compose está usando y su estado:

   ```bash
   docker compose config --images
   docker compose images m2-cad m2-cad-worker
   docker compose ps
   ```

   Compose construye una imagen por servicio con el mismo `Dockerfile`; sus nombres terminan
   en `-m2-cad` y `-m2-cad-worker`. Las dos deben volver juntas a la versión buena.

2. Leer el motivo del fallo:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
   ```

### Acción

1. Si aún no se hizo, etiquetar las imágenes buenas antes de reconstruir (comando en Git Bash):

   ```bash
   ( set -e; for S in m2-cad m2-cad-worker; do IMAGEN=$(docker compose config --images | grep -x -- ".*-$S"); SIN_TAG="${IMAGEN%:*}"; docker tag "$IMAGEN" "${SIN_TAG}:ultima-buena"; echo "etiquetada: ${SIN_TAG}:ultima-buena"; done )
   ```

2. Volver a las etiquetas buenas y recrear los contenedores:

   ```bash
   ( set -e; for S in m2-cad m2-cad-worker; do IMAGEN=$(docker compose config --images | grep -x -- ".*-$S"); SIN_TAG="${IMAGEN%:*}"; docker tag "${SIN_TAG}:ultima-buena" "$IMAGEN"; done; docker compose up -d --force-recreate m2-cad m2-cad-worker )
   ```

   `set -e` detiene todo si falta una imagen o una etiqueta: no se recrea nada a medias.

3. Si no existe `ultima-buena`, reconstruir desde el commit anterior conocido con
   `make build` y repetir la verificación. No borrar volúmenes `data/` ni `outputs/`: el
   rollback es de código, no de datos.

### Verificación de recuperación

```bash
docker compose ps
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/health
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `m2-cad` `Up (healthy)`, `m2-cad-worker` `Up`, `/v1/health` 200, `/v1/ready` 200 y
humo sin `error`.

### Escalado

Escalar si no hay imagen buena etiquetada o si el rollback no restaura el healthcheck.
Incluir `docker compose images m2-cad m2-cad-worker`, el último mensaje de logs y el commit
implicado.

## Restauración de `data/registro.csv`

### Síntoma

- `/v1/ready` devuelve `HTTP 503` con `"registro":"no_disponible"`.
- `data/registro.csv` fue borrado, truncado, reemplazado por una cabecera equivocada o quedó con
  filas incompletas.
- La CLI responde `La cabecera del registro no coincide con CAMPOS.` o `Registro CSV incompleto.`

### Diagnóstico

1. Comprobar si el archivo existe y leer su cabecera:

   ```bash
   docker compose exec -T m2-cad sh -c 'test -f /app/data/registro.csv && echo presente || echo ausente'
   docker compose exec -T m2-cad sh -c 'head -n 1 /app/data/registro.csv 2>/dev/null || echo SIN_CABECERA'
   ```

2. Listar respaldos disponibles:

   ```bash
   docker compose exec -T m2-cad sh -c 'cd /app/data/backups 2>/dev/null && ls -1 registro-*.csv 2>/dev/null || echo SIN_BACKUPS'
   ```

3. Comprobar disponibilidad local:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
   ```

### Acción

1. Tomar un snapshot del estado actual antes de restaurar; si no hay archivo, el comando avisa
   y se continúa con el respaldo:

   ```bash
   docker compose exec -T m2-cad sh -c 'MARCA=$(date +%Y%m%d-%H%M%S); mkdir -p /app/data/backups; uv run --no-sync python -m m2_cad.persistencia_registro backup --registro data/registro.csv --destino data/backups/registro-pre-restore-$MARCA.csv'
   ```

2. Restaurar el respaldo elegido, con reemplazo atómico y validación de cabecera. `ARCHIVO` es
   uno de los nombres que listó el diagnóstico:

   ```bash
   docker compose exec -T -e ARCHIVO=registro-AAAAMMDD-HHMMSS.csv m2-cad sh -c 'uv run --no-sync python -m m2_cad.persistencia_registro restore --registro data/registro.csv --origen "data/backups/$ARCHIVO"'
   ```

3. Si la restauración falla por cabecera, no editar el CSV a mano: escalar con el primer renglón
   leído y elegir otro respaldo. Un respaldo anterior a HU-53 tiene 8 columnas (sin `usuario`)
   y no pasa la validación de `restore`; escalarlo en lugar de forzarlo.

### Verificación de recuperación

```bash
docker compose exec -T m2-cad sh -c 'head -n 1 /app/data/registro.csv'
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/ready
```

Esperado: cabecera
`id,hora,texto,traduccion,resultado,latencia_ms,error,version,usuario` y `/v1/ready` 200 con
`"registro":"ok"`.

### Escalado

Escalar si no hay respaldo válido, si la restauración rompe la cabecera o si `/v1/ready` sigue en
503. Incluir el nombre del respaldo y el mensaje de error de la CLI; nunca pegar el CSV completo
si contiene texto de solicitudes.

## Restauración de `outputs/`

### Síntoma

- Faltan carpetas `outputs/<uuid>/` o sus entregables `programa.json`, `.step`, `.glb` y `.csv`.
- Una generación terminó en `entregada` pero las descargas devuelven 404 a su dueño.
- Se borró o sobrescribió `outputs/` por error durante mantenimiento.

### Diagnóstico

1. Listar artefactos presentes y respaldos disponibles:

   ```bash
   docker compose exec -T m2-cad sh -c 'find /app/outputs -maxdepth 2 -type f | head -n 20; cd /app/data/backups 2>/dev/null && ls -1 outputs-*.tar.gz 2>/dev/null || echo SIN_BACKUPS'
   ```

2. Confirmar que el fallo no es de descarga con token ni de propiedad: un 403 es un token de
   descarga inválido o ausente y un 410, un token caducado (HU-36); un 404 también aparece si
   la generación pertenece a otro usuario (HU-53). Leer los logs buscando 403/404 y `request_id`:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad m2-cad-worker
   ```

### Acción

1. Tomar snapshot de `outputs/` antes de tocar nada:

   ```bash
   docker compose exec -T m2-cad sh -c 'MARCA=$(date +%Y%m%d-%H%M%S); mkdir -p /app/data/backups; tar -czf /app/data/backups/outputs-pre-restore-$MARCA.tar.gz -C /app outputs && echo "snapshot: outputs-pre-restore-$MARCA.tar.gz"'
   ```

2. Restaurar los archivos del respaldo elegido sobre `outputs/`; `ARCHIVO` es uno de los nombres
   que listó el diagnóstico:

   ```bash
   docker compose exec -T -e ARCHIVO=outputs-AAAAMMDD-HHMMSS.tar.gz m2-cad sh -c 'tar -xzf "/app/data/backups/$ARCHIVO" -C /app'
   ```

   `/app/outputs` es un volumen montado: no se puede mover ni renombrar desde el contenedor
   (`Device or resource busy`). La extracción repone los archivos faltantes o dañados y
   conserva los demás; el snapshot del paso 1 permite volver atrás.

### Verificación de recuperación

```bash
docker compose exec -T m2-cad sh -c 'find /app/outputs -maxdepth 2 -type f | head -n 20'
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/v1/health
```

Esperado: reaparecen los archivos del respaldo y `/v1/health` sigue en 200. Para confirmar una
descarga concreto, repetir el humo con autorización; **gasta tokens**:

```bash
uv run python scripts/smoke_deploy.py --n 1
```

### Escalado

Escalar si no hay respaldo, si el tar está corrupto o si las descargas siguen fallando tras la
restauración. Incluir nombre del respaldo, cantidad de archivos listados y `request_id` de la
descarga fallida.
