# Herramienta de evaluación HU-07

Estado: **corrida real única ejecutada con DeepSeek**: 30/30 construcciones
conformes (meta ≥26) y 10/10 declinaciones correctas (meta ≥8). Sin fallos técnicos,
geometrías no conformes ni errores silenciosos por familia. Pendiente de revisión
humana; no se declara HU-07 cerrada automáticamente.

Evidencia: [reporte completo](banco-real-20261114T042139Z-85855d97/20261114T042140Z-1303cab4/reporte.md)
y [auditoría de aceptación](banco-real-20261114T042139Z-85855d97/auditoria.md).
Los JSON, registros CSV, STEP y snapshot de código se conservan localmente bajo
esa carpeta, fuera de Git según SPEC-016 RNF-2; los hashes quedan en el Markdown.
Latencia cliente media 2,765 s y p90 2,956 s; 26280 tokens de entrada y 2700 de salida.
Se conservaron 40 registros, 30 STEP y 40 referencias a corridas MLflow finalizadas.
Banco, prompt, código y configuración se comprobaron sin cambios durante la corrida;
el código sin commit está archivado con manifiesto SHA-256. No hubo reintentos,
ajustes ni segunda corrida. El smoke de `smoke/acf49455e82f4b44bea3c7470ff4864b/`
queda separado y no entra en los denominadores.

## Preparación del smoke positivo único

Estado comprobado en la preparación inicial: faltan credenciales DeepSeek en entorno
y `.env`; API `127.0.0.1:8000` y MLflow `127.0.0.1:5000` no son accesibles.
Compose tiene seguimiento habilitado y URI interna configurada, pero no hay
servicios del proyecto levantados. La validez de una clave y el saldo del
proveedor no se han comprobado. No se ejecutó inferencia.

Durante el arranque posterior se detectó un 403 de MLflow para el host interno
`mlflow:5000`, aun con `/health` 200. Compose ahora declara `--allowed-hosts`
con los hosts interno y locales exactos; no se desactiva la protección de hosts.
Después de corregirlo: salud externa de API/MLflow 200, consulta del cliente
MLflow desde el contenedor API correcta (sin crear corridas) y las 11 fuentes
Python del backend coinciden por SHA-256 con el árbol actual, incluidos cambios
sin commit. La recreación de ambos contenedores conservó marcadores de diagnóstico
en los montajes de datos/salidas y en el volumen MLflow; SQLite pasó `quick_check`.
Los marcadores de datos/salidas se retiraron después de comprobarlos. Esto verifica
persistencia de almacenamiento, no generación real de piezas. La clave continúa
pendiente de introducir manualmente; no se llamó al proveedor.

Antes de ejecutar el smoke: configura `DEEPSEEK_API_KEY` sin publicarla y arranca
la API/MLflow con el código actual (`docker compose up --build -d` desde esta
rama incluye cambios sin commit). Conserva montajes `data/`, `outputs/` y volumen
MLflow. Verifica salud de ambos; el build debe incluir `/registros/{id}`.
No basta con reutilizar una imagen anterior a la recuperación HU-07.

Comando exacto para **HU02-P01 únicamente** (placa positiva del banco vigente):

```powershell
uv run --link-mode=copy --no-sync --with mlflow-skinny==3.18.0 python scripts/smoke_hu07.py
```

**Este comando hace una llamada DeepSeek con costo**, no se ha ejecutado en esta
preparación. El script comprueba salud/contrato y acceso a MLflow antes del único
POST de generación. Reutiliza `evaluar_caso`, envía solo la descripción original
en español y solicita JSON. No reintenta la generación ni invoca el banco completo.

Conserva en `docs/hu07/smoke/<uuid>/`: `resultado.json` (medidas, latencia,
correlación, métricas, ID/enlace a la corrida MLflow), `registro.json` cuando
se confirma el CSV remoto y `pieza.step` con SHA-256 cuando puede descargarse.
Busca la corrida existente por `solicitud_id`; no crea una corrida adicional.
Los archivos originales y el CSV permanecen en los volúmenes del backend.
Salida 0 requiere conformidad, registro, STEP y corrida MLflow confirmados;
salida 2 conserva lo obtenido sin declarar éxito. Si un POST agota el timeout,
no repitas a ciegas: puede seguir ejecutándose en el backend. Este smoke no
acredita las metas de 40 casos de HU-07.

