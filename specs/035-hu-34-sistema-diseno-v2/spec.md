# SPEC-035 · HU-34 — Sistema de diseño v2: tokens, tipografía y modo oscuro

- **ID**: SPEC-035
- **Historia**: issue por crear · Ola 1 · Tamaño M · Épica: UX
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: —
- **Rama**: `feature/hu-34-sistema-diseno-v2`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §4

## Problema y contexto

HU-15 ([SPEC-015](../015-hu-15-vue-sse/spec.md)) dejó un sistema de tokens que funciona,
pero con tres límites. Esta spec reformula el ítem 24 del borrador; no parte de cero:

1. Los tokens viven en `design/tokens.css` (63 líneas), **fuera del paquete del
   frontend**, y se importan con una ruta relativa que sale de `frontend/`
   (`frontend/src/main.ts:3`).
2. Solo hay tema claro: `color-scheme: light` (`design/tokens.css:3`) y ninguna regla
   `prefers-color-scheme`.
3. Existen tokens tipográficos (`design/tokens.css:25-34`: familias, cuatro tamaños,
   pesos e interlineados), pero no hay una escala tipográfica documentada que indique
   sus proporciones y usos.

`design/README.md` y `design/validation.md` documentan el contraste del tema claro; el
tema oscuro no tiene validación.

## Historia de usuario

**Como** usuario de la interfaz, **quiero** un tema claro y uno oscuro que respeten mi
preferencia y cumplan contraste AA, **para** trabajar cómodo en cualquier entorno; y
**como** desarrollador del frontend, **quiero** tokens dentro del paquete y documentados,
**para** cambiar el aspecto sin tocar componentes.

## Requisitos

### Funcionales

- **RF-1**: los tokens viven dentro de `frontend/src` o en un paquete propio; la elección
  queda abierta para `plan.md`.
- **RF-2**: escala tipográfica definida y documentada.
- **RF-3**: tema claro y oscuro, seleccionado por `prefers-color-scheme` y por una
  preferencia explícita del usuario que prevalece sobre la del sistema.
- **RF-4**: contraste AA verificado en ambos temas.
- **RF-5**: documentación del sistema de diseño (tokens, escala, temas y su uso).

### No funcionales

- **RNF-1**: las pruebas no usan red, API key ni GPU.
- **RNF-2**: se mantiene la regla de HU-15: sin fuentes ni recursos remotos
  (`design/tokens.css:1`).
- **RNF-3**: el fondo oscuro del visor 3D (`design/tokens.css:7-8`) conserva el contraste
  con la pieza en ambos temas.
- **Supuesto**: la preferencia explícita se guarda en el navegador; no requiere backend.

## Criterios de aceptación

### AC1 — Contraste en ambos temas

- **Dado** el tema claro y el tema oscuro
- **Cuando** se mide el contraste de cada par de texto y fondo y del indicador de foco
- **Entonces** el texto cumple ≥ 4.5:1 y el foco ≥ 3:1 en ambos temas.

### AC2 — Cambiar un token no toca componentes

- **Dado** el sistema de tokens dentro del paquete del frontend
- **Cuando** se cambia el valor de un token
- **Entonces** el cambio se refleja en la interfaz sin modificar ningún componente
  `.vue` ni `style.css`.

### AC3 — Selección de tema

- **Dado** un sistema operativo con preferencia oscura
- **Cuando** se abre la interfaz sin preferencia explícita guardada
- **Entonces** se muestra el tema oscuro; y si el usuario elige el claro, se mantiene el
  claro aunque el sistema prefiera el oscuro.

### AC4 — Tokens dentro del frontend

- **Dado** el código del frontend
- **Cuando** se revisan sus importaciones
- **Entonces** ningún archivo importa tokens desde fuera de su paquete.

## Fuera de alcance

- Cierre de brechas WCAG fuera del contraste ([SPEC-041](../041-hu-40-wcag-aa/spec.md)).
- App shell y navegación ([SPEC-039](../039-hu-38-app-shell/spec.md)).
- Rediseño visual de componentes.

## Métricas de éxito

- 0 pares de contraste por debajo de AA en ambos temas.
- 0 componentes modificados al cambiar un token.
