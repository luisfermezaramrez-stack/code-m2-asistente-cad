# SPEC-065 · HU-64 — Quitar el atajo «Ver la pieza en el visor 3D» (refactor)

- **ID**: SPEC-065
- **Historia**: #173 (HU-64) · 1 SP · Etiquetas: Frontend, refactor
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-64-sin-atajo-visor` (desde `main`, donde el atajo ya está publicado)
- **Estado**: Spec-first · implementada en local, pendiente de PR
- **Supera**: [SPEC-064](../064-hu-63-plantillas-y-atajo-visor/spec.md) en RF-5 y RF-6 (el atajo y
  su anclaje). El resto de SPEC-064 sigue vigente.

## Problema y contexto

SPEC-064 agregó, al pulsar «Generar pieza», un enlace «Ver la pieza en el visor 3D» dentro de la
card de la solicitud. Con el layout vigente —una sola columna y el orden «Especifica la pieza que
necesitas» → «Vista 3D» → «Archivos de la pieza»— ese atajo no aporta un camino nuevo: el visor
está a un scroll normal de distancia y aparece inmediatamente debajo de la card donde se generó.

En cambio, suma cosas que mantener y que se pueden romper:

- Un estado más en la vista (el enlace aparece en cuanto hay trabajo), que compite con la acción
  primaria «Generar pieza».
- Un anclaje artificial: `id="vista-3d"`, `ref="visor"`, `tabindex="-1"`, `scroll-margin-top` y
  una función `verVisor()` que sólo existen para ese enlace.
- Una prueba dedicada y una clase `.ver-visor` en el CSS global.

La acción primaria de la card debe ser generar; el resultado se lee bajando.

## Historia de usuario

**Como** usuario que acaba de pedir una pieza, **quiero** que la card de la solicitud termine en
la acción de generar, **para** que la pantalla tenga una sola acción primaria y el resultado se
lea en el orden natural de la página.

## Requisitos

### Funcionales

- **RF-1**: la card «Especifica la pieza que necesitas» no contiene ningún enlace ni botón que
  lleve al visor 3D. Termina en las acciones de la solicitud y, cuando corresponde, en las
  acciones de espera.
- **RF-2**: se retiran todos los restos del atajo, sin dejar código ni atributos sin uso:
  `verVisor()`, `ref="visor"`, `id="vista-3d"`, `tabindex="-1"`, la regla `.ver-visor` y
  `#vista-3d { scroll-margin-top }` de `style.css`, y la prueba del atajo.
- **RF-3**: la card «Vista 3D» conserva su título, el visor GLB, el mensaje de estado vacío
  («Aún no hay una pieza» / «Vista 3D no disponible») y su comportamiento de descarga.
- **RF-4**: el resto de la vista de solicitud no cambia: ni textos, ni etiquetas, ni
  identificadores de campo, ni atributos ARIA, ni el orden de los paneles.
- **RF-5**: se retira la prueba `ofrece ir al visor 3D con un clic al generar`; las demás pruebas
  de generación, tema, acceso y navegación siguen pasando sin cambios.

### No funcionales

- **RNF-1**: sin estilos ni atributos muertos (mismo criterio que SPEC-060 RNF-1 y SPEC-061
  RNF-2).
- **RNF-2**: el número de peticiones y el estado de la generación no cambian: sigue viviendo en
  el shell (`useGeneration`).

## Criterios de aceptación

### AC1 — Sin atajo en la card de la solicitud

- **Dado** una solicitud enviada, en curso o terminada
- **Cuando** se inspecciona la card «Especifica la pieza que necesitas»
- **Entonces** no existe ningún enlace `#vista-3d` ni texto «Ver la pieza en el visor 3D».

### AC2 — Sin restos del anclaje

- **Dado** el repositorio tras el cambio
- **Cuando** se busca `vista-3d`, `verVisor` y `.ver-visor` en `frontend/src` y `frontend/tests`
- **Entonces** no aparecen.

### AC3 — El visor sigue completo

- **Dado** una pieza verificada con GLB
- **Cuando** se baja hasta la card «Vista 3D»
- **Entonces** el visor renderiza la pieza y, sin GLB, se ve el mensaje de estado vacío
  correspondiente.

### AC4 — Suite sin la prueba retirada

- **Dado** el frontend tras el cambio
- **Cuando** se ejecuta la suite
- **Entonces** pasa completa sin la prueba del atajo y con las pruebas de generación intactas.

## Fuera de alcance

- Mover, redimensionar o plegar la card «Vista 3D».
- Reemplazar el atajo por otro mecanismo (pestaña, botón flotante, scroll automático al
  terminar, modal de resultado). Si más adelante se quiere, va en su propia spec.
- Tocar la sección de plantillas o su resultado.

## Métricas de éxito

- Cero referencias al ancla del visor en el código del frontend.
- Una sola acción primaria por estado en la card de la solicitud.
