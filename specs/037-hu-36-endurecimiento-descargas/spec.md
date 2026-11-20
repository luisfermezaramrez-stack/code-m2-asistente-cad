# SPEC-037 · HU-36 — Endurecimiento de artefactos y descargas

- **ID**: SPEC-037
- **Historia**: issue por crear · Ola 1 · Tamaño S · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: —
- **Rama**: `feature/hu-36-endurecimiento-descargas`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §4

## Problema y contexto

Las descargas ya tienen controles básicos, pero no de acceso ni de vigencia:

1. `/generaciones/{solicitud_id}/archivos/{formato}` acepta solo `step`, `glb` y `csv`
   (`src/m2_cad/api.py:520-531`), restringe la ruta a `outputs/` (`api.py:540-549`) y
   fija el tipo MIME por formato (`api.py:550-556`).
2. `/registros/{identificador}/step` entrega el STEP de cualquier fila del registro con la
   misma restricción a `outputs/` (`api.py:234-254`).
3. Ninguna de las dos rutas pide autorización: cualquiera con el UUID descarga el
   artefacto.
4. No hay expiración: el STEP del registro sigue disponible mientras exista en disco, y
   el identificador de `/registros/{identificador}` no se valida como UUID
   (`api.py:222-231`).

Esta spec es el mínimo de seguridad que el backlog separa de la autenticación completa
([SPEC-054](../054-hu-53-autenticacion/spec.md)).

## Historia de usuario

**Como** usuario que genera una pieza, **quiero** que solo quien tiene el token de mi
solicitud pueda descargar sus artefactos y que estos expiren, **para** que conocer o
adivinar un UUID no baste para obtener mis archivos.

## Requisitos

### Funcionales

- **RF-1**: cada solicitud emite un token propio; las descargas exigen ese token.
- **RF-2**: la expiración de artefactos es configurable.
- **RF-3**: un artefacto expirado responde 410.
- **RF-4**: validación estricta del id (formato UUID) y del tipo MIME en toda ruta de
  descarga.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU.
- **RNF-2**: se conservan las cabeceras `Cache-Control: no-store` y
  `X-Content-Type-Options: nosniff` (`api.py:253`, `api.py:555`).
- **RNF-3**: el token no se escribe en el registro ni en MLflow.
- **Supuesto**: el frontend recibe el token en la respuesta de `/generar` y lo envía en
  sus descargas (`frontend/src/api.ts:37`).

## Criterios de aceptación

### AC1 — UUID ajeno sin token

- **Dado** una generación verificada de otra solicitud
- **Cuando** se pide su artefacto con el UUID pero sin su token
- **Entonces** la descarga se rechaza y no se entrega ningún byte del archivo.

### AC2 — Artefacto expirado

- **Dado** un artefacto cuya expiración configurada ya pasó
- **Cuando** se pide con un token válido
- **Entonces** el servicio responde 410.

### AC3 — Validación estricta

- **Dado** un id que no es un UUID o un formato fuera de la allowlist
- **Cuando** se pide la descarga
- **Entonces** el servicio la rechaza sin leer el disco.

## Fuera de alcance

- Autenticación de usuarios y cuentas (SPEC-054).
- Retención y limpieza de `outputs/`
  ([SPEC-031](../031-hu-30-persistencia-registro/spec.md)).

## Métricas de éxito

- 0 descargas exitosas sin token válido en las pruebas.
- 100 % de artefactos expirados respondiendo 410.
