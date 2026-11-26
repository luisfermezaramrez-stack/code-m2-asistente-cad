# Runbook operativo

Este documento describe incidentes previsibles del servicio y su respuesta. Complementa la
puesta en marcha de [HU-15/despliegue](hu15-despliegue.md) y el [README](../README.md). Cada
escenario tiene síntoma, diagnóstico, acción, verificación de recuperación y escalado. Si un
comando muestra una clave, una URL privada o un token, detén la ejecución y escala: el servicio
está diseñado para no hacerlo.

Convenciones:

- Ejecutar los comandos desde la raíz del repositorio. Los bloques `bash` están listos para
  Git Bash; en Windows PowerShell usar `curl.exe` donde se indica `curl`.
- `docker compose` interpola `M2_DOWNLOAD_SECRET` (`docker-compose.yml`); en operación debe
  existir en `.env` y no mostrarse. No escribir secretos reales en la línea de comandos.
- Los comandos de diagnóstico no piden la clave ni llaman al modelo, salvo que se diga
  explícitamente «gasta tokens».
- `m2-cad` publica `127.0.0.1:8000`. `/health` es vida del proceso; `/ready` es disponibilidad
  local de modelo y registro, sin consultar al proveedor.
- Los respaldos se guardan en `backups/` (ignorado por Git). No versionarlos ni pegarlos en un
  ticket.
- Un HTTP 422 con `Pieza declinada:` no es un incidente: es una declinación válida del catálogo.
  Sí lo es un 422 con `ErrorGeneracion` o `ErrorVerificacion`.

## Modelo caído o sin respuesta

### Síntoma

- La SPA muestra `El servicio no está disponible. Vuelve a intentarlo.` o, en SSE,
  `No se pudo completar la solicitud. Vuelve a intentarlo.` / `Se perdió la conexión.`
  (`frontend/src/useGeneration.ts`).
- Una generación JSON devuelve HTTP 503 con `El modelo no está configurado: falta
  DEEPSEEK_API_KEY.` o `El servicio de generación no está disponible.` (`src/m2_cad/api.py`).
- `docker compose ps` no muestra `m2-cad` como `Up (healthy)`, o `/health` no devuelve HTTP 200.

No son este escenario: HTTP 401 (clave rechazada), 402 (sin crédito), 429 (límite) ni un
programa inválido. Esos se tratan en sus propias secciones.

### Diagnóstico

1. Confirmar que el contenedor existe y está levantado:

   ```bash
   docker compose ps
   ```

   Salida esperada en funcionamiento: fila `m2-cad` con `STATUS` `Up ... (healthy)` y `PORTS`
   `127.0.0.1:8000->8000/tcp`. Si la fila no existe o dice `Exited`, es caída de la aplicación.

2. Comprobar la vida del proceso, sin modelo ni clave:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health
   ```

   Salida esperada: `{"status":"ok"}` y `HTTP 200`. Si falla la conexión o el cuerpo no es ese
   JSON, es caída de la aplicación o el puerto está ocupado por otro proceso. No continuar con
   el proveedor hasta corregir el puerto.

3. Comprobar dependencias locales sin consultar al proveedor:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
   ```

   Salida esperada: `HTTP 200` con
   `{"status":"ok","dependencias":{"modelo":"ok","registro":"ok"}}`. Si devuelve `HTTP 503` con
   `"modelo":"no_disponible"`, la configuración local no tiene `DEEPSEEK_API_KEY`,
   `LLM_API_KEY` ni `LLM_BASE_URL`; es fallo de configuración, no de salud del proceso.

4. Verificar la presencia de la clave sin mostrarla:

   ```bash
   docker compose exec -T m2-cad uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"
   ```

   Salida esperada: `configurada`. La salida `ausente` confirma configuración incompleta. Este
   comando nunca imprime el valor.

