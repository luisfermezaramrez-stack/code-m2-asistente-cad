# HU-36 — Seguimiento de tareas

## Fase 1. Análisis y planificación

- [x] Revisar SPEC-037 y los criterios AC1–AC3.
- [x] Identificar los endpoints de descarga existentes.
- [x] Revisar el ciclo de vida de trabajos SSE.
- [x] Identificar cambios necesarios en Vue.
- [ ] Confirmar y documentar el diseño técnico.

## Fase 2. Implementación de seguridad

- [ ] Crear `src/m2_cad/seguridad_descargas.py`.
- [ ] Implementar generación de tokens firmados.
- [ ] Asociar tokens a UUID y expiración.
- [ ] Configurar TTL y secreto de firma.
- [ ] Validar firmas sin comparaciones inseguras.
- [ ] Implementar validación estricta de UUID.

## Fase 3. Integración con FastAPI

- [ ] Entregar tokens al crear solicitudes.
- [ ] Proteger `/registros/{identificador}/step`.
- [ ] Proteger `/generaciones/{solicitud_id}/archivos/{formato}` para GET y HEAD.
- [ ] Validar UUID en `/registros/{identificador}`.
- [ ] Devolver HTTP 403 para credenciales inválidas.
- [ ] Devolver HTTP 410 para artefactos expirados.
- [ ] Conservar controles de rutas, MIME y cabeceras.
- [ ] Evitar exposición de tokens en logs, registros y MLflow.

## Fase 4. Integración con Vue

- [ ] Recibir el token desde FastAPI.
- [ ] Conservar el token en memoria.
- [ ] Incorporarlo a las peticiones HEAD.
- [ ] Incorporarlo a las descargas GET.
- [ ] Manejar errores 403 y 410 en la interfaz.

## Fase 5. Pruebas automatizadas

- [ ] AC1: rechazar descargas sin token o con token ajeno.
- [ ] AC2: devolver HTTP 410 para artefactos expirados.
- [ ] AC3: rechazar UUID inválidos sin consultar disco ni registro.
- [ ] Verificar descargas válidas.
- [ ] Verificar la protección contra rutas externas.
- [ ] Comprobar que no se exponen secretos.
- [ ] Ejecutar pruebas de regresión de FastAPI y SSE.
- [ ] Ejecutar pruebas del frontend.
- [ ] Ejecutar Ruff y comprobar la cobertura.

## Fase 6. Entrega

- [ ] Crear `evidence.md` con resultados verificables.
- [ ] Revisar archivos modificados mediante Git.
- [ ] Crear commit de HU-36.
- [ ] Publicar la rama en GitHub.
- [ ] Abrir Pull Request hacia `develop`.
- [ ] Solicitar revisión de Luis.

## Criterios de cierre

- AC1: ninguna descarga exitosa sin token válido.
- AC2: todas las solicitudes de artefactos expirados responden HTTP 410.
- AC3: los identificadores inválidos se rechazan sin consultar archivos.
- Las pruebas no requieren API keys, red externa ni GPU.
- Los componentes existentes conservan su funcionamiento.