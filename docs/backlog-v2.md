# Backlog v2 — Profesionalización de M2 Asistente CAD

> Estado: **propuesta**, no ejecutada. No hay specs, issues ni PRs creados a partir de
> este documento. Reemplaza la numeración 24–48 del borrador de 25 specs.
> Base: estado real del repositorio al cierre de SPEC-023 (HU-22, `v1.0` publicada).

## 1. Qué cambia respecto del borrador de 25

El borrador proponía cinco épicas parejas de cinco. La validación contra el código
encontró tres problemas de fondo:

1. **Cinco ítems ya existen o están a medio hacer**: sistema de tokens (24), layout
   responsive (25), base de accesibilidad (28), dashboard/MLflow (40) y Docker
   multi-etapa (45). Especificarlos "desde cero" produce documentación que contradice
   el código.
2. **Dos dependencias invertidas**: la evaluación continua del banco en CI (41) gasta
   tokens reales y necesita primero caché/replay del LLM (37); las alertas de regresión
   (43) necesitan un baseline histórico que sólo existe después de 41.
3. **Falta lo que más justifica "profesional"**: el núcleo determinista (DSL →
   verificación → STEP) corre sus 113 pruebas **sólo en el contenedor del autor**, no
   en CI. Mientras eso siga así, el resto son features sobre una base no verificada.

Resultado: **33 especificaciones (SPEC-024 … SPEC-056)** en cuatro olas, con el ID
ordenado por ejecución: el ID más bajo es siempre lo próximo a tomar.

## 2. Cómo leer cada spec

- **Ola** = prioridad y orden de ejecución, no importancia académica.
- **Tamaño** = S (≤ 1 PR chico), M (1–2 PRs), L (3+ PRs, o PR encadenada).
- **Depende** = spec que debe estar fusionada antes.
- **Hoy** = evidencia del estado actual (ruta:línea).
- **HU** = historia única en el tablero; `HU-23` arranca después de `HU-22`.

## 3. Ola 0 — Baratas y de alto retorno

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 024 | Corpus dorado del núcleo determinista en CI | Calidad | M | — | Luis Meza |
| 025 | Logging estructurado y trazas correlacionadas | Backend | S | — | Juan Camilo |
| 026 | Reintentos con backoff y caché de respuestas del LLM | Backend | S | — | Juan Camilo |
| 027 | Motivo de declinación legible y etiquetado por causa | Pipeline | S | — | Luis Meza |
| 028 | Tipos del frontend generados desde OpenAPI | Frontend/API | S | — | Carlos |
| 029 | Escaneo de dependencias y secretos en CI | Entrega | S | — | Carlos |
| 030 | Runbook operativo | Entrega | S | — | Carlos |

### SPEC-024 · Corpus dorado del núcleo determinista en CI
- **Hoy**: `make kernel-test` (113 pruebas) se ejecuta sólo en el contenedor del autor;
  `ci.yml` corre `make check` + smoke con `--simulate-model`. El núcleo no está en CI.
- **Entrega**: corpus de pares DSL → (acepta/declina + hash del STEP) congelado, runner
  sin GPU ni red, job de CI que falla ante cualquier divergencia geométrica.
- **AC**: un cambio en `constraint-kit` o en `dsl.check` que altere una pieza rompe CI;
  el corpus declara explícitamente los casos esperados como declinación.

### SPEC-025 · Logging estructurado y trazas correlacionadas
- **Hoy**: `logging.getLogger` suelto (`trabajos.py:22,97,106`, `seguimiento.py:23,260,331`),
  sin `dictConfig`, sin formato JSON, sin request-id.
- **Entrega**: `dictConfig` con JSON, `request_id`/`job_id` propagados de API → SSE →
  pipeline → MLflow, y el registro del motivo de error sin secretos.
- **AC**: una solicitud completa se reconstruye filtrando por un único id.

### SPEC-026 · Reintentos con backoff y caché de respuestas del LLM
- **Hoy**: llamada única sin retry (`pipeline.py:386`); `_REINTENTOS_HTTP` de
  `seguimiento.py:30-34` es del cliente MLflow, no del LLM. Sin caché.
