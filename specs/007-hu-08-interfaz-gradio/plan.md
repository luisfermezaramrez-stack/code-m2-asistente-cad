
# HU-08 — Plan técnico de la interfaz Gradio

## 1. Objetivo

Implementar una interfaz web en Gradio para solicitar diseños
preliminares CAD mediante FastAPI, visualizar archivos GLB y
descargar STEP y CSV.

La interfaz debe funcionar tanto en desarrollo local como en
un entorno desplegado mediante Docker Compose.

## 2. Arquitectura

El sistema utiliza servicios independientes:

1. Gradio recibe la descripción técnica del usuario.
2. Gradio envía una solicitud HTTP POST a FastAPI.
3. FastAPI valida la solicitud y ejecuta el pipeline CAD.
4. El pipeline genera los archivos correspondientes o
   comunica una declinación.
5. FastAPI devuelve el resultado a Gradio.
6. Gradio presenta el modelo 3D, los archivos disponibles
   y los mensajes correspondientes.

### Componentes

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Interfaz | src/m2_cad/interfaz.py | Formulario, visualización y descargas |
| API | src/m2_cad/api.py | Validación y procesamiento HTTP |
| Pipeline | src/m2_cad/pipeline.py | Generación y verificación CAD |
| Registro | src/m2_cad/registro.py | Trazabilidad de solicitudes |
| Despliegue | docker-compose.yml | Orquestación de servicios |

## 3. Contrato de integración

### Solicitud

Endpoint: POST /generar

```json
{
  "texto": "Placa de 120 mm con cuatro agujeros"
}
```

### Generación exitosa

Gradio admite los campos:

- step: ruta del archivo STEP.
- glb: ruta del archivo GLB.
- bom_csv: ruta del archivo CSV de materiales.

Por compatibilidad con las pruebas existentes, también
admite la clave csv.

### Declinaciones

FastAPI comunica las piezas declinadas mediante HTTP 422,
con un motivo en el campo detail.

Gradio identifica el prefijo "Pieza declinada:", presenta
la justificación y oculta los componentes de descarga.

### Archivos faltantes

Si no existe GLB, se oculta el visor 3D.

Si existe STEP, su descarga continúa disponible aunque
el GLB no pueda visualizarse.

Si falta STEP, la interfaz presenta un aviso explícito.

## 4. Configuración

Variables de entorno:

| Variable | Valor local predeterminado | Función |
|---|---|---|
| M2_API_URL | http://127.0.0.1:8000 | Dirección de FastAPI |
| M2_UI_HOST | 127.0.0.1 | Dirección de escucha de Gradio |
| M2_UI_PORT | 7860 | Puerto de la interfaz |
| M2_API_TIMEOUT | 70 segundos | Tiempo máximo de espera HTTP |

El tiempo de espera de 70 segundos es el valor utilizado
actualmente por la interfaz. Su parametrización mediante
M2_API_TIMEOUT es una mejora prevista.

## 5. Despliegue mediante Docker Compose

Se utilizan dos servicios de aplicación:

### m2-cad

- Ejecuta FastAPI mediante Uvicorn.
- Publica el puerto 8000.
- Se comunica con el servicio del modelo CAD.

### m2-cad-ui

- Ejecuta Gradio.
- Publica el puerto 7860.
- Se conecta a FastAPI mediante http://m2-cad:8000.
- Utiliza M2_UI_HOST=0.0.0.0 para aceptar conexiones
  desde fuera del contenedor.

### Volumen compartido

Ambos servicios montan:

./outputs:/app/outputs

Esto permite acceder desde Gradio a los archivos
generados por el servicio CAD.

El directorio outputs se crea al construir la interfaz.

## 6. Seguridad y controles

- Longitud permitida de solicitudes: 1 a 1000 caracteres.
- No se admiten entradas vacías.
- Los archivos solo se ofrecen desde outputs/.
- Se verifican existencia y extensión de archivos.
- No se exponen rutas externas al directorio permitido.
- Los errores HTTP se presentan mediante mensajes controlados.
- Se informa que los diseños son preliminares.

## 7. Estrategia de pruebas

### Pruebas automatizadas

Herramientas: Pytest, pytest-cov y Ruff.

Se verifican:

- Validación de solicitudes.
- Comunicación HTTP con FastAPI.
- Generación y declinación simuladas.
- Compatibilidad con las respuestas del pipeline.
- Disponibilidad independiente de STEP y GLB.
- Protección de rutas de archivos.
- Mensajes de error y creación de outputs/.

### Pruebas de despliegue

Comandos:

```bash
docker compose config --quiet
docker compose up --build --no-deps -d m2-cad-ui
curl -I http://localhost:7860
```

La ejecución aislada de Gradio valida el servicio web,
pero no sustituye la prueba completa del pipeline CAD.

### Pruebas funcionales

Se realizarán cinco solicitudes en Chrome y Firefox.

Se registrarán:

- Descripción utilizada.
- Resultado esperado y obtenido.
- Funcionamiento del visor 3D.
- Disponibilidad de STEP y CSV.
- Número de clics para descargar.
- Capturas de pantalla.
- Errores encontrados.

## 8. Criterios de cierre

HU-08 estará lista para revisión definitiva cuando:

1. Pytest y Ruff terminen sin errores.
2. Se supere la cobertura mínima del 70 %.
3. Docker permita acceder a Gradio por el puerto 7860.
4. Se confirme el funcionamiento del volumen compartido.
5. Se documenten AC1–AC5 con evidencia.
6. Se completen las cinco pruebas en Chrome y Firefox.
7. Se confirme la integración con archivos CAD reales.

Las evidencias y resultados se registran en evidence.md.
