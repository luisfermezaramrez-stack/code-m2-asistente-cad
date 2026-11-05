#!/usr/bin/env bash
# Vendea constraint-kit y parchea su classifier inválido (que rompe el build de hatchling).
# Uso: bash scripts/vendor-constraint-kit.sh
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

CK_DIR="vendor/constraint-kit"
CK_REV="2ed27db4d8fa821afef41103f0efc9befbf116e6"

if [ -d "$CK_DIR/.git" ]; then
  echo "constraint-kit ya está vendoreado en $CK_DIR (rev $(git -C "$CK_DIR" rev-parse --short HEAD))"
  exit 0
fi

mkdir -p vendor
git clone https://github.com/jajmangold/constraint-kit.git "$CK_DIR"
git -C "$CK_DIR" checkout "$CK_REV"

# Fix: hatchling rechaza el classifier inválido "Computer Aided Design (CAD)".
sed -i 's#Topic :: Scientific/Engineering :: Computer Aided Design (CAD)#Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)#' \
  "$CK_DIR/pyproject.toml"

echo "OK: constraint-kit vendoreado y parchado en $CK_DIR"
