# HU-36 — Evidencias de implementación

**Fecha:** 21 de noviembre de 2026  
**Issue:** #96  
**Especificación:** SPEC-037  
**Rama:** `feature/hu-36-endurecimiento-descargas`

## 1. Implementación

Se implementaron controles de seguridad para las descargas CAD:

- Tokens HMAC-SHA256 asociados al identificador de solicitud.
- Expiración configurable de las credenciales.
- Validación estricta del formato UUID.
- Protección de las descargas STEP, GLB y CSV mediante HTTP GET y HEAD.
- Integración de tokens con el frontend Vue y el flujo SSE.
- Actualización de cabeceras CORS.

## 2. Resultados de las pruebas

| Validación | Resultado |
|---|---|
| Pytest: seguridad e integración HTTP | 34 aprobadas |
| Vitest: frontend Vue | 50 aprobadas |
| Compilación Vue y TypeScript | Exitosa |
| Ruff: análisis estático | Sin errores |
| Ruff: formato | 5 archivos correctamente formateados |
| Git: comprobación de espacios | Sin errores |

## 3. Criterios de aceptación

- **AC1:** pruebas de autorización mediante tokens válidos, ausentes, incorrectos y ajenos.
- **AC2:** pruebas de expiración con respuesta HTTP 410.
- **AC3:** pruebas de UUID inválidos con respuesta HTTP 422.

## 4. Entorno y limitaciones

Las pruebas Python se ejecutaron en macOS utilizando una simulación temporal de `constraint_kit`, sin GPU ni llamadas a DeepSeek.

Se registró una advertencia no bloqueante de compatibilidad entre Starlette y HTTPX.

No se ha realizado una prueba integral del despliegue Docker ni una verificación completa del pipeline CAD real.

La configuración de `M2_DOWNLOAD_SECRET` en el entorno de despliegue y la ejecución de la integración continua quedan pendientes de validación.

## 5. Conclusión

Los resultados obtenidos respaldan los controles de seguridad implementados y la compatibilidad de los componentes cubiertos por las pruebas. La aceptación definitiva requiere revisión del Pull Request y validación de las condiciones pendientes.