# SPEC-016 · HU-07 — Corrida completa del banco con reporte por familia

- **ID**: SPEC-016
- **Historia**: #7 · 2 SP · Etiquetas: Testing, ML · CPM: I (días 8–9)
- **Responsable**: Carlos Eduardo Trujillo (I3 · Pruebas y documentación)
- **Rama**: `feature/hu-07-evaluacion-banco`
- **Estado**: Implementada y evaluada; pendiente de revisión humana
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

`make bench` (HU-14) ya corre el banco HU-02 contra el modelo y deja un CSV y un JSON
con un resumen **global** (`m2_cad.banco.resumir`). Faltan tres cosas para que el
resultado sirva como criterio de aceptación del pipeline:

1. No hay desglose **por familia**, que es como se planificaron las metas.
2. No se distinguen los **errores silenciosos**: piezas entregadas que están mal.
3. Los STEP se construyen en un `tempfile.TemporaryDirectory` y se borran al terminar
   (`banco.main`), así que ningún resultado puede enlazar su STEP.

## Historia de usuario

**Como** responsable de calidad, **quiero** ejecutar las 40 solicitudes del banco con un
solo comando y obtener un reporte por familia, **para** saber el día 9 si el pipeline
cumple la meta de 26 de 30 piezas conformes y 8 de 10 declinaciones correctas.

## Requisitos

### Funcionales

- **RF-1**: un comando corre las 40 solicitudes y produce el reporte sin intervención manual.
- **RF-2**: el reporte agrega por familia: positivas conformes, declinaciones correctas
  y errores silenciosos, más el total contra las metas (≥ 26/30 y ≥ 8/10).
- **RF-3**: **error silencioso** = el sistema entrega una pieza (`estado=construida`) que
  es incorrecta: fuera de la tolerancia de ±2 % en una positiva, o construida cuando el
  caso esperaba declinación.
- **RF-4**: cada caso enlaza su fila del registro de la corrida (CSV por caso, y el
  `run_id` de MLflow cuando el seguimiento está activo) y la ruta de su STEP.
- **RF-5**: el reporte en Markdown queda en `docs/` con el modelo, la fecha y el commit.

### No funcionales

- **RNF-1**: las pruebas no usan red ni API key: el modelo se simula.
- **RNF-2**: no se versionan STEP ni salidas del banco (`outputs/` sigue ignorado);
  solo se versiona el reporte Markdown.
- **RNF-3**: no cambia el comportamiento ni el formato actual de `make bench` para
  quien no pide el reporte (compatibilidad con HU-14 y HU-16).

## Criterios de aceptación

### AC1 — Un comando

- **Dado** el banco `data/test_cases.csv` con 40 solicitudes y una API key válida
- **Cuando** se ejecuta `make bench-report`
- **Entonces** las 40 solicitudes se procesan sin intervención manual y el comando
  termina con código 0.

### AC2 — Reporte por familia

- **Dado** una corrida completa
- **Cuando** se abre el reporte
- **Entonces** muestra, por cada una de las 6 familias y en total, conformes (meta
  ≥ 26 de 30), declinaciones correctas (meta ≥ 8 de 10) y errores silenciosos, con el
  estado de cada meta (cumple / no cumple).

### AC3 — Enlaces por caso

- **Dado** el reporte de una corrida
- **Cuando** se busca un caso por su id
- **Entonces** la fila enlaza la ruta de su STEP (si se construyó), su fila en el CSV de
  la corrida y, con MLflow activo, el `run_id` de su corrida hija.

### AC4 — Meta incumplida

- **Dado** una corrida en la que una meta no se cumple
- **Cuando** se genera el reporte
- **Entonces** el reporte lista la causa por caso fallido, se documenta el ajuste
  aplicado y se repite la corrida **una sola vez**, conservando ambos reportes.

### AC5 — Publicación

- **Dado** el reporte final
- **Cuando** se cierra la historia
- **Entonces** el reporte está en `docs/` y enlazado desde la tarjeta #7 y desde el informe
  final (HU-13, SPEC-017).

## Fuera de alcance

- Cambiar el prompt, el modelo o la tolerancia para "pasar" las metas.
- Paralelizar la corrida o comparar varios modelos (ya lo cubre HU-16 en MLflow).
- Versionar los STEP generados.

## Métricas de éxito

- Conformes / 30, declinaciones correctas / 10 y errores silenciosos = 0, por familia y total.
- Latencia media y costo de la corrida (ya calculados por `resumir`).
