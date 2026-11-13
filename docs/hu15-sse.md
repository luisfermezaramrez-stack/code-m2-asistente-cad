# HU-15 · Contrato backend de progreso y cancelación

## Compatibilidad y negociación

`GET /health` conserva `200 {"status":"ok"}`.
`POST /generar` conserva cuerpo y respuesta JSON existentes cuando no se pide
SSE. Vue sustituye a Gradio después de migrar sus pruebas útiles; la entrega
integrada y la trazabilidad se documentan en `hu15-despliegue.md`.

Para recibir SSE, enviar el mismo cuerpo `{"texto":"Espaciador de 14 mm"}` con
`Content-Type: application/json` y `Accept: text/event-stream`. En un navegador,
usar un cliente de streaming de POST (por ejemplo, `fetch` y lectura del cuerpo);
`EventSource` nativo solo admite GET y no sirve para este POST.

La validación del cuerpo ocurre antes de iniciar un trabajo: entradas vacías,
espacios, más de 1000 caracteres o cuerpo mal formado devuelven el 422 JSON
habitual. No se inventan eventos para solicitudes rechazadas.

Tras aceptar el stream, HTTP es 200. Cabeceras:

- `Content-Type: text/event-stream; charset=utf-8`.
- `X-Solicitud-ID`: identificador opaco generado por el servidor.
- `Cache-Control: no-cache, no-transform`, `Vary: Accept` y
  `X-Accel-Buffering: no` para evitar almacenamiento/buffering del stream.

Los fallos posteriores se expresan con un evento terminal, no cambiando el
estado HTTP ya enviado. No hay reanudación/replay ni soporte de `Last-Event-ID`:
repetir el POST crea otro trabajo. Consultar el ID existente para recuperar su
estado en lugar de reenviar automáticamente la solicitud.

## Eventos y etapas reales

Cada frame tiene `id: <solicitud_id>:<secuencia>`, `event: <estado>` y una línea
`data:` JSON. La secuencia aumenta desde 1 y todos los frames comparten ID.

```text
id: 6c...:1
event: validando
data: {"solicitud_id":"6c...","secuencia":1,"estado":"validando","terminal":false,"cancelacion_solicitada":false}

```

| Evento | Significado | Campos adicionales |
| --- | --- | --- |
| `validando` | Entrada al control de validación del pipeline; validación de texto y traducción técnica | Ninguno |
| `generando` | Traducción finalizada; comienza planificación con modelo, seguida de catálogo, verificación, construcción y exportación | Ninguno |
| `verificado` | El pipeline devolvió después de construir/exportar y verificar | `resultado`: mismo diccionario de entregables/métricas que JSON |
| `declinado` | Declinación explícita de dominio; no se infiere de un HTTP 422 genérico | `motivo`, `codigo_http: 422` |
| `error` | Fallo de traducción/modelo/verificación, excepción interna o de registro | `motivo`, `codigo_http` |
| `cancelado` | El pipeline salió en un punto de cancelación cooperativa, sin avanzar a más etapas | `motivo`, `pipeline_detenido: true`, `cancelacion_remota_confirmada: false` |

Todos incluyen `terminal` y `cancelacion_solicitada`. Solo los cuatro últimos
son terminales, exactamente uno por trabajo. `cancelado` amplía explícitamente
los tres resultados de AC3 del issue #39, conforme al requisito posterior de
tener cancelación terminal inequívoca. No se usa `error` para disimularla.

El camino normal es `validando` → `generando` → terminal. Un error durante la
validación/traducción termina sin `generando`; si se cancela antes de empezar,
puede existir solo `cancelado`. Un fallo al cargar el motor puede producir solo
`error`. Nunca se añaden etapas no ejecutadas para completar una secuencia.

Sin modelo configurado se informa la validación de configuración y `error` 503.
La marca `verificado` no certifica resistencia ni normas: el resultado conserva
el aviso preliminar existente. Declinación, error y cancelación no incluyen
entregables de otra solicitud.

No hay porcentajes, temporizadores de avance ni estimaciones. Cada 15 segundos
sin datos puede enviarse un comentario SSE `: keep-alive`, exclusivamente para
mantener la conexión; no es una etapa ni señal de avance. Si el cliente no recibe
eventos de etapa, debe informar que no dispone de progreso.

## Consultar y solicitar cancelación

`GET /generaciones/{solicitud_id}` devuelve la última etapa/terminal conocido y
`cancelacion_solicitada`, incluso después de desconectar SSE. Antes del primer
evento puede devolver `estado: iniciando`, sin atribuir una etapa al pipeline.

`DELETE /generaciones/{solicitud_id}` es idempotente:

