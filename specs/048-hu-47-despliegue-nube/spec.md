# SPEC-048 · HU-47 — Despliegue en la nube

- **ID**: SPEC-048
- **Historia**: #107 (HU-47) · 4 SP · Etiquetas: infra · Hito: M4
- **Planificación**: Ola 3 (opcional) · Tamaño L · Épica: Entrega
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-033](../033-hu-32-costo-limites-idempotencia/spec.md),
  [SPEC-037](../037-hu-36-endurecimiento-descargas/spec.md),
  [SPEC-046](../046-hu-45-cola-persistente/spec.md); además
  [SPEC-054](../054-hu-53-autenticacion/spec.md) si el despliegue es público
- **Rama**: `feature/hu-47-despliegue-nube`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6

## Problema y contexto

El empaquetado ya existe: el `Dockerfile` es multi-etapa (build del frontend en
`Dockerfile:2`, vendoreo de constraint-kit en `Dockerfile:11`, imagen final en
`Dockerfile:20`) con `HEALTHCHECK` contra `/health` (`Dockerfile:51-52`) y Uvicorn con
`--workers 1` (`Dockerfile:55`). El despliegue documentado es sólo local con Docker
Compose (HU-10, SPEC-010). Esta spec **no** rehace el empaquetado: cubre despliegue en un
proveedor de nube, TLS, dominio y runbook (ítem 45 del borrador, reformulado).

El servicio no tiene autenticación ni topes de costo hoy; por eso depende de SPEC-033
(costo y límites), SPEC-037 (endurecimiento de descargas) y SPEC-046 (cola persistente,
para no perder trabajos en reinicios). Si el despliegue es público, requiere SPEC-054.

## Historia de usuario

**Como** equipo del proyecto, **quiero** el asistente desplegado en la nube con HTTPS y un
dominio propio, **para** que evaluadores y usuarios lo usen sin instalar nada localmente.

## Requisitos

### Funcionales

- **RF-1**: desplegar la imagen existente en un proveedor de nube. Supuesto: proveedor con
  contenedores gestionados y nivel gratuito o de bajo costo; se elige en `plan.md`.
- **RF-2**: servir el frontend y la API por HTTPS con certificado válido y renovación
  automática, bajo un dominio o subdominio del proyecto.
- **RF-3**: inyectar secretos (API key del LLM, precios, orígenes CORS `M2_CORS_ORIGINS`
  de `src/m2_cad/web.py:14`) desde el gestor del proveedor, nunca desde la imagen.
- **RF-4**: persistir el registro y los trabajos en almacenamiento que sobreviva a
  reinicios (apoyado en SPEC-031 y SPEC-046).
- **RF-5**: runbook de despliegue, rollback y rotación de secretos, enlazado desde el
  runbook operativo de SPEC-030.

### No funcionales

- **RNF-1**: el despliegue usa el `HEALTHCHECK` existente como sonda de vida.
- **RNF-2**: un despliegue público no se habilita sin SPEC-054 y sin los topes de SPEC-033.
- **RNF-3**: las pruebas automatizadas no usan red, API key ni GPU; la verificación del
  entorno desplegado es un paso manual o un job separado documentado.

## Criterios de aceptación

### AC1 — Servicio accesible por HTTPS

- **Dado** la imagen publicada y los secretos configurados
- **Cuando** se despliega con el procedimiento documentado
- **Entonces** `https://<dominio>/health` responde 200 con certificado válido.

### AC2 — Generación de punta a punta

- **Dado** el servicio desplegado
- **Cuando** se envía una solicitud del banco desde la UI
- **Entonces** se recibe la pieza (STEP, GLB y CSV) o una declinación con motivo.

### AC3 — Reinicio sin pérdida

- **Dado** una solicitud en curso
- **Cuando** el proveedor reinicia el contenedor
- **Entonces** la solicitud se reanuda o se informa su estado sin perderse (SPEC-046).

### AC4 — Rollback

- **Dado** una versión desplegada defectuosa
- **Cuando** se sigue el runbook de rollback
- **Entonces** la versión anterior queda en servicio en menos de 15 minutos (Supuesto).

## Fuera de alcance

- Rehacer el `Dockerfile` o el empaquetado multi-etapa.
- Autenticación de usuarios (SPEC-054) y topes de costo (SPEC-033).
- Escalado horizontal con varios workers o réplicas.

## Métricas de éxito

- Disponibilidad observada del endpoint `/health` durante la evaluación.
- Tiempo de despliegue y de rollback medidos con el runbook.
