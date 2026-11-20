# SPEC-038 · HU-37 — Historial de solicitudes en la UI

- **ID**: SPEC-038
- **Historia**: #97 (HU-37) · 3 SP · Etiquetas: Frontend, Backend · Hito: M4
- **Planificación**: Ola 2 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-031](../031-hu-30-persistencia-registro/spec.md)
- **Rama**: `feature/hu-37-historial-ui`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

La interfaz Vue sólo muestra la solicitud en curso: no hay `localStorage` ni vista de
historial en `frontend/src`. Sin embargo, el registro de solicitudes **ya existe** en el
servidor:

1. `src/m2_cad/registro.py:29` fija `data/registro.csv` como ruta por defecto del
   registro persistente.
2. `src/m2_cad/api.py:222-231` expone `GET /registros/{identificador}`, que devuelve una
   fila existente, y `src/m2_cad/api.py:234-254` enlaza su STEP incluso tras reiniciar
   los trabajos.

El backend tiene dos límites: esta historia resuelve el primero y declara el segundo:

- **No existe endpoint de listado**: la única consulta es `GET /registros/{identificador}`
  (`api.py:222-231`), que exige conocer el id.
- **Sólo el STEP es re-descargable** de una solicitud pasada (`api.py:234-255`). El GLB y
  el CSV se sirven desde `/generaciones/{solicitud_id}/archivos/{formato}`, que exige el
  trabajo vivo en `GestorTrabajos` (`api.py:520-531`) y se pierde al reiniciar. Sus rutas
  sí quedan en la columna `resultado` del registro (`api.py:477-480`), pero ninguna ruta
  las sirve desde allí.

Falta un listado consultable y una vista que permita volver a una solicitud anterior.
La persistencia transaccional de SPEC-031 es la fuente de datos de esta historia; el
cliente no debe convertirse en una copia autoritativa (borrador 26 del backlog,
"datos desde el backend, no caché local").

## Historia de usuario

**Como** usuario del asistente, **quiero** ver, filtrar y reabrir mis solicitudes
anteriores, **para** recuperar una pieza o una declinación sin repetir la descripción ni
gastar otra llamada al modelo.

## Requisitos

### Funcionales

- **RF-1**: una vista de historial lista las solicitudes registradas, obtenidas del
  backend (persistencia de SPEC-031).
- **RF-2**: el listado se puede filtrar (Supuesto: al menos por resultado —construida o
  declinada— y por texto de la descripción).
- **RF-3**: al reabrir una solicitud se reanuda la vista de resultado (estado, motivo de
  declinación y, si el GLB sigue disponible, visor de la pieza).
- **RF-4**: desde la solicitud reabierta se descarga su STEP por
  `/registros/{identificador}/step`; el GLB y el CSV sólo se ofrecen mientras el trabajo
  siga vivo en el servidor.
- **RF-5**: el backend expone un endpoint de listado de solicitudes registradas
  (Supuesto: `GET /registros`, con los filtros de RF-2).

### No funcionales

- **RNF-1**: no hay copia de datos autoritativa en el cliente; cualquier caché local es
  descartable y el backend prevalece.
- **RNF-2**: las pruebas no usan red, API key ni GPU: el backend se simula.
- **RNF-3**: la vista conserva la base de accesibilidad existente (foco visible,
  anuncios `aria-live`).

## Criterios de aceptación

### AC1 — Persistencia ante recarga

- **Dado** un historial con al menos una solicitud registrada
- **Cuando** se recarga el navegador
- **Entonces** el historial muestra las mismas solicitudes.

### AC2 — Otro equipo

- **Dado** solicitudes registradas desde un navegador
- **Cuando** se abre la interfaz desde otro equipo contra el mismo backend
- **Entonces** el historial muestra esas solicitudes.

### AC3 — El listado usa un endpoint de listado

- **Dado** un backend con varias solicitudes registradas
- **Cuando** se abre el historial
- **Entonces** el cliente obtiene el listado de un endpoint de listado del backend (hoy no
  existe: sólo `GET /registros/{identificador}`), sin recorrer ids conocidos por el
  cliente.

### AC4 — Reabrir y descargar

- **Dado** una solicitud construida en el historial
- **Cuando** se reabre
- **Entonces** se muestra su vista de resultado y su STEP se puede descargar, incluso
  tras reiniciar el servidor.

## Fuera de alcance

- Re-descarga de GLB y CSV de solicitudes cuyo trabajo ya no está vivo: exige servirlos
  desde el registro (posible extensión de este endpoint o de SPEC-031).
- Autenticación y separación de historiales por usuario (SPEC-054).
- Edición iterativa a partir de una solicitud anterior (SPEC-036).
- Cambiar el esquema de persistencia (SPEC-031).

## Métricas de éxito

- Solicitudes reabiertas sin una nueva llamada al modelo.
- Cero datos de historial que existan sólo en el cliente.