- **Entrega**: N reintentos con backoff y jitter sólo ante errores transitorios;
  caché de respuestas por hash(prompt+modelo+parámetros) con TTL; métricas de
  reintentos y de aciertos de caché.
- **AC**: un 5xx transitorio no llega al usuario como `ModeloNoDisponible`; un reintento
  con la misma solicitud no paga tokens dos veces.

### SPEC-027 · Motivo de declinación legible y etiquetado por causa
- **Hoy**: `PiezaDeclinada` / `ErrorVerificacion` existen (`pipeline.py:200-243`) pero el
  motivo que ve el usuario es técnico.
- **Entrega**: catálogo de causas (`familia_no_soportada`, `dimension_incoherente`,
  `verificacion_fallida`, `fuera_de_tolerancia`, `texto_ambiguo`…), mensaje en español
  legible con qué haría falta para aceptarla, y etiqueta estructurada persistida.
- **AC**: cada declinación del corpus de 024 tiene causa asignada y mensaje no técnico;
  las etiquetas son la fuente de las alertas de 047 y del panorama de 052.

### SPEC-028 · Tipos del frontend generados desde OpenAPI
- **Hoy**: `frontend/src/api.ts` escrito a mano; hay un test que congela el contrato
  (`tests/test_sse.py:116`) pero nada impide que el TS derive.
- **Entrega**: generación de tipos desde `/openapi.json` en `make` y en CI; falla si
  `api.ts` no coincide con el contrato.
- **AC**: cambiar un campo del API sin regenerar rompe CI, no producción.

### SPEC-029 · Escaneo de dependencias y secretos en CI
- **Hoy**: `dependabot.yml` cubre npm/uv/actions; no hay `pip-audit`, `gitleaks` ni
  `detect-secrets`; pre-commit sólo bloquea pesos y archivos grandes.
- **Entrega**: `pip-audit` + `gitleaks` como jobs de CI con política de excepciones
  documentada.
- **AC**: un secreto commiteado o un CVE alto falla el PR con el paso exacto a seguir.

### SPEC-030 · Runbook operativo
- **Hoy**: la documentación explica cómo levantar el sistema, no cómo operarlo cuando
  falla.
- **Entrega**: runbook con modelo caído / sin crédito / respuesta inválida, rotación de
  la clave DeepSeek, rollback de versión de modelo y de imagen, restauración de
  `data/registro.csv` y `outputs/`.
- **AC**: cada escenario tiene síntoma, diagnóstico y acción con comando exacto.

## 4. Ola 1 — Fundacionales

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 031 | Persistencia transaccional, retención y backup del registro | Backend | M | — | Juan Camilo |
| 032 | API `/v1` versionada con contrato congelado | Backend | M | 028 | Juan Camilo |
| 033 | Control de costo, límites de uso e idempotencia | Backend | M | 026 | Juan Camilo |
| 034 | Prompts versionados como artefactos | Pipeline | M | — | Luis Meza |
| 035 | Sistema de diseño v2: tokens, tipografía y modo oscuro | UX | M | — | Carlos |
| 036 | Edición iterativa de la pieza | Pipeline | L | 034 | Luis Meza |
| 037 | Endurecimiento de artefactos y descargas | Backend | S | — | Juan Camilo |

### SPEC-031 · Persistencia transaccional, retención y backup
- **Hoy**: `data/registro.csv` se escribe con `open(ruta,"a")` (`registro.py:89`), sin
  lock, sin `os.replace`, sin dedupe, mientras hay hasta 128 trabajos concurrentes
  (`trabajos.py:144-160`). `outputs/` crece sin política de retención.
- **Entrega**: escritura atómica y serializada (o migración a SQLite con esquema
  versionado), dedupe por id, retención configurable de `outputs/`, comando de
  backup/restore, `/ready` con chequeo de dependencias.
- **AC**: una corrida concurrente de N solicitudes no pierde ni duplica filas; el
  restore reproduce el registro exacto; `/ready` falla con el modelo caído.

