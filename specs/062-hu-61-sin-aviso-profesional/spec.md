# SPEC-062 · HU-61 — Sin aviso profesional persistente en el shell (refactor)

- **ID**: SPEC-062
- **Historia**: #167 (HU-61) · 1 SP · Etiquetas: frontend, refactor, UX
- **Responsable**: Luis Meza
- **Rama**: `refactor/hu-58-60-interfaz-login` (HU-58 a HU-61 en un solo PR)
- **Estado**: Spec-first · en revisión (PR #171 / #172)
- **Supera**: la colocación visible del aviso que exige
  [SPEC-003](../003-declinacion-preliminar/spec.md) («marcar toda salida como diseño
  preliminar») y el panel de aviso del shell de [SPEC-039](../039-hu-38-app-shell/spec.md).

## Problema y contexto

El shell mostraba, entre la cabecera y la navegación, un aviso permanente
(`frontend/src/App.vue`): «Diseño preliminar: requiere revisión profesional / La verificación
geométrica no certifica resistencia ni cumplimiento normativo.»

Tres problemas:

1. **Se repite en todas las vistas** y compite con lo que el usuario vino a hacer; el ruido
   crece cuanto más se usa la aplicación.
2. **No distingue estado**: aparece igual antes de pedir una pieza, mientras se genera y
   después de una declinación, donde el mensaje de la declinación sí importa.
3. **Duplica una marca que ya viaja con el resultado**: la respuesta de la API incluye
   `aviso` con `MARCA_PRELIMINAR` (`src/m2_cad/pipeline.py:217`, `src/m2_cad/api.py:239`), de
   modo que la condición de diseño preliminar sigue declarada en la entrega y no se pierde al
   retirar el banner.

## Historia de usuario

**Como** usuario del asistente CAD, **quiero** que la pantalla de trabajo no repita un aviso
fijo en cada vista, **para** concentrarme en la solicitud y ver las advertencias donde
corresponden al resultado.

## Requisitos

### Funcionales

- **RF-1**: el shell no renderiza ningún aviso profesional persistente entre la cabecera y la
  navegación.
- **RF-2**: la marca de diseño preliminar permanece en el contrato de la API: la respuesta de
  generación y la de instanciación de plantillas siguen incluyendo `aviso` con el texto de
  `MARCA_PRELIMINAR`; el backend y su spec (SPEC-003) no cambian.
- **RF-3**: el aviso que el resultado traiga consigo, cuando la interfaz lo muestre, se asocia
  a ese resultado y no al shell.
- **RF-4**: no se sustituye el aviso por otro banner fijo: la advertencia deja de ser un
  elemento permanente de la interfaz.
- **RF-5**: los estados que sí comunican riesgo (declinación con motivo, error terminal,
  falta de archivo STEP) conservan su mensaje y su rol accesible.

### No funcionales

- **RNF-1**: se retira también su estilo (`.notice`) para no dejar CSS sin consumidores.
- **RNF-2**: el cambio no toca autenticación, navegación, ni el contenido de las vistas.

## Criterios de aceptación

### AC1 — Sin aviso persistente

- **Dado** un usuario autenticado en cualquier vista del shell
- **Cuando** se inspecciona la pantalla
- **Entonces** no existe el aviso «Diseño preliminar: requiere revisión profesional» ni el
  elemento `.notice`.

### AC2 — La marca sigue en la entrega

- **Dado** una generación verificada
- **Cuando** se lee la respuesta de la API
- **Entonces** incluye `aviso` con el texto de `MARCA_PRELIMINAR`, igual que antes del cambio.

### AC3 — La advertencia de declinación no se pierde

- **Dado** una solicitud declinada
- **Cuando** se muestra el resultado
- **Entonces** el motivo de la declinación sigue visible como texto, con su tratamiento
  accesible, sin depender del aviso retirado.

## Fuera de alcance

- Retirar `MARCA_PRELIMINAR` del dominio, de la API o de los artefactos entregados.
- Cambiar los mensajes de declinación (SPEC-027) o de error.
- Sustituir el aviso por un diálogo modal, un onboarding o un tooltip.

## Métricas de éxito

- Cero apariciones del aviso persistente en las vistas del shell.
- `aviso` presente en el 100 % de las respuestas de generación e instanciación.