## Corrida completa (posterior al smoke)

Desde la raíz, con el entorno instalado y la API real disponible:

```powershell
make bench-report
# Equivalente, si no hay make:
uv run --no-sync python -B -m m2_cad.evaluacion --api-url http://localhost:8000
```

Son alternativas: ejecutar una sola, no ambas. Ambas hacen 40 solicitudes con costo.

Lee y valida las 40 filas del banco versionado. Hace 40 POST secuenciales a
`/generar` con `Accept: application/json`, exclusivamente con `{"texto": solicitud}`.
Las dimensiones, parámetros
y respuestas esperadas permanecen en el evaluador. La cabecera `X-Request-ID`
correlaciona la fila del CSV de registro y no forma parte del prompt.

Cada corrida conserva `docs/hu07/<corrida>/reporte.md` y `resultados.json`, con
huella SHA-256 del banco, causas, tiempos HTTP, medidas, desviaciones, registros
y enlaces STEP. `--salida` permite cambiar el directorio; `--timeout` fija los
segundos de espera por operación HTTP. No hay reintentos automáticos ni exclusión
de casos fallidos: los denominadores son siempre 30 positivos y 10 negativos.
Salida 0: metas alcanzadas y 40 registros confirmados; salida 2: metas o registros
pendientes. Los fallos de red también se reportan; no son declinaciones.

## Clasificación

- `conforme`: positivo con STEP declarado, volumen y **cada eje X/Y/Z, sin
  ordenar**, dentro de ±2 % de la referencia HU-02.
- `geometria_no_conforme`: construcción fuera de tolerancia o construcción de un
  negativo. Cuenta como error silencioso: HTTP 200 no demuestra conformidad.
- `declinacion_explicita`: negativo con HTTP 422, señal
  `X-Resultado-Tipo: declinacion_explicita` y motivo de declinación no vacío.
  Se considera correcta por rechazo explícito de una solicitud negativa; no se
  pretende evaluar automáticamente la equivalencia semántica del motivo.
- `declinacion_indebida`: el mismo rechazo explícito, pero de un positivo.
- `fallo_tecnico`: transporte, 4xx/5xx sin declinación explícita, JSON inválido,
  medidas inválidas o entregable ausente. Nunca incrementa éxitos.

Un 422 genérico, un error del verificador o un timeout no son negativas correctas.
STEP se marca `no aplica` en ambas clases de declinación, `no disponible` cuando
no se obtuvo construcción. Un registro no recuperable queda **no confirmado**;
su enlace conserva el ID solicitado para investigar, sin afirmar que exista.
El evaluador compara las medidas reportadas por el pipeline; no sustituye una
inspección independiente del STEP ni una auditoría de norma o forma completa.
Incluso reimportando el STEP, volumen y caja conformes **no descartan todas las
diferencias de forma**: agujeros, posiciones, radios, topología o acabados distintos
pueden conservar esas magnitudes. La revisión humana de cada STEP contra la
solicitud permanece pendiente; no se afirma equivalencia total ni aptitud de fabricación.

## Trazabilidad compatible

El cuerpo actual de `/generar` se conserva, sin campo de traducción ni nuevas
medidas provenientes del evaluador. Las cabeceras `X-Registro-ID`, `X-Registro-URL` y `X-Step-URL`
permiten correlacionar sin cambiar las ocho columnas existentes del CSV.
`GET /registros/<id>` consulta la fila; `GET /registros/<id>/step` entrega el
archivo únicamente dentro de `outputs/`. Las excepciones controladas, inesperadas
y de validación se registran una vez por solicitud. La traducción es `no aplica`.
El CSV y MLflow conservan el identificador de configuración vigente de HU-16:
`LLM_MODEL_VERSION` o el modelo configurado. No certifica los pesos ni una revisión
inmutable del proveedor. La identidad reportada por el proveedor permanece como
metadato interno del programa/resultado y de los errores de planificación o CAD;
no altera el cuerpo JSON público ni sustituye la versión configurada de MLflow.