5. Leer los mensajes ya redactados del proveedor:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad
   ```

   Buscar `proveedor respondió HTTP 401/402/429`,
   `El modelo no respondió dentro del plazo total de 120 s.` o
   `No fue posible conectar con el modelo.` (`src/m2_cad/pipeline.py`). No copiar la clave al
   ticket: los logs redactan secretos (`src/m2_cad/observabilidad.py`).

### Acción

**A. Caída de la aplicación** (falla `docker compose ps` o `/health`):

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

**B. Aplicación sana pero proveedor o configuración fallida** (`/health` 200 y `/ready` o logs
con problema de entrega/modelo):

- Si `/ready` dice `modelo: no_disponible` o la clave está `ausente`: no escribir la clave en
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
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health
   docker compose ps
   ```

   Esperado: `HTTP 200` con `{"status":"ok"}` y `m2-cad` `Up (healthy)`.

2. Configuración local, sin llamar al modelo:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
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

- `/health` sigue sin responder después de `make up`, o `docker compose ps` muestra reinicios.
- `/ready` mantiene `modelo: no_disponible` y la rotación de clave no está autorizada.
- Aparece 401, 402 o 429 repetido, o timeout/5xx después de los reintentos automáticos.
- El puerto 8000 responde con un cuerpo ajeno, por ejemplo
  `{"status":"ok","service":"mantenimientos"}`.

Incluir en el escalado: hora, `request_id` visible en logs o respuesta, último mensaje
redactado y resultados de `/health` y `/ready`. Nunca incluir la API key.

## Cuenta sin crédito

### Síntoma

- `POST /generar` devuelve HTTP 503 con `La cuenta de DeepSeek no tiene saldo suficiente
  (HTTP 402).` En SSE el evento terminal es `error` con el texto genérico
  `El servicio de generación no está disponible.`
- Los logs contienen `proveedor respondió HTTP 402: ...` (`src/m2_cad/pipeline.py`).
- `/health` sigue en 200: la cuenta no afecta a la vida del proceso.

### Diagnóstico

1. Confirmar que el fallo es de proveedor y no de configuración local:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
   ```

2. Confirmar que la clave existe, sin imprimirla:

   ```bash
   docker compose exec -T m2-cad uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"
   ```

3. Buscar el código original en los logs redactados:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad
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
   docker compose up -d --force-recreate m2-cad
   ```

### Verificación de recuperación

```bash
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `/health` 200 y el humo con `pieza` o `declinada`, nunca `error` ni HTTP 402.

### Escalado

Escalar si el 402 persiste después de confirmar la recarga, o si aparece junto con 401/429.
Incluir hora, `request_id` y el mensaje redactado. Nunca incluir la clave ni datos de pago.

## Respuesta inválida del modelo

### Síntoma

- `POST /generar` devuelve HTTP 422 con `La salida del modelo no contiene un programa JSON.`,
  `Respuesta del modelo sin contenido.`, `Respuesta del modelo sin contenido de texto.` o un
  mensaje de validación del catálogo (`ErrorGeneracion` / `ErrorVerificacion`).
- En SSE, el evento terminal es `error` con ese mismo detalle antes de construir la pieza.
- Los logs muestran `pipeline: programa generado` seguido de un fallo de validación, o el
  proveedor devolvió texto/prosa en lugar de JSON.

No es este escenario un HTTP 422 con `Pieza declinada: ...`: esa respuesta es una declinación
correcta del catálogo (`frontend/src/useGeneration.ts`).

### Diagnóstico

1. Verificar que la API está viva y que el modelo está configurado:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
   ```

2. Leer el error exacto y el `request_id`:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad
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
   Start-Sleep -Seconds 60; uv run python scripts/smoke_deploy.py --n 1
   ```

   El bloque anterior es PowerShell; en Git Bash usar `sleep 60; uv run python
   scripts/smoke_deploy.py --n 1`.

2. Si vuelve a fallar, volver a la versión de modelo conocida según «Rollback de la versión de
   modelo» y recrear:

   ```bash
   docker compose up -d --force-recreate m2-cad
   ```

3. Si el fallo empezó tras un cambio de imagen, aplicar «Rollback de la imagen del servicio».

### Verificación de recuperación

```bash
docker compose logs --no-color --tail=200 m2-cad
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: sin `ErrorGeneracion` ni `ErrorVerificacion` recientes; el humo termina en `pieza` o
en `declinada` con motivo.

