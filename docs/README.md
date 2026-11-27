# Documentación

Carpeta de documentación del proyecto. El sitio navegable se genera desde la raíz con
`make docs-build`: la navegación está en [`../mkdocs.yml`](../mkdocs.yml) y el runbook
operativo se sirve desde [esta sección](./runbook-operativo.md) sin duplicar su texto.

Convenciones sugeridas (los directorios `adr/`, `spikes/` y `research/` se crearán cuando
haya contenido para ellos):

| Documento | Contenido |
|-----------|-----------|
| [`arquitectura.html`](./arquitectura.html) | Diagrama interactivo de la arquitectura de runtime (Archify). |
| [`arquitectura.json`](./arquitectura.json) | Fuente versionada del diagrama; se regenera el HTML con Archify, nunca a mano. |
| `adr/` | *Architecture Decision Records*: decisiones grandes con contexto y consecuencias. |
| `spikes/` | Investigaciones técnicas acotadas (pregunta, timebox, hallazgo). |
| `research/` | Notas de investigación y comparativas. |

> El historial de decisiones resumido vive en
> [`../CONSTITUTION.md`](../CONSTITUTION.md); los ADR entran en detalle cuando la decisión
> lo amerita.

Reglas:

- Un documento, un tema.
- Fechas en ISO (`AAAA-MM-DD`).
- Enlaza cada documento desde la constitución o el README cuando sea relevante.
- No subas datos sensibles ni personales reales (usa *fixtures* sintéticos).
