# SPEC-038 · HU-37 — Historial de solicitudes en la UI

- **ID**: SPEC-038
- **Historia**: issue por crear · Ola 2 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-031](../031-hu-30-persistencia-registro/spec.md)
- **Rama**: `feature/hu-37-historial-ui`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §5

## Problema y contexto

La interfaz Vue sólo muestra la solicitud en curso: no hay `localStorage` ni vista de
historial en `frontend/src`. Sin embargo, el registro de solicitudes **ya existe** en el
servidor:

1. `src/m2_cad/registro.py:29` fija `data/registro.csv` como ruta por defecto del
   registro persistente.
2. `src/m2_cad/api.py:222-231` expone `GET /registros/{identificador}`, que devuelve una
   fila existente, y `src/m2_cad/api.py:234-254` enlaza su STEP incluso tras reiniciar
   los trabajos.

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
  declinación o visor de la pieza).
- **RF-4**: desde la solicitud reabierta se descargan sus artefactos disponibles.

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

### AC3 — Sin copia autoritativa en el cliente

- **Dado** un navegador con el almacenamiento local vacío o borrado
- **Cuando** se abre el historial
- **Entonces** el contenido se reconstruye completo desde el backend.

### AC4 — Reabrir y descargar

- **Dado** una solicitud construida en el historial
- **Cuando** se reabre
- **Entonces** se muestra su vista de resultado y sus artefactos se pueden descargar.

## Fuera de alcance

- Autenticación y separación de historiales por usuario (SPEC-054).
- Edición iterativa a partir de una solicitud anterior (SPEC-036).
- Cambiar el esquema de persistencia (SPEC-031).

## Métricas de éxito

- Solicitudes reabiertas sin una nueva llamada al modelo.
- Cero datos de historial que existan sólo en el cliente.