### SPEC-032 · API `/v1` versionada con contrato congelado
- **Hoy**: rutas planas (`/generar`, `/generaciones`, `/registros`, `/health`) con
  `version="0.1.0"` (`api.py:27-33`); `/docs` y `/openapi.json` abiertos.
- **Entrega**: prefijo `/v1` con redirección desde las rutas viejas durante una
  versión, contrato OpenAPI congelado por versión, política de deprecación documentada.
- **AC**: el cliente viejo sigue funcionando; quitar un campo sin subir versión rompe
  el test de contrato.

### SPEC-033 · Control de costo, límites de uso e idempotencia
- **Hoy**: los tokens y el costo **ya se calculan** (`seguimiento.py:71-101`,
  `api.py:112-121`) pero no se aplica ningún tope; sin rate limit (no hay `slowapi` ni
  middleware) y sin clave de idempotencia en `/generar`.
- **Entrega**: tope por ventana y por sesión, presupuesto diario configurable, rechazo
  explícito al excederse, `Idempotency-Key` en `/generar` y métrica de gasto.
- **AC**: superar el presupuesto devuelve un error tipado, no una llamada pagada;
  reenviar el mismo `Idempotency-Key` no duplica la generación ni el costo.

### SPEC-034 · Prompts versionados como artefactos
- **Hoy**: prompts inline en `pipeline.py:45-68` (familias, material, formato DSL).
- **Entrega**: prompts como archivos versionados con id + hash, registro de la versión
  usada en cada solicitud y en MLflow, y tests de prompt (formato de salida, familias
  cubiertas, rechazo de texto ambiguo).
- **AC**: cada fila del registro es trazable a una versión de prompt; cambiar el prompt
  sin versión rompe CI.

### SPEC-035 · Sistema de diseño v2: tokens, tipografía y modo oscuro
- **Hoy**: `design/tokens.css` (72 líneas, `color-scheme: light`) importado desde
  `frontend/src/main.ts:3` — **vive fuera del paquete del frontend**; no hay modo oscuro
  ni escala tipográfica documentada.
- **Entrega**: tokens dentro de `frontend/src` (o paquete propio), escala tipográfica,
  tema claro/oscuro con `prefers-color-scheme` + preferencia explícita, contraste AA
  verificado en ambos temas, y documentación del sistema.
- **AC**: ambos temas cumplen contraste ≥ 4.5:1 en texto y ≥ 3:1 en foco; cambiar un
  token no requiere tocar componentes.

### SPEC-036 · Edición iterativa de la pieza
- **Hoy**: `/generar` sólo acepta `texto` (`api.py:36-51,405-414`); no existe endpoint
  que reciba programa o pieza anterior. Es el diferenciador principal del pipeline.
- **Entrega**: endpoint que recibe la pieza previa + instrucción de cambio, diff del
  programa DSL, re-verificación determinista y nueva versión de la pieza con historial
  de versiones por solicitud.
- **AC**: "hazla 5 mm más gruesa" produce una pieza nueva verificada y conserva la
  anterior; un cambio que rompe la verificación declina con causa de 027.

### SPEC-037 · Endurecimiento de artefactos y descargas
- **Hoy**: la allowlist de formatos existe (`api.py:~527`) y se restringe a `outputs/`,
  pero cualquiera con el UUID descarga cualquier artefacto y no hay expiración.
- **Entrega**: autorización por token de solicitud para descargas, expiración
  configurable de artefactos, validación estricta de id y de tipo MIME.
- **AC**: un UUID ajeno sin token no descarga; un artefacto expirado devuelve 410.

