# SPEC-014 · HU-12 — Tareas de documentación

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #41). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-014
- **Historia**: #12
- **Responsable**: Carlos Eduardo Trujillo (backlog); autor del PR #41: `JuanC0319`
- **Rama**: `feature/hu-12-manuales-y-readme`
- **PR**: #41 (fusionado 2026-11-13)
- **Estado**: Fusionada; quedan brechas abiertas (T08–T11)
- **Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md)

## Tareas

- [x] T01 — Crear `CONSTITUTION.md` como fuente única de verdad · Responsable: autor del
  PR #41 (`JuanC0319`) · Hecho cuando: cubre alcance, stack, estructura y decisiones ·
  Evidencia: `CONSTITUTION.md` (+262) en `7a28040`
- [x] T02 — Ampliar `README.md` con badges, índice, arquitectura, estructura, requisitos,
  instalación y variables de entorno (dep. T01) · Responsable: `JuanC0319` · Hecho
  cuando: la sección de instalación tiene ≤ 5 comandos · Evidencia: `README.md`
  (+72 −6), 3 comandos en § Instalación y uso
- [x] T03 — Diagrama de arquitectura con Archify y su fuente (dep. T01) · Responsable:
  `JuanC0319` · Hecho cuando: `docs/arquitectura.html` se genera desde
  `docs/arquitectura.json` · Evidencia: ambos archivos en `7a28040`
- [x] T04 — Índice `docs/README.md` · Responsable: `JuanC0319` · Hecho cuando: enlaza el
  diagrama y su fuente · Evidencia: `docs/README.md` en `7a28040`
- [x] T05 — Gobernanza: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, plantillas de PR e
  issues · Responsable: `JuanC0319` · Hecho cuando: existen y validan como YAML ·
  Evidencia: lista de archivos del PR #41
- [x] T06 — `.env.example` sin secretos y `AGENTS.md` · Responsable: `JuanC0319` · Hecho
  cuando: existen sin valores sensibles · Evidencia: lista de archivos del PR #41
- [x] T07 — Revisión por otro integrante (AC5) (dep. T01–T06) · Responsable: revisor ·
  Hecho cuando: el PR queda aprobado · Evidencia: `APPROVED` de
  `luisfermezaramrez-stack`, 2026-11-13 04:47 UTC (sin comentarios escritos)
- [ ] T08 — Manual de usuario con las 3 tareas y capturas (AC1) · Responsable: Carlos
  Eduardo Trujillo (backlog) · Hecho cuando: existe el documento con capturas
  versionadas · Evidencia: **Brecha**; no consta en el PR #41 ni en el repositorio
- [ ] T09 — Contrato de endpoints en el manual técnico (AC2) · Responsable: sin asignar
  · Hecho cuando: cada endpoint documenta entrada, salida y códigos · Evidencia:
  **Brecha**; solo se nombran en `CONSTITUTION.md` § 2
- [x] T10 — Incluir el paso de vendor en la instalación del README (AC3) · Responsable:
  posterior al PR #41 · Hecho cuando: el README lista el vendor antes de `uv sync` ·
  Evidencia: `README.md` actual, § Instalación y uso (`bash scripts/vendor-constraint-kit.sh`)
- [ ] T11 — Instalación cronometrada por una persona ajena (AC4) (dep. T10) ·
  Responsable: sin asignar · Hecho cuando: queda registro de ≤ 30 min solo con el
  README · Evidencia: **No verificado**

## Notas

- El PR #41 se declaró «Sin issue asociado»; el issue #12 se cerró el
  2026-11-14 00:51 UTC.
- La redacción de AC2 en el issue #12 dice «restricciones de validez»; la del backlog,
  «límites». Esta especificación usa la del backlog.
