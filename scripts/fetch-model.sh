#!/usr/bin/env bash
# HEREDADO (HU-01): desde HU-14 el modelo es la API de DeepSeek. Este script solo
# sirve para reproducir la línea base con Gemma 4 12B ConstraintKit.
# HU-01 — Descarga y verificación del modelo Gemma 4 12B ConstraintKit (GGUF Q6_K).
# Uso: bash scripts/fetch-model.sh   (idempotente: verifica antes de re-descargar)
set -euo pipefail

MODEL_DIR="models"
MODEL_FILE="gemma4-12b-constraintkit-grpo-Q6_K.gguf"
MODEL_URL="https://huggingface.co/jajmangold/gemma-4-12b-constraintkit-GGUF/resolve/main/${MODEL_FILE}"
# SHA-256 (Git LFS oid) publicado en Hugging Face — AC1 de HU-01.
SHA256="42c5b8ce7d81d060e4fa4b9673786b6e507e96bd84bfde1f24dacc30ebcb7843"

# Trabajar desde la raíz del repo (independiente del cwd actual)
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."
mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_DIR/$MODEL_FILE" ]; then
  echo "Verificando $MODEL_FILE ..."
  if (cd "$MODEL_DIR" && echo "$SHA256  $MODEL_FILE" | sha256sum -c -); then
    echo "OK: ya está descargado y verificado ($MODEL_DIR/$MODEL_FILE)."
    exit 0
  fi
  echo "Hash no coincide; se re-descarga."
fi

echo "Descargando $MODEL_FILE (9,8 GB) desde Hugging Face..."
if command -v wget >/dev/null 2>&1; then
  wget -c "$MODEL_URL" -O "$MODEL_DIR/$MODEL_FILE"
else
  curl -L -C - -o "$MODEL_DIR/$MODEL_FILE" "$MODEL_URL"
fi

echo "Verificando SHA-256..."
(cd "$MODEL_DIR" && echo "$SHA256  $MODEL_FILE" | sha256sum -c -)
echo "OK: modelo listo en $MODEL_DIR/$MODEL_FILE"
