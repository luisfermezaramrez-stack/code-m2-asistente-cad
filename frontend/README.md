# HU-15 · Frontend Vue

Vue 3 (Composition API), Vite y TypeScript. Reutiliza directamente
`../design/tokens.css`: no hay segunda copia de la paleta o de los tokens.
La aplicación contiene únicamente textos de producto; la maqueta y sus variantes
siguen en `design/`.

## Ejecutar localmente

Requiere Node ≥22.12 (verificado con Node 24) y el entorno Python del proyecto.
Desde la raíz, iniciar la API en una terminal:

```bash
uv run --no-sync uvicorn m2_cad.api:app --app-dir src --host 127.0.0.1 --port 8000
```

En otra terminal:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

Abrir la dirección local de Vite, normalmente `http://127.0.0.1:5173`. Su proxy
de desarrollo envía `/generar`, `/generaciones` y `/health` a la API local.
No hay URLs del modelo ni claves en el código cliente. Las credenciales de
Gemini y la configuración de llama.cpp pertenecen exclusivamente al backend.
Sin esos servicios configurados, la API devuelve un error real: la SPA no tiene
modo demo, fixtures ni progreso generado por tiempo.

## Verificación

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

`npm --prefix frontend run preview` sirve el build local con el mismo proxy de
desarrollo, normalmente en `http://127.0.0.1:4173`. La integración de despliegue
sirve `frontend/dist` directamente con FastAPI en `http://127.0.0.1:8000/`, sin
Vite ni otro servicio web en ejecución. Docker compila Vue en una etapa Node y
copia solo el build a la imagen Python. Gradio ya se retiró tras migrar sus
comportamientos útiles; véase `../docs/hu15-despliegue.md`.

## Flujo y cancelación

- `fetch` POST con `Accept: text/event-stream` y `AbortController`; parser de
  bytes UTF-8 fragmentados, CR/LF/CRLF, comentarios y `data:` multilínea.
- Solo se muestran etapas recibidas del servidor. No hay porcentajes ni tiempos
  estimados. Esperar cabeceras o recibir únicamente heartbeats no crea etapas.
- El identificador se obtiene de cabeceras/eventos; se validan coincidencia,
  secuencia, estado y terminal. Un stream incompleto no es éxito.
- Cancelar envía DELETE. Un 202 es solicitud pendiente y mantiene SSE abierto
  para recibir la salida real. Un terminal ya confirmado gana cualquier carrera.
- Interrumpir espera aborta el transporte; no confirma detención. Se consulta GET
  una vez al interrumpirse y se ofrece «Actualizar estado» si aún no hay terminal.
  No hay polling que invente progreso. La consulta manual puede recuperar la
  última etapa sin inventar las anteriores que no se recibieron.
- «Procesamiento local detenido» requiere `cancelado` y `pipeline_detenido: true`.
  Siempre aclara que no confirma la detención remota. Si se interrumpe antes de
  recibir un ID, no es posible consultar/cancelar explícitamente ese trabajo.
- Timeout configurable de 5–600 s (180 por defecto), destinado a la espera real;
  consultas/cancelación/comprobación de archivos tienen un límite de 10 s.
  Se conserva la descripción al fallar o declinar.
- Nueva solicitud: se abortan conexiones anteriores y se limpian etapas, modelo
  y archivos. Las respuestas tardías se descartan por versión de solicitud.

## Archivos y visor

Los valores de ruta del pipeline no se convierten en URLs del navegador. Cada
archivo usa `/generaciones/{id}/archivos/{step|glb|csv}`; HEAD comprueba disponibilidad
y GET entrega bytes reales. La API limita la entrega al resultado verificado
de ese trabajo, dentro de `outputs/`, existente y con extensión correcta.
No se publica el directorio completo. Los tests pueden sustituir esa raíz por
un directorio temporal.

STEP, GLB y CSV se comprueban independientemente. Un GLB ausente o un fallo de
WebGL no impiden descargar STEP/CSV. Se reconoce tanto `bom_csv` como `csv`.
Los enlaces son nativos y descargan desde FastAPI, no desde rutas del sistema.

Three.js se carga bajo demanda al existir GLB. Carga geometría real, sin modelos
de muestra; el entorno de iluminación se calcula localmente, sin recursos remotos.
Flechas giran, +/− cambian distancia e Inicio restablece; también hay botones
operables por teclado. Se liberan renderer, controles, geometrías, materiales,
texturas y peticiones al cambiar de modelo o desmontar. No hay autorrotación.
Los GLB con recursos externos referenciados no se admiten: el visor no consulta
terceros. Si WebGL no está disponible, muestra un mensaje y conserva descargas.

## Evidencia y servicios simulados

Los resultados vigentes de Vitest, pytest, TypeScript, build, Ruff y cobertura se
registran en `../docs/hu15-despliegue.md`.
El visor es un módulo diferido (aprox. 161 kB gzip); no se descarga antes de
necesitar una vista GLB.

- Pruebas Vitest: flujo Vue y parser reales. `tests/fakeCadService.ts` es un
  **doble explícito de FastAPI**, solo de pruebas. El renderer WebGL se sustituye
  en pruebas de componentes y está marcado como «Visor WebGL simulado».
- Se prueban validación/foco, ausencia de avance simulado, SSE byte a byte,
  terminales, reinicio/limpieza, carreras, abort, GET/DELETE, timeout, errores,
  respuestas tardías, independencia y ausencia de archivos, motivos como texto
  y ocultamiento de direcciones/claves en mensajes de servicio.
- Integración comprobada en Chrome con build de producción y FastAPI/SSE reales:
  **traductor y modelo simulados**, motor CAD/exportación reales. Descargas STEP,
  GLB y CSV devuelven bytes; GLB renderizado con WebGL y controles de teclado.
  Cancelación pendiente y salida local confirmada se observaron por separado.
  No se probó disponibilidad de Gemini/llama.cpp ni cancelación de esos proveedores.
- A 1280 y 768 px se comprobaron estado vacío, éxito y declinación: cero elementos
  fuera de límites horizontales. Tab, foco visible de 3 px y controles del visor
  funcionan en Chrome. No se afirma validación de lectores de pantalla ni de
  otros navegadores. Contraste de tokens: texto ≥6.31:1, bordes/foco ≥3.39:1.

Límites heredados: retención de trabajos en memoria de un proceso, archivos
indisponibles por ID tras expulsión/reinicio y operaciones bloqueantes que no se
interrumpen inmediatamente. Véase `../docs/hu15-sse.md`.
