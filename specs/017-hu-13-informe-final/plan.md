# SPEC-017 · HU-13 — Plan del informe final

- **ID**: SPEC-017 · **Historia**: #13 · **Responsable**: los 3 integrantes
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

Documento único `docs/informe-final.md` con esta estructura:

1. Resumen en tres líneas: producto, modelo (`deepseek-v4-pro` por API) y resultado global.
2. Tabla de objetivos (meta, valor medido, estado, evidencia).
3. Reproducibilidad: comando, estado del CI y versión etiquetada.
4. Estado del tablero: Done / total y brecha por historia.
5. Enlaces: repositorio, tablero, reporte del banco, Model Card y specs.

El informe no calcula nada: copia los valores de las evidencias versionadas y enlaza la
fuente de cada uno.

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Markdown en `docs/` | Versionado, revisable por PR y visible en GitHub sin herramientas. |
| Solo consolidar, no medir | Evita dos fuentes de verdad; cada número tiene una sola evidencia. |
| Tabla «Metas» del README como lista de objetivos | Es la definición ya publicada; el supuesto de correspondencia se confirma con la propuesta del M2. |
| Etiqueta anotada `v1.0` sobre `main` | `main` solo recibe entregas (Gitflow del proyecto). |

## 3. Dependencias

- SPEC-016 (HU-07): conformes, declinaciones y `docs/reporte-banco.md`.
- SPEC-010 (HU-10): latencia p90 sobre ≥ 30 solicitudes.
- SPEC-006 (HU-11): autonomía de usuarios.
- Si una dependencia no está lista el día 15, el informe la marca «no medido» con la
  causa; no se estima el valor.

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Una evidencia llega tarde | Estado «no medido» con causa explícita (AC3 admite brecha explicada). |
| Enlaces rotos tras renombrar archivos | Verificación de enlaces antes del PR (T05). |
| Etiqueta sobre un commit equivocado | Se crea después del merge de `develop` → `main` y se verifica con `git show v1.0`. |

## 5. Alternativas descartadas

- **Informe en PDF**: no se revisa por diff ni se versiona bien.
- **Dashboard generado**: más costo que valor para cinco indicadores.

## 6. Estrategia de verificación

Documento pasivo: verificación estructural. Cada fila de la tabla tiene enlace a una
evidencia existente; los enlaces relativos se comprueban con un recorrido de los
archivos citados; `git tag -l v1.0` devuelve la etiqueta.
