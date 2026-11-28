# SPEC-060 · HU-59 — Retirar «Métricas» y «Ajustes» de la interfaz (refactor)

- **ID**: SPEC-060
- **Historia**: HU-59 · 1 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58, HU-59 y HU-60 en un solo PR)
- **Estado**: Spec-first · implementada en local, pendiente de PR
- **Supera**: los requisitos de navegación de [SPEC-039](../039-hu-38-app-shell/spec.md) y de
  [SPEC-052](../052-hu-51-panorama-metricas/spec.md) (pestaña de métricas), y retira la vista de
  estado de «Ajustes» creada por SPEC-039.
- **Preserva**: la entrada «Plantillas» de [SPEC-050](../050-hu-49-plantillas-parametrizadas/spec.md)
  (HU-49) y el detalle de historial de [SPEC-038](../038-hu-37-historial-ui/spec.md) (HU-37).

## Problema y contexto

La navegación tiene cinco entradas (`frontend/src/App.vue:74-78`): Nueva solicitud, Historial,
Plantillas, Métricas y Ajustes. Dos de ellas no aportan a la tarea del usuario:

- **Ajustes** (`frontend/src/views/SettingsView.vue`) no configura nada: repite estados de
  vista y remite a la cabecera y a Nueva solicitud (`SettingsView.vue:19`). Es un cascarón.
- **Métricas** (`frontend/src/views/MetricsView.vue`) muestra el panorama de MLflow de
  SPEC-052, pero el detalle y la comparación de corridas viven en la UI de MLflow. Su valor
  operativo real no está en la pantalla de trabajo del usuario del asistente.

Con el acceso como primera pantalla (SPEC-059), cada entrada del menú cuesta atención: el
menú debe contener sólo lo que se usa para pedir y revisar piezas.

## Historia de usuario

**Como** usuario autenticado del asistente CAD, **quiero** que el menú muestre sólo las
funciones de la aplicación, **para** llegar a pedir o revisar una pieza sin pasar por pantallas
vacías o de operación interna.

## Requisitos

### Funcionales

- **RF-1**: la navegación principal contiene exactamente tres entradas: «Nueva solicitud»,
  «Historial» y «Plantillas».
- **RF-2**: las rutas `/metricas` y `/ajustes` dejan de existir; navegar a ellas resuelve en
  la vista de ruta no encontrada.
- **RF-3**: se eliminan `frontend/src/views/MetricsView.vue`, `frontend/src/views/SettingsView.vue`
  y `frontend/tests/Metrics.test.ts`, junto con las importaciones de `router.ts` y la función
  `cargarMetricas` de `frontend/src/api.ts`, que queda sin consumidores.
- **RF-4**: la vista de ruta no encontrada deja de mencionar «ajustes» y enumera sólo las
  entradas vigentes (nueva solicitud, historial y plantillas).
- **RF-5**: el endpoint `GET /v1/metricas` y su módulo `m2_cad.metricas` permanecen intactos
  como contrato de la API (`tests/test_api_metricas.py`, `tests/test_metricas.py` sin cambios):
  la retirada es de interfaz, no de backend.
- **RF-6**: la navegación sólo con teclado sigue cubriendo todas las entradas vigentes: Tab y
  Shift+Tab recorren las dos entradas y Enter activa la enfocada.

### No funcionales

- **RNF-1**: no queda código muerto: ningún archivo sin importadores, ninguna exportación sin
  consumidor.
- **RNF-2**: la cobertura de pruebas del frontend se mantiene por encima del umbral del
  proyecto (≥ 70 %) sin bajar el umbral ni excluir archivos.

## Criterios de aceptación

### AC1 — Menú con tres entradas

- **Dado** un usuario autenticado en el shell
- **Cuando** observa la navegación principal
- **Entonces** hay tres enlaces: «Nueva solicitud», «Historial» y «Plantillas», y ninguno dice
  «Métricas» ni «Ajustes».

### AC2 — Rutas retiradas

- **Dado** el usuario en la aplicación
- **Cuando** abre `/metricas` o `/ajustes` por URL
- **Entonces** ve la vista de ruta no encontrada, sin errores de consola ni peticiones a
  `/v1/metricas`.

### AC3 — Navegación por teclado completa

- **Dado** el foco en la navegación principal
- **Cuando** recorre con Tab, Shift+Tab y activa con Enter
- **Entonces** alcanza y activa las tres entradas vigentes, y el skip link sigue siendo
  enfocable.

### AC4 — Backend intacto

- **Dado** el repositorio tras el cambio
- **Cuando** se ejecuta la suite de pruebas del backend
- **Entonces** `test_api_metricas.py` y `test_metricas.py` pasan sin modificarse.

## Fuera de alcance

- Retirar el endpoint `/v1/metricas`, el módulo `metricas` o la spec 052 del catálogo.
- Implementar el contenido real de Historial (SPEC-038).
- Rediseñar la navegación (pestañas laterales, menú colapsable).

## Métricas de éxito

- Tres entradas en el menú; cero archivos de vista sin importadores.
- Cero peticiones a `/v1/metricas` originadas en la SPA.
