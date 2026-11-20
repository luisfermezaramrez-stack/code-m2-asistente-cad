# SPEC-029 · HU-28 — Escaneo de dependencias y secretos en CI

- **ID**: SPEC-029
- **Historia**: #88 (HU-28) · 1 SP · Etiquetas: infra, Testing · Hito: M4
- **Planificación**: Ola 0 · Tamaño S · Épica: Entrega
- **Responsable**: Carlos Eduardo Trujillo
- **Depende de**: —
- **Rama**: `feature/hu-28-escaneo-seguridad`
- **Estado**: Spec-first · propuesta; `plan.md` y `tasks.md` se redactan al tomar la HU
- **Origen**: [`docs/backlog-v2.md`](../../docs/backlog-v2.md) §3

## Problema y contexto

1. `.github/dependabot.yml:4,22,43` cubre los ecosistemas `npm`, `uv` y `github-actions`:
   propone actualizaciones, pero no bloquea una PR que introduce una vulnerabilidad.
2. `.github/workflows/ci.yml` no ejecuta `pip-audit`, `gitleaks` ni `detect-secrets`.
3. `.pre-commit-config.yaml` sólo bloquea archivos grandes (`check-added-large-files`,
   línea 16) y pesos de modelo (`no-model-weights`, línea 30), además de Ruff y chequeos de
   formato. Nada impide commitear una API key (por ejemplo `DEEPSEEK_API_KEY`).

## Historia de usuario

**Como** responsable de la entrega, **quiero** que CI escanee dependencias vulnerables y
secretos en cada PR, **para** que un CVE alto o una clave commiteada se detengan antes de
fusionar y con instrucciones claras para corregirlos.

## Requisitos

### Funcionales

- **RF-1**: un job de CI con `pip-audit` sobre las dependencias Python bloqueadas en
  `uv.lock`.
- **RF-2**: un job de CI con `gitleaks` sobre los cambios de la PR.
- **RF-3**: ambos jobs fallan ante un hallazgo de severidad alta (CVE) o un secreto, y el
  mensaje indica el paso exacto a seguir (actualizar la dependencia, rotar y retirar la
  clave, o registrar una excepción).
- **RF-4**: una política de excepciones documentada: dónde se declaran, quién las aprueba,
  justificación obligatoria y fecha de revisión.

### No funcionales

- **RNF-1**: los jobs no requieren secretos del repositorio para ejecutarse.
- **RNF-2**: las versiones de las herramientas quedan fijadas.
- **RNF-3**: la gestión de dependencias Python sigue pasando por `uv` (sin `pip` ni
  `requirements.txt` versionado).

> **Supuesto**: `pip-audit` recibe la lista exportada desde `uv.lock` en el propio job, sin
> versionar ningún `requirements.txt`.

> **Supuesto**: el escaneo de dependencias npm queda fuera; el backlog sólo nombra
> `pip-audit` y `gitleaks`.

## Criterios de aceptación

### AC1 — Secreto commiteado

- **Dado** una PR que agrega una cadena con forma de API key
- **Cuando** corre CI
- **Entonces** el job de secretos falla, señala archivo y línea, e indica el paso exacto:
  rotar la clave, retirarla del historial o declarar una excepción justificada.

### AC2 — CVE alto

- **Dado** una PR que fija una dependencia Python con un CVE de severidad alta
- **Cuando** corre CI
- **Entonces** el job de dependencias falla, nombra el paquete, el CVE y la versión
  corregida, e indica el comando para actualizarla.

### AC3 — Excepción documentada

- **Dado** un hallazgo aceptado conforme a la política
- **Cuando** se registra como excepción con justificación y fecha de revisión
- **Entonces** el job pasa y la excepción queda visible en el repositorio.

## Fuera de alcance

- Análisis estático de código (SAST) o escaneo de imágenes Docker.
- Endurecimiento de descargas y artefactos
  ([SPEC-037](../037-hu-36-endurecimiento-descargas/spec.md)).

## Métricas de éxito

- Secretos y CVE altos fusionados en `develop`: 0.
- Excepciones sin justificación o vencidas: 0.