### Escalado

Escalar con el mensaje exacto, `request_id`, versión devuelta por el proveedor y los últimos
`programa.json`. No pegar el contenido completo si incluye texto del usuario.

## Rotación de la clave DeepSeek

### Síntoma

- `POST /generar` devuelve HTTP 503 con `DeepSeek rechazó la API key (HTTP 401). Revisa
  DEEPSEEK_API_KEY.`
- Los logs muestran `proveedor respondió HTTP 401: ...` redactado.
- La clave anterior quedó expuesta, venció o debe revocarse por política.

### Diagnóstico

1. Comprobar presencia actual, sin imprimir el valor:

   ```bash
   docker compose exec -T m2-cad uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"
   ```

2. Leer los mensajes del proveedor:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad
   ```

3. Confirmar que no hay secretos en los logs:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad | grep -i -E 'sk-|authorization|api[_-]?key' || echo SIN_SECRETOS_EN_LOGS
   ```

### Acción

1. Revocar la clave anterior en el proveedor y generar una nueva. No pegarla en chat, ticket,
   terminal compartida ni `.env` versionado.
2. Actualizar `DEEPSEEK_API_KEY` en `.env` con un editor local. No usar `echo "DEEPSEEK_API_KEY=..." > .env`:
   el valor queda en el historial de la shell.
3. Recrear el contenedor para que Compose inyecte la nueva clave:

   ```bash
   docker compose up -d --force-recreate m2-cad
   ```

### Verificación de recuperación

```bash
docker compose exec -T m2-cad uv run --no-sync python -c "import os; print('configurada' if os.getenv('DEEPSEEK_API_KEY') else 'ausente')"
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
docker compose logs --no-color --tail=200 m2-cad | grep -i -E 'sk-|authorization|api[_-]?key' || echo SIN_SECRETOS_EN_LOGS
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `configurada`, `/ready` 200, `SIN_SECRETOS_EN_LOGS` y humo sin `error`.

### Escalado

Escalar al responsable de credenciales si el 401 persiste tras la rotación o si aparece cualquier
secreto en logs. Incluir solo hora y `request_id`; nunca la clave antigua ni la nueva.

## Rollback de la versión de modelo

### Síntoma

- Tras cambiar `LLM_MODEL`, aumentan las declinaciones, cambia el formato de salida o el
  `version_modelo` del registro deja de ser el esperado.
- El proveedor publicó una versión nueva incompatible con el prompt del catálogo cerrado.

### Diagnóstico

1. Leer la configuración efectiva dentro del contenedor, sin secretos:

   ```bash
   docker compose exec -T m2-cad uv run --no-sync python -c "import os; print('LLM_MODEL=' + (os.getenv('LLM_MODEL') or 'no-fijado')); print('LLM_MODEL_VERSION=' + (os.getenv('LLM_MODEL_VERSION') or 'no-fijado'))"
   ```

   `LLM_MODEL_VERSION=no-fijado` es esperable: `docker-compose.yml` no interpola esa variable;
   el código la usa solo si el proceso la recibe (`src/m2_cad/seguimiento.py`).

2. Comparar con la versión que figura en los logs y en `data/registro.csv`:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad
   docker compose exec -T m2-cad sh -c 'tail -n 5 /app/data/registro.csv'
   ```

### Acción

1. Fijar en `.env` la versión conocida, por ejemplo `LLM_MODEL=deepseek-v4-pro`. No tocar la
   clave. Recrear el contenedor:

   ```bash
   docker compose up -d --force-recreate m2-cad
   ```

