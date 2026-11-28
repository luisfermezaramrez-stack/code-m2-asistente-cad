# SPEC-061 · HU-60 — La card de proceso bajo la descripción de la pieza (refactor)

- **ID**: SPEC-061
- **Historia**: HU-60 · 1 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58, HU-59 y HU-60 en un solo PR)
- **Estado**: Spec-first · implementada en local, pendiente de PR
- **Ajusta**: el orden de paneles de [SPEC-039](../039-hu-38-app-shell/spec.md) en la vista de
  nueva solicitud.

## Problema y contexto

En `frontend/src/views/NewRequestView.vue` la columna izquierda contiene sólo el panel
«Describe tu pieza» (líneas 41-62) y la columna derecha arranca con la card «Proceso»
(líneas 63-76), seguida de «Vista 3D» (77-84) y «Archivos de la pieza» (85-97).

El resultado es que el estado del trabajo que el usuario acaba de pedir aparece **al lado** de
la descripción, no debajo: al enviar la solicitud, la mirada tiene que viajar al margen derecho
y el panel de descripción queda como un bloque cerrado sin continuación. La card de proceso
pertenece al pedido —describe qué le pasó a esa descripción—, así que su lugar es
inmediatamente debajo, en la misma columna y con el mismo ancho de lectura. La vista 3D y las
descargas sí son resultados: se quedan en la columna lateral.

## Historia de usuario

**Como** usuario que envía una descripción, **quiero** ver el proceso de mi solicitud justo
debajo de la descripción que escribí, **para** seguir el avance sin buscar en otra columna.

## Requisitos

### Funcionales

- **RF-1**: la card «Proceso» se renderiza en la columna de la descripción, inmediatamente
  después del panel «Describe tu pieza», y comparte su ancho.
- **RF-2**: «Vista 3D» y «Archivos de la pieza» permanecen en la columna lateral, en ese orden.
- **RF-3**: en pantallas de 900 px o menos, donde la rejilla pasa a una sola columna, el orden
  de lectura es descripción → proceso → vista 3D → archivos.
- **RF-4**: no cambia ningún contenido, etiqueta, atributo ARIA ni comportamiento de los
  paneles: sólo su posición en el documento. La región `aria-live` de «Proceso» sigue
  anunciando el mismo estado.
- **RF-5**: la navegación por teclado conserva el orden del documento: descripción y opciones
  de espera, acciones de la solicitud, acciones de espera y consulta, y luego el resto.

### No funcionales

- **RNF-1**: la rejilla se mantiene con los tokens existentes (`--request-column`, `.workspace`,
  `.stack`); no se agregan valores de layout nuevos ni estilos en línea.
- **RNF-2**: el cambio no altera el número de peticiones ni el estado de la generación, que
  vive en el shell (`useGeneration`).

## Criterios de aceptación

### AC1 — Proceso bajo la descripción

- **Dado** la vista de nueva solicitud
- **Cuando** se inspecciona el orden de los paneles
- **Entonces** «Proceso» es el panel inmediatamente siguiente a «Describe tu pieza» y ambos
  están en la misma columna.

### AC2 — Resultados en la columna lateral

- **Dado** la vista de nueva solicitud en escritorio
- **Cuando** se envía una solicitud y llega una pieza
- **Entonces** «Vista 3D» y «Archivos de la pieza» aparecen en la columna lateral, después de
  la columna que contiene descripción y proceso.

### AC3 — Una sola columna en móvil

- **Dado** un ancho de 900 px o menos
- **Cuando** se recorre la vista
- **Entonces** el orden vertical es descripción, proceso, vista 3D y archivos.

### AC4 — Sin cambios de contenido

- **Dado** el panel «Proceso» antes y después del cambio
- **Cuando** se comparan sus textos, estados y atributos de accesibilidad
- **Entonces** son idénticos; sólo cambió la posición.

## Fuera de alcance

- Rediseñar el contenido de la card de proceso o de las etapas informadas.
- Cambiar el visor 3D (SPEC-040) o las descargas (SPEC-037).
- Reordenar los paneles de Historial.

## Métricas de éxito

- El panel de proceso es el siguiente elemento del documento tras la descripción.
- Cero cambios en el DOM interno de cada panel.
