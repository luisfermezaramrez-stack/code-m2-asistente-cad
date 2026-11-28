# SPEC-063 · HU-62 — Gradiente de identidad del asistente CAD (refactor)

- **ID**: SPEC-063
- **Historia**: #168 (HU-62) · 1 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58 a HU-62 en un solo PR)
- **Estado**: Spec-first · implementada en local, pendiente de PR
- **Extiende**: la paleta de [SPEC-035](../035-hu-34-sistema-diseno-v2/spec.md) con un gradiente
  de identidad; no cambia ningún color existente.

## Problema y contexto

El shell y la pantalla de acceso usaban superficies planas: la cabecera era texto sobre el
fondo de la página, sin ningún recurso visual que dijera de qué se trata la aplicación. Un
asistente CAD para componentes metálicos puede permitirse una referencia sobria al material y
al plano de trabajo, siempre que no compita con el contenido ni rompa el contraste.

La solución es un **gradiente de identidad** de tonos acero —de gris azulado claro a azul
profundo en tema claro, y de azul grafito a azul noche en tema oscuro—, aplicado como fondo de
la cabecera del shell y de la cabecera del acceso, y definido como token para que el sistema de
diseño siga siendo la única fuente de verdad.

## Historia de usuario

**Como** usuario del asistente CAD, **quiero** que la aplicación se reconozca a simple vista como
una herramienta de diseño mecánico, **para** ubicarme en ella sin que el ornamento me quite
legibilidad.

## Requisitos

### Funcionales

- **RF-1**: el sistema de diseño define un token de gradiente (`--gradiente-app`) en los tres
  bloques de tema (`:root`, `prefers-color-scheme: dark` y `[data-theme='dark']`), con la misma
  clave en los tres.
- **RF-2**: la cabecera del shell usa el token como fondo, con `--radius-panel` y `padding` de
  los tokens existentes; la cabecera de la pantalla de acceso usa el mismo token.
- **RF-3**: el gradiente alude al material del dominio (acero, plancha, azul de plano) en tonos
  sobrios; no introduce imágenes, texturas ni recursos remotos.
- **RF-4**: ningún elemento de texto cambia de color por el gradiente: título, marca, texto
  apagado y botones conservan sus tokens, y el contraste AA se mantiene en ambos temas.
- **RF-5**: los colores se declaran sólo en `frontend/src/design/tokens.css`; `style.css` usa el
  token, sin valores literales.
- **RF-6**: el tema claro deja de apoyarse en blanco puro: fondo, superficie y superficie sutil
  pasan a tonos acero (`#e2e9f1`, `#f9fbfd`, `#e9eff6`), de modo que la pantalla no se lea
  como una hoja en blanco.
- **RF-7**: el ajuste de paleta clara conserva el contraste AA de todos los pares de tokens que
  ya verifica `frontend/tests/tokens.test.ts` (texto, texto apagado, acento, foco y borde).

### No funcionales

- **RNF-1**: el token cumple la paridad de claves de los tres bloques que ya verifica
  `frontend/tests/tokens.test.ts`; los bloques oscuros son idénticos entre sí.
- **RNF-2**: no se agregan dependencias, imágenes ni fuentes remotas.
- **RNF-3**: el gradiente no participa de la lógica de tema: se resuelve con variables CSS y
  responde al cambio claro/oscuro sin JavaScript adicional.

## Criterios de aceptación

### AC1 — Token en los tres temas

- **Dado** `frontend/src/design/tokens.css`
- **Cuando** se comparan los tres bloques
- **Entonces** los tres definen `--gradiente-app` y la prueba de paridad de tokens pasa.

### AC2 — Cabeceras con el gradiente

- **Dado** el shell autenticado y la pantalla de acceso, en tema claro y oscuro
- **Cuando** se inspecciona la cabecera
- **Entonces** su `background-image` es el gradiente del token vigente y su texto mantiene el
  contraste AA.

### AC3 — Sin literales en el estilo

- **Dado** `frontend/src/style.css`
- **Cuando** se buscan colores hexadecimales
- **Entonces** no hay ninguno; todos los colores llegan por tokens.

### AC4 — Tema claro con color, sin perder contraste

- **Dado** el tema claro
- **Cuando** se inspeccionan el fondo y las superficies
- **Entonces** ningún token de superficie es blanco puro y la prueba de contraste AA pasa en los
  dos temas.

## Fuera de alcance

- Cambiar los colores base, la tipografía o los estados del sistema de diseño (SPEC-035).
- Animaciones, transiciones de tema o gradientes en cards y botones.
- Ilustraciones o imágenes de fondo.

## Métricas de éxito

- Un único token de gradiente, definido tres veces (una por bloque) y usado en dos cabeceras.
- Cero literales de color fuera de `tokens.css` y contraste AA conservado.