2. Si el servicio corre sin Docker (README, «Instalación y uso»), levantarlo con la variable
   explícita:

   ```bash
   LLM_MODEL=deepseek-v4-pro uv run uvicorn m2_cad.api:app --app-dir src --host 127.0.0.1 --port 8000 --workers 1
   ```

3. Para forzar `LLM_MODEL_VERSION` en Docker hace falta añadir
   `LLM_MODEL_VERSION: ${LLM_MODEL_VERSION:-}` al servicio `m2-cad` de `docker-compose.yml` o
   usar un override; no se logra editando solo `.env`.

### Verificación de recuperación

```bash
docker compose exec -T m2-cad uv run --no-sync python -c "import os; print('LLM_MODEL=' + (os.getenv('LLM_MODEL') or 'no-fijado')); print('LLM_MODEL_VERSION=' + (os.getenv('LLM_MODEL_VERSION') or 'no-fijado'))"
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `LLM_MODEL` con el valor conocido, `/ready` 200 y humo sin `error`.

### Escalado

Escalar si el modelo conocido también falla, o si el proveedor cambió el contrato sin aviso.
Incluir modelo anterior y nuevo, `request_id` y ejemplos de salida sanitizada.

## Rollback de la imagen del servicio

### Síntoma

- Después de `make build` o un cambio de `Dockerfile`, el contenedor no pasa el healthcheck,
  reinicia o la SPA/API deja de responder.
- `docker compose ps` muestra `Exited`, `Restarting` o `Up (unhealthy)` para `m2-cad`.

### Diagnóstico

1. Identificar la imagen que Compose está usando y su estado:

   ```bash
   IMAGEN=$(docker compose config --images | grep m2-cad | head -n 1); echo "$IMAGEN"
   docker compose images m2-cad
   docker compose ps
   ```

2. Leer el motivo del fallo:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad
   ```

### Acción

1. Si aún no se hizo, etiquetar la imagen buena antes de reconstruir (comando en Git Bash):

   ```bash
   IMAGEN=$(docker compose config --images | grep m2-cad | head -n 1); SIN_TAG="${IMAGEN%:*}"; docker tag "$IMAGEN" "${SIN_TAG}:ultima-buena"
   ```

2. Volver a la etiqueta buena y recrear el contenedor:

   ```bash
   IMAGEN=$(docker compose config --images | grep m2-cad | head -n 1); SIN_TAG="${IMAGEN%:*}"; docker tag "${SIN_TAG}:ultima-buena" "$IMAGEN"; docker compose up -d --force-recreate m2-cad
   ```

3. Si no existe `ultima-buena`, reconstruir desde el commit anterior conocido con
   `make build` y repetir la verificación. No borrar volúmenes `data/` ni `outputs/`: el
   rollback es de código, no de datos.

### Verificación de recuperación

```bash
docker compose ps
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
uv run python scripts/smoke_deploy.py --n 1
```

Esperado: `m2-cad` `Up (healthy)`, `/health` 200, `/ready` 200 y humo sin `error`.

### Escalado

Escalar si no hay imagen buena etiquetada o si el rollback no restaura el healthcheck.
Incluir `docker compose images m2-cad`, el último mensaje de logs y el commit implicado.

## Restauración de `data/registro.csv`

### Síntoma

- `/ready` devuelve `HTTP 503` con `"registro":"no_disponible"`.
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
   docker compose exec -T m2-cad sh -c 'ls -1 /app/backups/registro-*.csv 2>/dev/null || echo SIN_BACKUPS'
   ```

3. Comprobar disponibilidad local:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
   ```

### Acción

1. Tomar un snapshot del estado actual antes de restaurar; si no hay archivo, el comando avisa
   y se continúa con el respaldo:

   ```bash
   docker compose exec -T m2-cad sh -c 'FECHA=$(date +%Y%m%d); mkdir -p /app/backups; uv run --no-sync python -m m2_cad.persistencia_registro backup --registro data/registro.csv --destino backups/registro-pre-restore-$FECHA.csv'
   ```