JSON usa el UUID de `X-Request-ID` cuando es válido; el mismo ID identifica la
fila CSV y el tag `solicitud_id` de su única corrida MLflow. SSE conserva el ID
del gestor de HU-15: la fila y la corrida terminal usan ese ID, sin una segunda
escritura de trazabilidad. La consulta de registro y STEP no crea filas ni corridas.
Un fallo inesperado devuelve 500 genérico, registra la clase del error y cierra
MLflow. Las entradas inválidas conservan el 422 de FastAPI, con una sola fila
CSV, sin arrancar el pipeline ni crear una corrida de generación.

## Preparación y seguimiento

Se necesitan DeepSeek (`DEEPSEEK_API_KEY`, modelo `LLM_MODEL`, por defecto
`deepseek-v4-pro`), kernel CAD y API con `data/` y `outputs/` persistentes.
La solicitud llega directamente en español, sin Gemini ni traducción.
MLflow conserva su configuración de HU-16 y Vue/SSE el contrato de HU-15.
El evaluador HTTP se complementa con `m2_cad.banco` de HU-14/HU-16: no lo
sustituye ni modifica sus referencias, métricas o seguimiento.
El modo HTTP no certifica por sí solo modelo o revisión del proveedor.

Las pruebas `tests/test_evaluacion.py` usan HTTP simulado y directorios temporales;
sus reportes se identifican como **SIMULADO — no evaluación LLM**. No descargan
pesos ni consultan servicios externos. Las referencias deterministas HU-02 no
cuentan como resultados del LLM.

Si una meta falla, el reporte muestra causas por caso. Corresponde documentar un
ajuste y repetir **una vez**, conservando ambas corridas y enlazando el reporte
real en el issue #7. La herramienta no modifica el banco ni el prompt.

## Verificación de la recuperación (sin inferencia)

Revisadas base, versión de develop y stash de los tres conflictos. Se integraron
las cabeceras y rutas persistentes de HU-07 manteniendo las firmas con medición,
declinación tipada, SSE, artefactos y cierre de MLflow. No se modificaron
`data/test_cases.csv`, `src/m2_cad/banco.py` ni las referencias de HU-14.

Pruebas afectadas (API, pipeline, evaluación, seguimiento de API, SSE y registro):
**155 aprobadas**, con proveedor simulado y directorios temporales. Incluyen
40 solicitudes HTTP simuladas contra la API actual, 40 filas únicas y enlaces
consultables; no son una corrida real ni evidencian las metas del modelo.
Banco/seguimiento: **25 aprobadas y un fallo** en el gate preexistente de
sobrecarga MLflow local: p95 **225,2 ms**, umbral **50 ms**, en Windows.
El módulo de seguimiento y ese gate no se modificaron ni se relajó el umbral;
su resultado impide declarar todos los checks en verde en este entorno.

El entorno CAD Windows existente no tenía MLflow; se verificó mediante overlay
temporal de uv, sin cambiar dependencias ni lockfile:

```powershell
uv run --link-mode=copy --no-sync --with mlflow-skinny==3.18.0 python -m pytest tests/test_api.py tests/test_pipeline.py tests/test_evaluacion.py tests/test_api_seguimiento.py tests/test_sse.py tests/test_registro.py -q --no-cov
uv run --link-mode=copy --no-sync --with mlflow-skinny==3.18.0 python -m pytest tests/test_banco.py tests/test_banco_seguimiento.py tests/test_seguimiento.py -q --no-cov
uv run --no-sync ruff check src tests
```

El primer intento de overlay sin `--link-mode=copy` falló por hardlinks
incompatibles con OneDrive (error 396); al usar copia, la suite pudo ejecutarse.
Esto no acredita instalación limpia ni cobertura de la suite completa.