- **202** si el trabajo sigue activo: solo establece la señal cooperativa.
  Devuelve la etapa actual, `terminal: false`, `cancelacion_solicitada: true`.
  No devuelve `pipeline_detenido: true` antes de comprobar una salida segura.
- **200** si ya es terminal: conserva exactamente el resultado que ganó la carrera,
  incluso si fue `verificado`, `declinado` o `error`. No lo reescribe como cancelado.
- **404** si es desconocido, expiró por retención o pertenece a otro proceso.

Cerrar la conexión solicita la misma cancelación cooperativa. Se contemplan el
mensaje ASGI `http.disconnect`, cancelación de la tarea de streaming y fallos
`OSError` de envío de cabeceras/datos (ASGI 2.4). La desconexión impide entregar
un terminal por ese canal: consultar por ID. La solicitud de cancelar y un
terminal pueden competir; el resultado registrado es la autoridad.

## Entrega de artefactos a la SPA

`GET /generaciones/{solicitud_id}/archivos/{step|glb|csv}` entrega bytes del archivo
con nombre de descarga y tipo de contenido correspondiente. `HEAD` permite
comprobar disponibilidad sin descargarlo. Cada formato es independiente: un GLB
ausente no impide STEP/CSV. CSV reconoce `bom_csv` y la clave anterior `csv`.

Solo se entrega el archivo asociado a un resultado `verificado`, existente dentro
de la raíz `outputs/` y con extensión correcta. Se resuelven enlaces/rutas antes
de comprobar la pertenencia; no se monta el directorio completo. Formatos no
permitidos, archivos ajenos/ausentes y resultados no verificados devuelven 404.
La retención de trabajos también limita el tiempo de acceso por ID.

El adaptador SSE traduce errores de disponibilidad de modelo/traducción a un
mensaje público genérico: no remite direcciones privadas ni claves del proveedor
incluidas en una excepción. El contrato JSON anterior se conserva.

## Límites comprobables

- No se matan hilos ni se promete abortar una llamada nativa o HTTP en curso.
  Hay puntos seguros antes de iniciar, después de traducción, después de modelo,
  antes de construcción y después de construcción/exportación.
- Traducción Gemini (timeout actual 8 s), modelo (120 s) y CAD/exportación son
  bloqueantes. Cancelar espera su retorno; CAD no tiene timeout ni interrupción
  garantizada. Durante esa espera sigue activo el estado anterior, no `cancelado`.
- `pipeline_detenido` confirma únicamente que terminó la ejecución local del
  pipeline en un punto seguro. No certifica que un proveedor remoto haya liberado
  GPU/procesos. No hay protocolo de cancelación remota de Gemini/llama.cpp;
  `cancelacion_remota_confirmada` permanece falso. Esto no es cancelación completa
  inmediata de extremo a extremo y no cierra por sí solo ese aspecto de AC3.
- Si una operación falla/expira mientras hay cancelación pendiente, gana `error`,
  sin afirmar que el proveedor remoto se detuvo. Si termina normalmente, el
  siguiente punto seguro puede confirmar la salida cooperativa local.
- Si se cancela durante exportación, podrían existir archivos ya creados en la
  subcarpeta de esa solicitud. No se anuncian en `cancelado`; no hay borrado
  automático ni promesa de rollback del sistema de archivos.
- El registro es en memoria de un único proceso: máximo 128 trabajos retenidos.
  Al llenarse se expulsa el terminal más antiguo por orden de creación; los activos
  no se expulsan y, si todos lo son, el nuevo POST devuelve 503 antes del stream.
  No persiste tras reiniciar ni coordina múltiples workers. No hay recuperación
  de un trabajo terminado por cierre del servidor; su detención no se confirma.
- Cada trabajo escribe su resultado terminal en el registro CSV existente antes
  de publicarlo. Una falla de escritura produce `error` explícito. La respuesta
  JSON existente mantiene su registro y contrato anteriores.

## Verificación

Pruebas de API heredada más pruebas SSE: secuencia, terminal único, dominio frente
a errores 422, disponibilidad del modelo, validación previa, resultado real con
motor CAD sin servicios externos, retención, entrega incremental mientras el
procesador sigue bloqueado, cancelación repetida, desconexión ASGI y fallos de
envío 2.4. Se comprueba que no se confirma cancelación durante la operación,
que el punto seguro evita etapas posteriores y que un fallo en curso sigue siendo
error. No se afirma haber probado detención de proveedores remotos.

En las pruebas de compatibilidad se reprodujo en `HEAD` un defecto previo de CSV
en Windows (`\r\r\n`). Se evita la segunda traducción de saltos al escribir el BOM,
conservando su contenido y formato; la prueba existente de lectura verifica la corrección.
