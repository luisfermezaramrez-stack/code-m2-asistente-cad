# SPEC-061 · HU-60 — Proceso compacto y orden vertical al 100 % (refactor)

- **ID**: SPEC-061
- **Historia**: #166 (HU-60) · 2 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58 a HU-61 en un solo PR)
- **Estado**: Spec-first · en revisión (PR #171 / #172)
- **Ajusta**: el layout de paneles de [SPEC-039](../039-hu-38-app-shell/spec.md) en la vista de
  nueva solicitud. Quinta iteración tras la revisión visual.

## Problema y contexto

La vista de nueva solicitud nació como una rejilla de dos columnas: la descripción a la
izquierda (`24rem`) y, a la derecha, el proceso, la vista 3D y las descargas. Con la
descripción y las etapas de la generación en columnas distintas, el recorrido natural —escribir
qué quiero, generar, ver el avance, mirar la pieza, descargar— quedaba repartido en dos ejes y
obligaba a saltar de columna en cada paso.

Las dos iteraciones anteriores movieron el proceso a la columna de la descripción y después lo
compactaron dentro de su panel. Falta la última pieza: **una sola columna**, con las tres cards
al 100 % del ancho, en el orden en que el usuario las usa.

## Historia de usuario

**Como** usuario que describe una pieza, **quiero** recorrer la vista de arriba hacia abajo en
una sola columna —descripción con su proceso, vista 3D y archivos—, **para** seguir el trabajo
sin saltar entre columnas.

## Requisitos

### Funcionales

- **RF-1**: la vista usa una sola columna; cada card ocupa el 100 % del ancho disponible del
  contenedor.
- **RF-2**: el orden del documento es: (1) «Especifica la pieza que necesitas», (2) «Vista 3D», (3) «Archivos
  de la pieza».
- **RF-3**: la card «Proceso» es una card propia, hermana de «Especifica la pieza que necesitas» y separada
  de ella, y se compacta al máximo: tipografía `--text-small`, `padding` y separaciones
  reducidos, estado y etapas sin relleno sobrante.
- **RF-4**: en la primera fila, «Especifica la pieza que necesitas» ocupa el 75 % del ancho y «Proceso» el
  25 %; por debajo de 900 px las dos cards se apilan (descripción y luego proceso), sin cambiar
  el orden de sus contenidos.
- **RF-8**: la card «Proceso» mide lo mismo que la card «Especifica la pieza que necesitas» en
  su fila, aunque su contenido sea más corto; su contenido se alinea arriba y el aire sobrante
  queda abajo.
  presentes y legibles; sólo cambia su densidad.
- **RF-9**: el título de la primera card nombra la acción del usuario («Especifica la pieza
  que necesitas») en lugar de la tarea del sistema («Describe tu pieza»).
- **RF-5**: no cambia ningún contenido, etiqueta, atributo ARIA ni comportamiento de las cards:
  sólo su posición y su ancho. La región `aria-live` del estado y la lista de etapas siguen
  anunciando lo mismo.
- **RF-6**: la navegación por teclado conserva el orden del documento: descripción, opciones de
  espera, acciones de la solicitud, acciones de espera, estado y etapas, visor 3D y descargas.

### No funcionales

- **RNF-1**: el layout usa los tokens existentes (`--space-*`, `--text-small`,
  `--border-width`, `--radius-panel`); no se agregan valores nuevos ni estilos en línea.
- **RNF-2**: se retiran las reglas de rejilla que quedan sin uso (`.stack` y el token
  `--request-column`) para no dejar CSS ni tokens muertos.
- **RNF-3**: el cambio no altera el número de peticiones ni el estado de la generación, que
  vive en el shell (`useGeneration`).

## Criterios de aceptación

### AC1 — Orden vertical de las cards

- **Dado** la vista de nueva solicitud
- **Cuando** se inspecciona el orden del documento
- **Entonces** las cards aparecen como «Especifica la pieza que necesitas», «Vista 3D» y «Archivos de la
  pieza», en ese orden.

### AC2 — Ancho completo

- **Dado** la vista en escritorio y en un ancho de 480 px
- **Cuando** se mide cada card
- **Entonces** las tres ocupan el 100 % del ancho del contenedor y ninguna comparte fila con
  otra.

### AC3 — Proceso como card propia y compacta

- **Dado** la vista de nueva solicitud en escritorio
- **Cuando** se mide la primera fila
- **Entonces** «Especifica la pieza que necesitas» ocupa el 75 % del ancho, «Proceso» el 25 %, son dos cards
  separadas con su propio borde y la card de proceso usa tipografía pequeña y espaciado
  reducido, sin eliminar estado, etapas ni ayudas.

### AC6 — Una columna por debajo de 900 px

- **Dado** un ancho de 900 px o menos
- **Cuando** se recorre la vista
- **Entonces** las cards «Especifica la pieza que necesitas» y «Proceso» se apilan en ese orden, seguidas de la
  vista 3D y de los archivos.

### AC4 — Sin cambios de contenido

- **Dado** cada card antes y después del cambio
- **Cuando** se comparan sus textos, estados y atributos de accesibilidad
- **Entonces** son idénticos; sólo cambió la posición y el ancho.

### AC5 — Sin estilos muertos

- **Dado** el repositorio tras el cambio
- **Cuando** se busca `--request-column` y la clase `.stack`
- **Entonces** no aparecen en `frontend/src`.

### AC7 — Mismo alto en la fila

- **Dado** la vista de nueva solicitud en escritorio
- **Cuando** se comparan las alturas de «Especifica la pieza que necesitas» y «Proceso»
- **Entonces** ambas cards miden lo mismo, con el contenido del proceso alineado arriba.

## Fuera de alcance

- Rediseñar el contenido de las cards o de las etapas informadas.
- Cambiar el visor 3D (SPEC-040) o las descargas (SPEC-037).
- Reordenar los paneles de Historial o de Plantillas.

## Métricas de éxito

- Un solo eje de lectura en la vista de nueva solicitud.
- Cero reglas y tokens de rejilla sin consumidores.