## 5. Ola 2 — Valor visible

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 038 | Historial de solicitudes en la UI | UX | M | 031 | Carlos |
| 039 | App shell y navegación por vistas | UX | M | 035 | Carlos |
| 040 | Visor 3D: vistas ortogonales, medidas y captura | UX | M | — | Carlos |
| 041 | Cierre de brechas WCAG 2.1 AA | UX | M | 035, 039 | Carlos |
| 042 | E2E del frontend con Playwright en CI | Calidad | M | 039 | Carlos |
| 043 | Exportación DXF de planos 2D | Pipeline | L | 024 | Luis Meza |
| 044 | Exportación PDF de planos con cotas | Pipeline | M | 043 | Luis Meza |
| 045 | Evaluación continua del banco con respuestas grabadas | MLOps | M | 026, 034 | Juan Camilo |
| 046 | Cola persistente de trabajos y worker | Backend | L | 031 | Juan Camilo |

### SPEC-038 · Historial de solicitudes en la UI
- **Hoy**: sin `localStorage`/`historial` en `frontend/src`, pero el registro **ya
  existe** server-side (`data/registro.csv`, `registro.py:29`) y `/registros/{id}` lo
  expone (`api.py:196-207`).
- **Entrega**: vista de historial que lista, filtra y reabre solicitudes desde el
  backend, con reanudación de la vista de resultado y descarga de artefactos.
- **AC**: el historial sobrevive a recargar el navegador y a otro equipo; no hay copia
  de datos autoritativa en el cliente.

### SPEC-039 · App shell y navegación por vistas
- **Hoy**: layout responsive con breakpoints 900/480 (`style.css:62-70`), skip link y
  `aria-live` ya presentes; todo vive en una sola vista `App.vue`.
- **Entrega**: shell con navegación (nueva solicitud / historial / ajustes), rutas con
  URL compartible, estados vacío, cargando, error y declinación diferenciados.
- **AC**: cada vista tiene URL propia y estado recuperable; la navegación es operable
  sólo con teclado.

### SPEC-040 · Visor 3D: vistas ortogonales, medidas y captura
- **Hoy**: three.js 0.187 + `GLTFLoader` + `OrbitControls` en `GlbViewer.vue:1-16`; sólo
  orbitar, zoom y reset; sin `OrthographicCamera` ni `toDataURL`.
- **Entrega**: vistas frontal/superior/lateral, cotas básicas sobre aristas, captura PNG
  y ajuste de unidades.
- **AC**: las tres vistas son reproducibles y exportables; las medidas coinciden con el
  CSV de la pieza dentro de la tolerancia declarada.

### SPEC-041 · Cierre de brechas WCAG 2.1 AA
- **Hoy**: base seria ya implementada (foco 3 px, `aria-describedby`, `role="alert"`,
  contraste 6.31:1 documentado); verificado sólo manualmente en Chrome.
- **Entrega**: auditoría axe en CI, corrección de brechas reales (no reescritura),
  navegación completa por teclado, anuncios de estado en SSE y contraste en ambos temas.
- **AC**: axe sin violaciones críticas/serias en las vistas principales; el flujo
  completo se opera sin mouse.

### SPEC-042 · E2E del frontend con Playwright en CI
- **Hoy**: 32 casos Vitest (`frontend/tests/`), sin Playwright ni `e2e/`.
- **Entrega**: flujo E2E feliz + declinación + error de modelo contra backend simulado,
  en CI, con artefactos de traza en fallo.
- **AC**: una regresión de UI que rompa el flujo feliz falla CI con captura y traza.

### SPEC-043 · Exportación DXF de planos 2D
- **Hoy**: sólo STEP/GLB/CSV (`pipeline.py:288-299`, allowlist en `api.py:~527`);
  `ezdxf` aparece sólo como extra de `constraint-kit` en `uv.lock`. Es el ítem más caro
  del backlog: exige proyección 2D y cotas.
- **Entrega**: proyección de vistas ortogonales a DXF con capas por tipo de arista y
  cotas principales; descarga por el canal de artefactos de 037.
- **AC**: el DXF abre en un visor CAD estándar; las cotas coinciden con la verificación
  determinista dentro de tolerancia.

### SPEC-044 · Exportación PDF de planos con cotas
- **Hoy**: inexistente (`pypdf` sólo como extra de `constraint-kit`).
- **Entrega**: PDF de plano con vistas de 043, cajetín (material, masa, fecha, id de
  solicitud) y escala declarada.
