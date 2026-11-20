# SPEC-056 · HU-55 — Releases automáticos con changelog

- **ID**: SPEC-056
- **Historia**: issue por crear · Ola 3 (opcional) · Tamaño M · Épica: Entrega
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: [SPEC-032](../032-hu-31-api-v1/spec.md)
- **Rama**: `feature/hu-55-releases-automaticos`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §6
- **Auditoría**: corregida según
  [`docs/auditoria-specs-024-056.md`](../../docs/auditoria-specs-024-056.md)

## Problema y contexto

Los releases se hacen a mano: existen las etiquetas `v1.0` y `v1.0.1`, pero el paquete
declara `version = "0.1.0"` (`pyproject.toml:3`), no hay `CHANGELOG.md` en la raíz y el
único workflow de CI corre pruebas en PRs y pushes a `develop`
(`.github/workflows/ci.yml:3-7`), sin job de release. El equipo ya usa PRs hacia
`develop` y Conventional Commits (`AGENTS.md`, "Flujo Diario"). Las etiquetas `v1.0` y
`v1.0.1` están en `main` (`CONSTITUTION.md:24`), pero ninguna rama de release está
declarada y el CI no corre en `main`.

## Decisión abierta para `plan.md`

"Al fusionar en la rama principal" es ambiguo hoy. `plan.md` debe elegir, y registrar en
`CONSTITUTION.md`, desde qué rama se corta el release y quién crea la etiqueta:

- **Opción A — release desde `main`**: se mantiene el precedente de `v1.0`/`v1.0.1`; exige
  un PR `develop` → `main` por release y que el job de release dispare en `main`, donde
  hoy no corre CI.
- **Opción B — release desde `develop`**: reutiliza el disparador actual del CI; las
  etiquetas dejan de vivir en `main` y `main` pierde su papel de rama publicada.

Los RF y AC dicen "rama de release" para referirse a la rama elegida.

El ítem 46 del borrador se bajó a la ola 3. Sólo aporta si se mantiene el flujo de PRs y
Conventional Commits ya en uso (`docs/backlog-v2.md` §6). Depende de SPEC-032 porque la
versión de la API `/v1` y su contrato congelado definen qué es un cambio incompatible.

## Historia de usuario

**Como** equipo del proyecto, **quiero** que cada release se publique con su versión y su
changelog generados desde los commits, **para** saber qué cambió entre versiones sin
redactarlo a mano.

## Requisitos

### Funcionales

- **RF-1**: calcular la siguiente versión semántica desde los Conventional Commits
  (`feat` → menor, `fix` → parche, `BREAKING CHANGE` → mayor).
- **RF-2**: generar o actualizar `CHANGELOG.md` agrupado por tipo de commit.
- **RF-3**: crear la etiqueta y el GitHub Release con las notas del changelog al fusionar
  en la rama de release (ver decisión abierta). Supuesto: herramienta estándar de release
  en GitHub Actions.
- **RF-4**: sincronizar la versión de `pyproject.toml` con la etiqueta publicada.
- **RF-5**: un cambio incompatible en el contrato `/v1` (SPEC-032) exige
  `BREAKING CHANGE` y produce versión mayor.

### No funcionales

- **RNF-1**: el job de release no se ejecuta en PRs ni en forks; usa el token mínimo
  necesario.
- **RNF-2**: las pruebas del cálculo de versión no usan red, API key ni GPU.
- **RNF-3**: commits que no siguen la convención se detectan antes de fusionar
  (Supuesto: verificación del título de la PR).

## Criterios de aceptación

### AC1 — Release de parche

- **Dado** sólo commits `fix:` desde la última etiqueta
- **Cuando** se fusiona en la rama de release
- **Entonces** se publica una versión de parche con su entrada en `CHANGELOG.md`.

### AC2 — Release mayor

- **Dado** un commit con `BREAKING CHANGE` sobre el contrato `/v1`
- **Cuando** se fusiona en la rama de release
- **Entonces** se publica una versión mayor y las notas destacan el cambio incompatible.

### AC3 — Versión coherente

- **Dado** un release publicado
- **Cuando** se compara la etiqueta con `pyproject.toml`
- **Entonces** ambas indican la misma versión.

## Fuera de alcance

- Publicar el paquete en PyPI o la imagen en un registro (ver SPEC-048).
- Reescribir el historial de commits previo a la adopción.
- Cambiar la estrategia de ramas más allá de elegir la rama de release (decisión abierta).

## Métricas de éxito

- 100 % de los releases con changelog generado y versión coherente.
- 0 pasos manuales para publicar un release.
