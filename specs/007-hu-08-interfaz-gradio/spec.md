
# HU-08 — Interfaz web con Gradio

## Objetivo

Desarrollar una interfaz web que permita solicitar diseños preliminares
de componentes metálicos auxiliares, consultar el servicio FastAPI,
visualizar modelos 3D y descargar los archivos CAD generados.

## Tecnologías

- Python
- Gradio Blocks
- FastAPI
- Docker Compose

## Criterios de aceptación

### AC1 — Solicitud y descarga
El usuario puede ingresar una descripción técnica y descargar
los archivos generados en un máximo de tres clics.

### AC2 — Declinación justificada
Cuando el pipeline rechaza una solicitud, la interfaz muestra
el motivo y oculta los componentes de descarga.

### AC3 — Advertencia de diseño preliminar
La interfaz muestra una advertencia visible indicando que los
resultados son preliminares y requieren revisión profesional.

### AC4 — Compatibilidad con navegadores
Realizar pruebas de humo con cinco solicitudes en Chrome y
Firefox, registrando resultados y evidencias.

### AC5 — Descarga STEP independiente del GLB
Si el archivo GLB no está disponible, el usuario todavía puede
descargar el archivo STEP, siempre que este se haya generado.

## Integración

La interfaz consume el endpoint POST /generar de FastAPI.

La respuesta de generación puede incluir:
- step: archivo CAD STEP.
- glb: modelo para visualización 3D.
- bom_csv: lista de materiales.

Las declinaciones provenientes del pipeline pueden comunicarse
mediante HTTP 422, incluyendo el motivo en el campo detail.

## Restricciones

- Solicitudes de entre 1 y 1000 caracteres.
- Acceso a archivos limitado al directorio outputs/.
- Configuración del servidor mediante variables de entorno.
- Directorio outputs/ compartido entre FastAPI y Gradio.
- La interfaz no sustituye la validación técnica profesional.
