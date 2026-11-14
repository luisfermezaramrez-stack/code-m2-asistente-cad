# SPEC-014 · HU-12 — Manuales de usuario, técnico y README

> **Documentación retroactiva.** Esta especificación se redactó el 2026-11-13, después de implementar y fusionar la historia (PR #41). Documenta lo construido para trazabilidad; no se presenta como especificación previa al código.

- **ID**: SPEC-014
- **Historia**: #12 · 3 SP · Etiquetas: Backend, Frontend · CPM: P
- **Responsable**: Carlos Eduardo Trujillo según `reference/HU-Carlos-Eduardo-Trujillo.md`.
  El issue #12 está asignado a `JuanC0319` y el PR #41 lo abrió `JuanC0319`.
- **Rama**: `feature/hu-12-manuales-y-readme`
- **PR**: #41, fusionado en `develop` el 2026-11-13 05:10 UTC (commit `7a28040`);
  aprobado por `luisfermezaramrez-stack`. El cuerpo del PR dice «Sin issue asociado».
- **Estado**: Fusionada con brechas (AC1, AC2 parcial, AC4)
- **Plan**: [`plan.md`](./plan.md) · **Tareas**: [`tasks.md`](./tasks.md)

## Problema y contexto

El repositorio carecía de una fuente única de verdad y de documentación de instalación
y operación para alguien ajeno al equipo. El PR #41 adoptó el estándar del proyecto
(`CONSTITUTION.md`, guías de contribución, plantillas de PR e issues), amplió el
`README.md` y añadió un diagrama interactivo de arquitectura (`docs/arquitectura.html`).
No incluyó un documento titulado «manual de usuario» ni capturas de pantalla.

## Historia de usuario

Cita literal de `reference/HU-Carlos-Eduardo-Trujillo.md`, «## HU-12»:

> **Como** desarrollador o usuario nuevo, **quiero** un manual de usuario, un manual técnico y un README con los comandos de instalación, **para** instalar, operar y mantener el servicio sin depender del equipo que lo construyó.
>
> - **AC1**: manual de usuario con las 3 tareas y capturas.
> - **AC2**: manual técnico con arquitectura, endpoints, despliegue y límites.
> - **AC3**: README con 5 comandos o menos.
> - **AC4**: una persona ajena instala el servicio solo con el README en ≤ 30 min.
> - **AC5**: manuales revisados por otro integrante.

## Requisitos funcionales

- **RF-1**: manual de usuario que explique las 3 tareas con capturas.
- **RF-2**: manual técnico con arquitectura, endpoints, despliegue y límites.
- **RF-3**: `README.md` con la instalación en 5 comandos o menos.
- **RF-4**: diagrama de arquitectura versionado con su fuente (`docs/arquitectura.json`).
- **RF-5**: `.env.example` con las variables esperadas, sin secretos.

## Requisitos no funcionales

- **RNF-1**: documentación en español; sin datos personales ni secretos.
- **RNF-2**: `pre-commit run --all-files` en verde (higiene, YAML/JSON).
- **RNF-3**: `CONSTITUTION.md` actualizada en el mismo cambio.

## Criterios de aceptación

### AC1 — Manual de usuario con las 3 tareas y capturas

- **Dado** un usuario nuevo, **cuando** abre el manual de usuario, **entonces** encuentra
  las 3 tareas paso a paso con capturas.
- **Evidencia**: el PR #41 no añade ningún manual de usuario ni imágenes (lista de
  archivos del PR). A 2026-11-13 no hay archivos `.png/.jpg/.gif/.webp` versionados ni
  un documento con «manual de usuario» en `README.md`, `docs/` o `CONSTITUTION.md`.
- **Estado**: **Brecha**.

### AC2 — Manual técnico con arquitectura, endpoints, despliegue y límites

- **Dado** un desarrollador nuevo, **cuando** consulta la documentación técnica,
  **entonces** encuentra arquitectura, endpoints, despliegue y límites.
- **Evidencia** (commit `7a28040`): arquitectura en `docs/arquitectura.html` y
  `README.md` § Arquitectura; estructura y stack en `CONSTITUTION.md` §§ 3–4;
  despliegue en `README.md` § Instalación y uso y § Entorno en la nube (Lambda);
  límites en `CONSTITUTION.md` § 2 «Fuera del alcance». Los endpoints solo se nombran
  (`POST /generar`, `GET /health`, `CONSTITUTION.md` § 2) sin entradas, salidas ni
  códigos de estado.
- **Estado**: **Parcial**. No hay un documento único de «manual técnico» y falta el
  contrato de los endpoints.

### AC3 — README con 5 comandos o menos

- **Dado** el `README.md`, **cuando** se sigue § Instalación y uso, **entonces** la
  instalación usa 5 comandos o menos.
- **Evidencia**: en `7a28040` el bloque tiene 3 comandos (`uv sync --dev`, `make check`,
  `make up`) o 1 con Docker (`docker compose up --build`). Sin embargo, el `Makefile`
  del mismo commit marca `vendor` como «necesario antes de uv sync/build» y
  `pyproject.toml` depende de `vendor/constraint-kit`; el README omitía ese paso. El
  README actual sí lo incluye y lista 5 comandos.
- **Estado**: Cumplido en número de comandos; secuencia **incompleta** en el PR #41
  para un checkout limpio (corregida después).

### AC4 — Instalación por una persona ajena en ≤ 30 min

- **Dado** una persona ajena al equipo, **cuando** instala siguiendo solo el README,
  **entonces** termina en ≤ 30 min.
- **Evidencia**: ninguna en el PR #41, su revisión ni el issue #12. El PR declara
  `make up` como N/A.
- **Estado**: **No verificado (Brecha)**.

### AC5 — Manuales revisados por otro integrante

- **Dado** los manuales, **cuando** otro integrante los revisa, **entonces** queda
  constancia de la revisión.
- **Evidencia**: revisión `APPROVED` de `luisfermezaramrez-stack` el 2026-11-13
  04:47 UTC, sin comentarios en el cuerpo. El PR no tiene comentarios.
- **Estado**: Cumplido como aprobación formal; no hay observaciones escritas de la
  revisión.

## Fuera de alcance

- Cambios de código funcional (solo `style` en `tests/test_api.py`).
- Documentación posterior de HU-14, HU-15 y HU-16 (`docs/hu15-*.md`, README actual).

## Métricas de éxito

- 5 AC cumplidos; hoy: AC3 y AC5 cumplidos, AC2 parcial, AC1 y AC4 abiertos.
- Instalación desde checkout limpio con el README en ≤ 30 min (sin medir).
