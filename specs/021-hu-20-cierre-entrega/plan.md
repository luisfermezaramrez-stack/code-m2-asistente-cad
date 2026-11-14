# SPEC-021 — Plan de la publicación de la entrega

- **ID**: SPEC-021 · **Historia**: HU-20 · **Responsable**: Luis Fernando Meza
- **Spec**: [`spec.md`](./spec.md) · **Tareas**: [`tasks.md`](./tasks.md)

## 1. Diseño

```text
HU-21 (#73) fusionada en develop → CI verde
  → PR develop → main → git tag -a v1.0 → git push origin v1.0
  → registro en informe-final.md y SPEC-017 T08 (PR a develop con Closes #72)
```

## 2. Decisiones

| Decisión | Porqué |
| --- | --- |
| Publicar después de la HU-21 | La etiqueta debe apuntar a un informe correcto; etiquetar antes congelaría datos contradictorios. |
| Etiqueta anotada, no ligera | Guarda autor, fecha y mensaje; es lo que pide SPEC-017 RF-4. |
| Registrar la etiqueta en una PR posterior | El commit etiquetado no puede contener su propio hash; el registro va en el siguiente commit. |

## 3. Comandos

```bash
make check
gh pr create --base main --head develop --title "release: v1.0"
git fetch origin && git tag -a v1.0 -m "v1.0 — entrega final M2" origin/main
git push origin v1.0
git ls-remote --tags origin v1.0
```

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Conflictos al promover `develop` a `main` | PR de promoción con CI; sin `--force`. |
| Etiquetar un commit equivocado | Etiquetar `origin/main` justo después de la fusión y verificar con `git ls-remote`. |

## 5. Verificación

- PR `develop → main` fusionada con CI en verde (AC1).
- `git ls-remote --tags origin v1.0` (AC2).
- Revisión del informe y de SPEC-017 T08 (AC3).
