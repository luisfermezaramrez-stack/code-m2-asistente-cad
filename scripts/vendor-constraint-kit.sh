#!/usr/bin/env bash
# Vendea constraint-kit en una revisión fija y aplica los dos parches de packaging
# que necesita para compilar su wheel con hatchling.
# Uso: bash scripts/vendor-constraint-kit.sh   (idempotente: se puede correr las veces que haga falta)
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

CK_DIR="vendor/constraint-kit"
CK_URL="https://github.com/jajmangold/constraint-kit.git"
CK_REV="2ed27db4d8fa821afef41103f0efc9befbf116e6"
CK_PYPROJECT="$CK_DIR/pyproject.toml"

if [ ! -d "$CK_DIR/.git" ]; then
  mkdir -p vendor
  git clone "$CK_URL" "$CK_DIR"
fi
git -C "$CK_DIR" checkout -q "$CK_REV"

# Parche 1: "Computer Aided Design (CAD)" no es un classifier válido de Trove y hatchling
# rechaza el campo classifiers completo.
if grep -q "Topic :: Scientific/Engineering :: Computer Aided Design (CAD)" "$CK_PYPROJECT"; then
  sed -i 's#Topic :: Scientific/Engineering :: Computer Aided Design (CAD)#Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)#' \
    "$CK_PYPROJECT"
fi

# Parche 2: el extra `gear` referencia cq_gears por git; hatchling exige habilitarlo
# explícitamente o no compila el wheel (falla en project.optional-dependencies).
if ! grep -q '^\[tool\.hatch\.metadata\]' "$CK_PYPROJECT"; then
  cat >> "$CK_PYPROJECT" <<'TOML'

[tool.hatch.metadata]
allow-direct-references = true
TOML
fi

echo "OK: constraint-kit vendoreado y parchado en $CK_DIR (rev $(git -C "$CK_DIR" rev-parse --short HEAD))"
