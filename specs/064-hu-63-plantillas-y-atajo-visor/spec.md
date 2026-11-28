# SPEC-064 · HU-63 — Plantillas legibles, sección en cards y atajo al visor 3D (refactor)

- **ID**: SPEC-064
- **Historia**: #169 (HU-63) · 2 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58 a HU-63 en un solo PR)
- **Estado**: Spec-first · en revisión (PR #170)
- **Ajusta**: la sección de plantillas de [SPEC-050](../050-hu-49-plantillas-parametrizadas/spec.md)
  y añade un atajo en la vista de nueva solicitud.

## Problema y contexto

**1. El texto del botón desaparece al elegir una plantilla.** `TemplatesView.vue` marcaba el
botón presionado con `aria-pressed` y una regla scoped
`.plantilla button[aria-pressed='true'] { color: var(--color-accent) }`, mientras `style.css`
aplica desde HU-50 `button[aria-pressed='true'] { background: var(--color-accent); color:
var(--color-on-accent) }`. Vue agrega `[data-v-…]` al selector scoped, que gana en
especificidad: el fondo queda accent (regla global) y el texto también accent (regla scoped),
de modo que «Usar «Placa con agujeros»» se vuelve **invisible** al pulsarlo. El estado también
dependía sólo del color, así que no había otra señal.

**2. La sección no seguía la jerarquía visual del resto.** La lista de plantillas eran cards,
pero el formulario de parámetros y el resultado eran bloques sueltos sobre el fondo de la
página, sin superficie propia ni separación del listado.

**3. Ver la pieza exigía buscar el visor.** Después de «Generar pieza», el usuario tenía que
desplazarse a mano hasta la card «Vista 3D», que en el orden vertical actual queda debajo.

## Historia de usuario

**Como** usuario que reutiliza una plantilla, **quiero** que el botón de elegirla siga siendo
legible y que la sección se lea como una secuencia clara, **para** ajustar medidas y ver el
resultado sin perder el estado ni buscar el visor.

## Requisitos

### Funcionales

- **RF-1**: el botón de una plantilla elegida conserva su etiqueta visible («Usar «nombre»»),
  con fondo `--color-accent` y texto `--color-on-accent`; ninguna regla puede dejar texto y
  fondo con el mismo token.
- **RF-2**: el estado de elección no depende sólo del color: la card elegida muestra el chip
  «Elegida» y su borde cambia al color de acento.
- **RF-3**: el formulario de parámetros y el resultado se presentan como cards con superficie,
  borde y separación propios, en el mismo ritmo visual que el resto del shell.
- **RF-4**: cuando hay plantillas y ninguna está elegida, la sección indica el siguiente paso
  («Elige una plantilla para ajustar sus medidas»).
- **RF-5**: al pulsar «Generar pieza» en la vista de nueva solicitud aparece un atajo «Ver la
  pieza en el visor 3D» que, con un solo clic, lleva al visor y le deja el foco.
- **RF-6**: el atajo se anuncia como enlace (`href="#vista-3d"`) y funciona también sin
  JavaScript como salto de ancla; la card «Vista 3D» es enfocable (`tabindex="-1"`).
- **RF-7**: no cambia ningún contenido, identificador, etiqueta de campo, `data-test` ni
  comportamiento de la generación desde plantilla (SPEC-050).

### No funcionales

- **RNF-1**: los colores salen de tokens; no se agregan literales en estilos scoped ni globales.
- **RNF-2**: el contraste AA se mantiene en ambos temas para el botón presionado y el chip.
- **RNF-3**: el atajo respeta `prefers-reduced-motion` a través del desplazamiento del navegador
  (no se codifica una animación propia).

## Criterios de aceptación

### AC1 — Botón presionado legible

- **Dado** una plantilla elegida
- **Cuando** se inspecciona su botón
- **Entonces** `aria-pressed` es `true`, la etiqueta conserva el nombre de la plantilla y el
  color del texto no es el mismo token que el fondo.

### AC2 — Estado visible sin depender del color

- **Dado** una plantilla elegida
- **Cuando** se mira su card
- **Entonces** aparece el chip «Elegida» y el borde de la card usa el color de acento.

### AC3 — Sección como secuencia de cards

- **Dado** la sección de plantillas con una plantilla elegida
- **Cuando** se recorre la página
- **Entonces** lista, parámetros y resultado son tres bloques con superficie propia y
  separación consistente.

### AC4 — Atajo al visor con un clic

- **Dado** una solicitud recién enviada desde la vista de nueva solicitud
- **Cuando** se pulsa «Ver la pieza en el visor 3D»
- **Entonces** el foco queda en la card «Vista 3D» y la página se ha desplazado hasta ella.

### AC5 — Sin regresión en plantillas

- **Dado** la suite de pruebas de HU-49
- **Cuando** se ejecuta
- **Entonces** pasa sin cambios: mismos identificadores de campo, mismos rangos, mismos
  `data-test` y mismos mensajes.

## Fuera de alcance

- Cambiar el contrato de `/v1/plantillas` o `/v1/plantillas/{id}/instanciar`.
- Guardar plantillas desde la interfaz (HU-07/HU-37).
- Llevar el visor 3D a la sección de plantillas.

## Métricas de éxito

- Cero estados de interfaz indicados sólo por color.
- Un clic entre «Generar pieza» y el visor 3D.