- **AC**: el PDF es imprimible A4/A3 con escala legible y reproduce el cajetín completo.

### SPEC-045 · Evaluación continua del banco con respuestas grabadas
- **Hoy**: el banco gasta tokens reales (`banco.py:1-14`) y **no corre en CI**;
  `evaluacion.py:246` declara que no reintenta.
- **Entrega**: modo replay del banco con respuestas grabadas y versionadas (apoyado en
  la caché de 026 y los prompts de 034), corrida en CI con umbral de aceptación, y
  corrida real programada fuera de CI.
- **AC**: CI detecta una caída de tasa de aceptación sin gastar tokens; la corrida real
  queda registrada en MLflow como baseline.

### SPEC-046 · Cola persistente de trabajos y worker
- **Hoy**: 128 trabajos en memoria (`trabajos.py:144-160`), `--workers 1`
  (`Dockerfile`); un reinicio pierde todo.
- **Entrega**: cola persistente, worker separado, reanudación de trabajos tras reinicio,
  drenaje ordenado en apagado.
- **AC**: reiniciar el servicio no pierde solicitudes en curso; el drenaje no corta SSE
  a mitad de un evento.

## 6. Ola 3 — Opcional según tiempo

| Spec | Título | Épica | Tamaño | Depende | Owner |
| --- | --- | --- | --- | --- | --- |
| 047 | Alertas de regresión de calidad | MLOps | M | 045 | Juan Camilo |
| 048 | Despliegue en la nube | Entrega | L | 033, 037, 046 | Carlos |
| 049 | Materiales, tolerancias y BOM con costos | Pipeline | L | 024 | Luis Meza |
| 050 | Plantillas parametrizadas de piezas | Pipeline | M | 036 | Luis Meza |
| 051 | Cortes y secciones en el visor 3D | UX | L | 040 | Carlos |
| 052 | Panorama de métricas sobre MLflow | MLOps | S | 025, 027 | Juan Camilo |
| 053 | Comparación A/B de prompts y modelos | MLOps | M | 034, 045 | Juan Camilo |
| 054 | Autenticación y usuarios | Backend | L | 037 | Juan Camilo |
| 055 | Sitio de documentación publicado | Entrega | M | 030 | Carlos |
| 056 | Releases automáticos con changelog | Entrega | M | 032 | Carlos |

Notas de la ola 3:

- **047** necesita el baseline de 045 y las etiquetas de 027; sin ellos "regresión" no
  es medible.
- **048** ya tiene Docker multi-etapa (`Dockerfile:1-63`, 3 etapas + `HEALTHCHECK`): la
  spec es despliegue, TLS, dominio y runbook, no empaquetado. Requiere 054 si el
  despliegue es público.
- **049** es research-first: depende de qué expongan materiales y tolerancias en
  `constraint-kit` vendoreado (`vendor/`, no verificado). Material hoy sólo vive en el
  prompt (`pipeline.py:68`) y la tolerancia ±2 % es de **medición** del banco
  (`banco.py:33`), no de fabricación.
- **052** es deliberadamente chica: MLflow ya registra params, métricas, tags y versión de
  modelo (`seguimiento.py:126-262,286-339`) y tiene UI en `:5000`. La spec cubre
  `/metricas`, etiquetas de 027 y el tablero de costo — no un sistema nuevo.
- **055** se cubre primero con el runbook de 030; el sitio es presentación, no operación.
- **056** sólo aporta si se mantiene el flujo de PRs y Conventional Commits ya en uso.

## 7. Trazabilidad: borrador 24–48 → backlog v2

