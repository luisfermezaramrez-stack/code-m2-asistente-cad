# SPEC-061 · HU-60 — La card de proceso compacta bajo la acción de generar (refactor)

- **ID**: SPEC-061
- **Historia**: HU-60 · 1 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58 a HU-61 en un solo PR)
- **Estado**: Spec-first · implementada en local, pendiente de PR
- **Ajusta**: el orden de paneles de [SPEC-039](../039-hu-38-app-shell/spec.md) en la vista de
  nueva solicitud. Segunda iteración tras la revisión visual: la card pasa a ser compacta y a
  vivir dentro del panel de la descripción.

## Problema y contexto

En `frontend/src/views/NewRequestView.vue` la columna derecha arrancaba con la card «Proceso»
a la altura de «Describe tu pieza»: el estado del trabajo que el usuario acaba de pedir
aparecía **al lado** de la descripción, no debajo, y obligaba a mover la mirada al margen
derecho justo después de pulsar «Generar pieza».

La primera iteración de esta spec la bajó a la columna de la descripción, pero como panel
independiente: seguía siendo un bloque grande, con su propio borde y su propio título, para
un contenido de una línea de estado y, a veces, dos o tres etapas. El proceso pertenece al
botón que lo dispara: va inmediatamente debajo, en el mismo panel, con jerarquía visual menor.

La vista 3D y las descargas sí son resultados: se quedan en la columna lateral.

## Historia de usuario

**Como** usuario que envía una descripción, **quiero** ver el estado del proceso justo debajo
del botón «Generar pieza», **para** confirmar qué está pasando sin perder de vista lo que pedí.

## Requisitos

### Funcionales

- **RF-1**: la card «Proceso» se renderiza dentro del panel «Describe tu pieza», inmediatamente
  después de las acciones de la solicitud y de las acciones de espera, con el mismo ancho que
  el formulario que la dispara.
- **RF-2**: la card es compacta: título de menor jerarquía visual, estado y etapas con
  espaciado reducido, separada del formulario por una línea superior en lugar de un panel
  propio con borde y fondo.
- **RF-3**: «Vista 3D» y «Archivos de la pieza» permanecen en la columna lateral, en ese orden.
- **RF-4**: en pantallas de 900 px o menos, donde la rejilla pasa a una sola columna, el orden
  de lectura es descripción y proceso → vista 3D → archivos.
- **RF-5**: no cambia ningún contenido, etiqueta, atributo ARIA ni comportamiento del panel:
  sólo su posición y su densidad. La región `aria-live` del estado y la lista de etapas siguen
  anunciando lo mismo.
- **RF-6**: la navegación por teclado conserva el orden del documento: descripción, opciones de
  espera, acciones de la solicitud, acciones de espera, y luego estado y etapas.

### No funcionales

- **RNF-1**: la rejilla y la densidad usan los tokens existentes (`--space-*`, `--text-small`,
  `--border-width`); no se agregan valores de layout nuevos ni estilos en línea.
- **RNF-2**: el cambio no altera el número de peticiones ni el estado de la generación, que
  vive en el shell (`useGeneration`).

## Criterios de aceptación

### AC1 — Proceso dentro del panel, bajo la acción

- **Dado** la vista de nueva solicitud
- **Cuando** se inspecciona el orden del documento
- **Entonces** el bloque «Proceso» está dentro del panel «Describe tu pieza» y es el siguiente
  elemento después de las acciones de la solicitud.

### AC2 — Card compacta

- **Dado** la vista de nueva solicitud en escritorio
- **Cuando** se compara la card «Proceso» con el formulario
- **Entonces** ocupa el ancho de la columna, no tiene borde ni fondo de panel propio, y su
  título es más pequeño y de menor contraste que el título del panel.

### AC3 — Resultados en la columna lateral

- **Dado** la vista de nueva solicitud en escritorio
- **Cuando** se envía una solicitud y llega una pieza
- **Entonces** «Vista 3D» y «Archivos de la pieza» aparecen en la columna lateral, fuera del
  panel de la descripción.

### AC4 — Una sola columna en móvil

- **Dado** un ancho de 900 px o menos
- **Cuando** se recorre la vista
- **Entonces** el orden vertical es descripción y proceso, vista 3D y archivos.

### AC5 — Sin cambios de contenido

- **Dado** el bloque «Proceso» antes y después del cambio
- **Cuando** se comparan sus textos, estados y atributos de accesibilidad
- **Entonces** son idénticos; sólo cambió la posición y la densidad.

## Fuera de alcance

- Rediseñar el contenido del proceso o de las etapas informadas.
- Cambiar el visor 3D (SPEC-040) o las descargas (SPEC-037).
- Reordenar los paneles de Historial o de Plantillas.

## Métricas de éxito

- El bloque de proceso es el siguiente elemento del panel tras la acción de generar.
- Cero cambios en el DOM interno del bloque (mismos nodos y atributos).
