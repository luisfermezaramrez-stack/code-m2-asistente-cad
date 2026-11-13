# HU-08 — Seguimiento de tareas: Interfaz Gradio

## 1. Implementación de la interfaz

- [x] Implementar la interfaz con Gradio Blocks.
- [x] Incorporar formulario para solicitudes técnicas en español.
- [x] Conectar la interfaz con el endpoint `POST /generar`.
- [x] Incorporar visor 3D para archivos GLB.
- [x] Habilitar descargas STEP y CSV.
- [x] Mostrar la advertencia de diseño preliminar.
- [x] Validar solicitudes entre 1 y 1000 caracteres.
- [x] Implementar mensajes de error y declinación.
- [x] Impedir el acceso a archivos fuera de `outputs/`.

## 2. Correcciones solicitadas en la revisión

### B1 — Arranque de Gradio en Docker

- [x] Crear el servicio `m2-cad-ui` en Docker Compose.
- [x] Publicar el puerto 7860 desde el servicio de interfaz.
- [x] Comprobar que el contenedor inicia.
- [x] Verificar respuesta HTTP 200 con `curl -I http://localhost:7860`.

### B2 — Configuración de red

- [x] Incorporar `M2_UI_HOST`.
- [x] Incorporar `M2_UI_PORT`.
- [x] Configurar `0.0.0.0` para Docker.
- [x] Conservar `127.0.0.1` como valor predeterminado local.

### B3 — Directorio de resultados

- [x] Crear `outputs/` al construir la interfaz.
- [x] Configurar el volumen compartido en Docker Compose.
- [x] Verificar que un archivo creado desde Gradio aparece en el host.
- [x] Confirmar el mismo origen y destino de montaje para ambos servicios.
- [ ] Verificar el acceso al volumen desde FastAPI en ejecución.

### B4 — Mensajes de conexión

- [x] Eliminar el puerto 8000 fijo del mensaje.
- [x] Utilizar la dirección configurada mediante `M2_API_URL`.
- [x] Agregar prueba automatizada del mensaje.

## 3. Mejoras adicionales

### N1 — Dependencias

- [x] Restringir Gradio a `>=4.0,<7`.
- [x] Preparar la dependencia local ConstraintKit.
- [x] Ejecutar la actualización de dependencias.
- [ ] Documentar la versión exacta de Gradio utilizada.

### N2 — Especificaciones y evidencias

- [x] Crear `spec.md`.
- [x] Crear `plan.md`.
- [x] Crear `tasks.md`.
- [ ] Crear `evidence.md`.
- [ ] Incorporar la evidencia del despliegue Docker.
- [ ] Documentar las pruebas funcionales en Chrome y Firefox.
- [ ] Adjuntar las capturas correspondientes.

### N3 — Cobertura automatizada

- [x] Probar validaciones de entrada.
- [x] Probar respuestas HTTP y errores de conexión.
- [x] Probar declinaciones justificadas.
- [x] Probar archivos STEP y GLB faltantes.
- [x] Probar protección de rutas.
- [x] Probar creación de `outputs/`.
- [x] Probar compatibilidad con `bom_csv`.
- [x] Probar declinaciones HTTP 422.
- [x] Superar el mínimo de cobertura del 70 %.

### N4 — Timeout configurable

- [ ] Incorporar `M2_API_TIMEOUT` como variable de entorno.
- [ ] Documentar y probar su comportamiento.

## 4. Criterios de aceptación

| Criterio | Estado | Pendiente |
|---|---|---|
| AC1 — Descarga en máximo 3 clics | Validado con simulaciones | Verificación con archivos reales |
| AC2 — Declinación con motivo | Validado con pruebas | Verificación funcional |
| AC3 — Advertencia preliminar visible | Validado | Ninguno identificado |
| AC4 — Cinco solicitudes en Chrome y Firefox | Pendiente | Ejecución y capturas |
| AC5 — STEP disponible sin GLB | Validado con pruebas | Verificación con archivos reales |

## 5. Validación final

- [ ] Ejecutar toda la batería de pruebas del repositorio.
- [ ] Ejecutar Ruff sobre `src/` y `tests/`.
- [ ] Validar la integración completa Gradio–FastAPI–pipeline.
- [ ] Comprobar la generación y descarga de archivos CAD reales.
- [ ] Ejecutar las cinco solicitudes de prueba en Chrome.
- [ ] Ejecutar las cinco solicitudes de prueba en Firefox.
- [ ] Completar `evidence.md` con resultados reproducibles.
- [ ] Crear un nuevo Pull Request hacia `develop`.
- [ ] Solicitar revisión de Luis.

## 6. Estado general

La interfaz está implementada y las pruebas automatizadas han superado el requisito mínimo de cobertura.

Se ha verificado el arranque independiente de Gradio en Docker con respuesta HTTP 200 y la configuración del volumen compartido.

**HU-08 todavía no está cerrada.** Falta completar las pruebas de extremo a extremo, documentar las evidencias y verificar los criterios de aceptación restantes antes de solicitar la aprobación definitiva.