| Borrador | Backlog v2 | Cambio |
| --- | --- | --- |
| 24 Sistema de diseño | 035 | Reformulada: tokens fuera del frontend, tipografía y modo oscuro |
| 25 Layout responsive | 039 | Reformulada: app shell con navegación, no cosmética responsive |
| 26 Historial en la UI | 038 | Mantenida; datos desde el backend, no caché local |
| 27 Visor 3D | 040 + 051 | Partida: ortogonal/medidas/captura (040) y cortes (051) |
| 28 Accesibilidad AA | 041 | Reformulada: cierre de brechas con axe, no auditoría desde cero |
| 29 Edición iterativa | 036 | Mantenida y priorizada; depende de prompts versionados |
| 30 Catálogo de plantillas | 050 | Mantenida; depende de 036 para reutilizar el programa |
| 31 Material y tolerancias | 049 | Mantenida, con BOM con costos; research-first |
| 32 DXF/PDF | 043 + 044 | Partida en dos specs por costo real |
| 33 Declinación legible | 027 | Priorizada a ola 0, con etiquetado por causa |
| 34 Persistencia BD | 031 | Priorizada; absorbe integridad, retención y backup |
| 35 Autenticación | 054 | Bajada a ola 3; el mínimo de seguridad va en 037 |
| 36 Rate limit/costo | 033 | Priorizada; el cálculo de costo ya existe, falta el tope |
| 37 Reintentos y caché | 026 | Priorizada a ola 0; habilita 045 |
| 38 `/v1` y OpenAPI | 032 | Reformulada: versionado y contrato, no "documentar" |
| 39 Logging | 025 | Mantenida, ola 0 |
| 40 Dashboard de métricas | 052 | Reformulada y reducida: no duplicar MLflow |
| 41 Banco en CI | 045 | Repriorizada; depende de 026 y 034 |
| 42 Comparación en MLflow | 053 | Reformulada: hoy no existe artefacto de prompt (034) |
| 43 Alertas de regresión | 047 | Repriorizada tras 045 y 027 |
| 44 Playwright | 042 | Mantenida |
| 45 Docker multi-etapa y nube | 048 | Reformulada: multi-etapa ya existe; sólo despliegue |
| 46 Releases automáticos | 056 | Bajada a ola 3 |
| 47 Escaneo de deps/secretos | 029 | Priorizada a ola 0 |
| 48 MkDocs | 055 | Bajada; el runbook (030) cubre la necesidad operativa |
| — | 024 | **Nueva**: corpus dorado del núcleo determinista en CI |
| — | 028 | **Nueva**: tipos del frontend desde OpenAPI |
| — | 030 | **Nueva**: runbook operativo |
| — | 034 | **Nueva**: prompts versionados como artefactos |
| — | 046 | **Nueva**: cola persistente y worker |
| — | 047 | **Nueva**: alertas de regresión |

## 8. Reglas de proceso

1. **Dos niveles de documento.** `spec.md` completo (problema, requisitos, AC
   Given-When-Then) al crear la spec; `plan.md` y `tasks.md` recién cuando la HU se
   toma. Evita 75 documentos a medio llenar.
2. **Reparto por ola, no por épica.** Un reparto 9/8/8 por épica deja 024 y 036 —las dos
   de mayor impacto— al final del calendario. Con olas, cada desarrollador toma una
   spec terminable por semana.
3. **Cada spec cierra con su evidencia**: PR fusionada, fila en `specs/README.md` y
   registro en el tablero, igual que 001–023.
4. **Las specs que reformulan algo existente citan el código actual** en su encabezado
   (ruta:línea), para que la retroactividad sea explícita y nadie "descubra" que ya
   estaba hecho.
5. **Nada se crea en GitHub hasta aprobar este documento**: las 33 HUs se abren e
   incorporan al tablero `m2-asistente-cad` en el mismo momento en que cada spec se
   redacta, no antes.

## 9. Riesgo declarado del backlog

- **Mayor incógnita técnica**: 043 y 044 (DXF/PDF). Proyección 2D y cotas dependen de lo
  que exponga `constraint-kit`; conviene un spike de medio día antes de comprometerlas.
- **Segunda incógnita**: 049 (materiales y tolerancias de fabricación) toca el DSL y la
  verificación; si `constraint-kit` no soporta tolerancias, la spec cambia de alcance.
- **Riesgo de calendario**: la ola 3 completa duplica el trabajo de la ola 0–2. Si hay
  que elegir, 047/052/055/056 aportan más por hora invertida que 049/051/054.