2. Restaurar el respaldo elegido del mismo día, con reemplazo atómico y validación de cabecera:

   ```bash
   docker compose exec -T m2-cad sh -c 'FECHA=$(date +%Y%m%d); uv run --no-sync python -m m2_cad.persistencia_registro restore --registro data/registro.csv --origen backups/registro-$FECHA.csv'
   ```

   Para un respaldo de otra fecha, sustituir `$FECHA` por `YYYYMMDD` en ambos extremos; el
   formato es el que imprime `ls` en el diagnóstico.

3. Si la restauración falla por cabecera, no editar el CSV a mano: escalar con el primer renglón
   leído y elegir otro respaldo.

### Verificación de recuperación

```bash
docker compose exec -T m2-cad sh -c 'head -n 1 /app/data/registro.csv'
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/ready
```

Esperado: cabecera
`id,hora,texto,traduccion,resultado,latencia_ms,error,version` y `/ready` 200 con
`"registro":"ok"`.

### Escalado

Escalar si no hay respaldo válido, si la restauración rompe la cabecera o si `/ready` sigue en
503. Incluir el nombre del respaldo y el mensaje de error de la CLI; nunca pegar el CSV completo
si contiene texto de solicitudes.

## Restauración de `outputs/`

### Síntoma

- Faltan carpetas `outputs/<uuid>/` o sus entregables `programa.json`, `.step`, `.glb` y `.csv`.
- Una generación terminó en `entregada` pero las descargas devuelven 404.
- Se borró o sobrescribió `outputs/` por error durante mantenimiento.

### Diagnóstico

1. Listar artefactos presentes y respaldos disponibles:

   ```bash
   docker compose exec -T m2-cad sh -c 'find /app/outputs -maxdepth 2 -type f | head -n 20; ls -1 /app/backups/outputs-*.tar.gz 2>/dev/null || echo SIN_BACKUPS'
   ```

2. Confirmar que el fallo no es de descarga con token: leer los logs buscando 403/404 y
   `request_id`:

   ```bash
   docker compose logs --no-color --tail=200 m2-cad
   ```

### Acción

1. Tomar snapshot de `outputs/` antes de tocar nada:

   ```bash
   docker compose exec -T m2-cad sh -c 'FECHA=$(date +%Y%m%d); mkdir -p /app/backups; tar -czf /app/backups/outputs-pre-restore-$FECHA.tar.gz -C /app outputs'
   ```

2. Restaurar conservando el directorio anterior como `outputs.old.FECHA`:

   ```bash
   docker compose exec -T m2-cad sh -c 'FECHA=$(date +%Y%m%d); mv /app/outputs /app/outputs.old.$FECHA && mkdir -p /app/outputs && tar -xzf /app/backups/outputs-$FECHA.tar.gz -C /app'
   ```

   Para un respaldo de otra fecha, sustituir `$FECHA` por `YYYYMMDD` en ambos extremos; no
   eliminar `outputs.old.*` hasta verificar la recuperación.

3. Si no hay `outputs/`, crearlo antes de restaurar:

   ```bash
   docker compose exec -T m2-cad sh -c 'mkdir -p /app/outputs'
   ```

### Verificación de recuperación

```bash
docker compose exec -T m2-cad sh -c 'find /app/outputs -maxdepth 2 -type f | head -n 20'
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health
```

Esperado: reaparecen los archivos del respaldo y `/health` sigue en 200. Para confirmar una
descarga concreto, repetir el humo con autorización; **gasta tokens**:

```bash
uv run python scripts/smoke_deploy.py --n 1
```

### Escalado

Escalar si no hay respaldo, si el tar está corrupto o si las descargas siguen fallando tras la
restauración. Incluir nombre del respaldo, cantidad de archivos listados y `request_id` de la
descarga fallida.
