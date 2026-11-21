# SPEC-057 · HU-56 — Constitución de Spec Kit apuntando a `CONSTITUTION.md` (refactor)

- **ID**: SPEC-057
- **Historia**: pendiente (HU-56) · 1 SP · Etiquetas: documentation, refactor
- **Responsable**: Luis Meza
- **Depende de**: [SPEC-023](../023-hu-22-constitution-refactor/spec.md)
- **Rama**: `docs/hu-56-constitucion-speckit`
- **Estado**: Spec-first · propuesta; la issue y la PR se registran al abrirse

## Problema y contexto

El proyecto tiene dos constituciones. La real es `CONSTITUTION.md`, declarada fuente única de
verdad (`AGENTS.md`; `CONSTITUTION.md:272`) y actualizada por SPEC-023. La segunda,
`.specify/memory/constitution.md`, la instaló Spec Kit 1.2.2 el 2026-11-03 y sigue siendo la
plantilla vacía: `[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]` y marcadores sin completar
(`.specify/memory/constitution.md:1-6`).

Los comandos de Spec Kit leen la segunda, no la primera:

- `/speckit.plan` carga `.specify/memory/constitution.md` y completa con ella el
  "Constitution Check" (`.pi/prompts/speckit.plan.md:60-68`).
- `/speckit.analyze` la trata como autoridad no negociable y marca como CRITICAL todo
  conflicto con ella (`.pi/prompts/speckit.analyze.md:56`, `:100`, `:153`).

Hoy esas validaciones corren contra marcadores vacíos: no detectan violaciones reales y
pueden producir hallazgos sin sentido.

## Historia de usuario

**Como** integrante del equipo que usa Spec Kit, **quiero** que la constitución de Spec Kit
remita a `CONSTITUTION.md`, **para** que `/speckit.plan` y `/speckit.analyze` validen contra
las reglas reales del proyecto y no contra una plantilla vacía.

## Requisitos

### Funcionales

- **RF-1**: `.specify/memory/constitution.md` deja de ser la plantilla y declara que la
  constitución del proyecto es `CONSTITUTION.md`, con la ruta relativa a la raíz del repo.
- **RF-2**: el archivo indica que, ante cualquier validación constitucional (Constitution
  Check, alineación de `/speckit.analyze`), se debe leer y aplicar `CONSTITUTION.md` completo.
- **RF-3**: el archivo no copia reglas de `CONSTITUTION.md`; sólo remite a él, para que no
  existan dos versiones que puedan divergir.
- **RF-4**: el archivo advierte que no se debe ejecutar `/speckit.constitution` para
  regenerarlo; los cambios de gobernanza se hacen en `CONSTITUTION.md`.
- **RF-5**: `CONSTITUTION.md` registra la decisión en su historial (§9) en el mismo commit,
  según su directiva de mantenimiento.

### No funcionales

- **RNF-1**: no se modifican los comandos vendoreados de Spec Kit (`.pi/prompts/speckit.*`,
  `.specify/templates/`, `.specify/scripts/`); una actualización de Spec Kit los
  sobrescribiría.
- **RNF-2**: no se usa enlace simbólico, porque Spec Kit se inicializó con
  `"allow_symlinks": false` (`.specify/init-options.json`).

## Criterios de aceptación

### AC1 — Sin marcadores de plantilla

- **Dado** el archivo `.specify/memory/constitution.md` tras el cambio
- **Cuando** se busca el patrón `\[[A-Z_0-9]+\]`
- **Entonces** no hay coincidencias.

### AC2 — Remisión a la constitución real

- **Dado** el archivo `.specify/memory/constitution.md`
- **Cuando** un agente lo lee al ejecutar `/speckit.plan` o `/speckit.analyze`
- **Entonces** encuentra la ruta `CONSTITUTION.md` y la instrucción de aplicarla completa.

### AC3 — Decisión registrada

- **Dado** `CONSTITUTION.md` tras el cambio
- **Cuando** se revisa su §9 "Historial de decisiones técnicas"
- **Entonces** hay una entrada que explica por qué la constitución de Spec Kit remite a ella.

## Fuera de alcance

- Modificar los comandos, plantillas o scripts vendoreados de Spec Kit.
- Reescribir `CONSTITUTION.md` en el formato de principios de Spec Kit.
- Actualizar la versión de Spec Kit.

## Métricas de éxito

- 0 marcadores de plantilla en `.specify/memory/constitution.md`.
- Una sola fuente de reglas de gobernanza en el repositorio.
