<!--
Título del PR: <tipo>(hu-XX): <descripción en imperativo>
Ej.: feat(hu-08): añadir vista 3D en la interfaz Gradio
-->

## Descripción

<!-- ¿Qué hace este PR y por qué? Referencia la HU/spec si aplica: specs/00X-.../spec.md -->

Closes #

## Cambios incluidos

- <!-- cambio 1 -->
- <!-- cambio 2 -->

## Cómo se probó

- [ ] `make check` en verde (Ruff + pytest + cobertura ≥ 70 %)
- [ ] `make precommit` en verde
- [ ] Pruebas nuevas o actualizadas cubren el cambio (patrón AAA)
- [ ] Verificación manual con servicio levantado (`make up`): <!-- describe el camino probado o marca N/A -->

## Checklist

- [ ] El título sigue **Conventional Commits** (`feat:`, `fix:`, `docs:`, …)
- [ ] Un solo propósito por PR (sin cambios colaterales sin relación)
- [ ] Sin secretos, datos personales ni archivos de pesos (`.gguf`, `.safetensors`)
- [ ] **CONSTITUTION.md** actualizado en el mismo commit si el cambio es
      arquitectónico, tecnológico o de proceso
- [ ] La salida del asistente sigue declarándose **preliminar** (si aplica)
