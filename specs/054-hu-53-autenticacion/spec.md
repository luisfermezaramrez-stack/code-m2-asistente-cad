# SPEC-054 · HU-53 — Autenticación y usuarios

- **ID**: SPEC-054
- **Historia**: #113 (HU-53) · 5 SP · Etiquetas: Backend · Hito: M4
- **Planificación**: Ola 3 (opcional) · Tamaño L · Épica: Backend
- **Responsable**: Juan Camilo Pérez
- **Depende de**: [SPEC-037](../037-hu-36-endurecimiento-descargas/spec.md)
- **Rama**: `feature/hu-53-autenticacion`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

La API no autentica a nadie: `POST /generar` (`src/m2_cad/api.py:397-398`), las
consultas, la cancelación y las descargas de `/generaciones/...`
(`src/m2_cad/api.py:495-522`) y la lectura del registro con `GET /registros/{id}` y
`GET /registros/{id}/step` (`src/m2_cad/api.py:222-235`, ambas de sólo lectura) están
abiertas a cualquier cliente que alcance el servicio.
La única restricción es CORS con orígenes exactos (`src/m2_cad/web.py:14-31`). Esto es
aceptable en despliegue local, pero no en uno público (SPEC-048).

El ítem 35 del borrador se bajó a la ola 3: el mínimo de seguridad (endurecimiento de
artefactos y descargas) va en SPEC-037, de la que depende esta spec
(`docs/backlog-v2.md` §7).

## Historia de usuario

**Como** responsable del servicio, **quiero** que sólo usuarios autenticados generen y
descarguen piezas, **para** controlar el acceso y el costo de un despliegue público.

## Requisitos

### Funcionales

- **RF-1**: los endpoints de generación, consulta, cancelación y descarga exigen un
  usuario autenticado; `/health` queda abierto.
- **RF-2**: mecanismo de autenticación. Supuesto: proveedor externo OIDC o sesión con
  cookie segura; se decide en `plan.md`.
- **RF-3**: cada solicitud y su registro quedan asociados al usuario que la creó.
- **RF-4**: un usuario sólo consulta, cancela y descarga sus propias solicitudes.
- **RF-5**: la UI ofrece iniciar y cerrar sesión y muestra el usuario activo.

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU; el proveedor de identidad se simula.
- **RNF-2**: credenciales y secretos sólo por entorno, nunca versionados.
- **RNF-3**: el modo local sin autenticación sigue disponible de forma explícita para
  desarrollo (Supuesto: variable de entorno documentada).

## Criterios de aceptación

### AC1 — Acceso anónimo rechazado

- **Dado** la autenticación activada
- **Cuando** un cliente sin credenciales llama a `POST /generar`
- **Entonces** recibe 401 y no se crea ninguna solicitud.

### AC2 — Aislamiento entre usuarios

- **Dado** una solicitud creada por el usuario A
- **Cuando** el usuario B intenta consultarla o descargar sus archivos
- **Entonces** recibe 404 o 403 sin revelar su contenido.

### AC3 — Trazabilidad

- **Dado** una solicitud de un usuario autenticado
- **Cuando** se consulta su registro
- **Entonces** el registro identifica al usuario.

### AC4 — Salud abierta (AC de no regresión)

- **Dado** la autenticación activada
- **Cuando** se consulta `/health`
- **Entonces** responde 200 sin credenciales.
- Hoy ya se cumple (`src/m2_cad/api.py:54-57`): es una prueba de no regresión que fija que
  la autenticación no cierre `/health`, no trabajo nuevo.

## Fuera de alcance

- Roles y permisos finos, organizaciones o facturación.
- Topes de costo por usuario (SPEC-033).
- Despliegue en la nube (SPEC-048).

## Métricas de éxito

- 0 endpoints de datos accesibles sin autenticación cuando está activada.
- Pruebas de aislamiento entre usuarios en verde en CI.
