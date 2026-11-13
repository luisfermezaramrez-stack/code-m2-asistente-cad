#!/usr/bin/env bash
# HEREDADO (HU-01): desde HU-14 el modelo es la API de DeepSeek. Este script solo
# sirve para reproducir la línea base con Gemma 4 12B ConstraintKit.
# HU-01 — Bootstrap completo de una instancia Vast.ai NUEVA (o reiniciada).
#
# Idempotente: verifica cada paso antes de ejecutarlo y retoma donde quedó
# (el build de cmake y el wget -c continúan desde lo ya hecho tras una caída).
# Deja la instancia sirviendo el modelo en el puerto interno 18080 (el 8080
# interno está ocupado por los servicios de la imagen de Vast).
#
# Uso (dentro de la instancia):
#   scp -P <puerto_ssh> scripts/cloud/vastai-bootstrap.sh root@<host>:/workspace/
#   ssh -p <puerto_ssh> root@<host>
#   LLAMA_PORT=18080 bash /workspace/vastai-bootstrap.sh
#   # y desde la máquina local:
#   ssh -p <puerto_ssh> -N -L 8080:localhost:18080 root@<host>
#
# Variables:
#   LLAMA_PORT   puerto interno del servidor (default: 18080)
#   JOBS         hilos de compilación (default: nproc)
set -euo pipefail

LLAMA_DIR="/workspace/llama.cpp"
BIN="$LLAMA_DIR/build/bin/llama-server"
MODEL="/workspace/gemma4-12b-constraintkit-grpo-Q6_K.gguf"
MODEL_URL="https://huggingface.co/jajmangold/gemma-4-12b-constraintkit-GGUF/resolve/main/gemma4-12b-constraintkit-grpo-Q6_K.gguf"
# SHA-256 (Git LFS oid) publicado en Hugging Face — AC1 de HU-01.
SHA256="42c5b8ce7d81d060e4fa4b9673786b6e507e96bd84bfde1f24dacc30ebcb7843"
JOBS="${JOBS:-$(nproc)}"
PORT="${LLAMA_PORT:-18080}"

fail() { printf 'FALLA: %s\n' "$*" >&2; exit 1; }
step() { printf '\n== %s ==\n' "$*"; }

# 1) GPU visible.
step "GPU"
command -v nvidia-smi >/dev/null 2>&1 || fail "nvidia-smi no disponible (¿instancia sin GPU?)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

# 2) Código fuente de llama.cpp.
step "llama.cpp: código fuente"
if [ -d "$LLAMA_DIR/.git" ]; then
  echo "ya clonado en $LLAMA_DIR"
else
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$LLAMA_DIR"
fi

# 3) Compilación con backend CUDA (arch 86 = Ampere: RTX 3090/4090/5090).
step "llama.cpp: compilación CUDA (retoma si quedó a medias)"
if [ -x "$BIN" ] && "$BIN" --version >/dev/null 2>&1; then
  "$BIN" --version | head -1
else
  command -v nvcmake >/dev/null 2>&1 || command -v nvcc >/dev/null 2>&1 \
    || fail "nvcc no disponible en la imagen"
  command -v cmake >/dev/null 2>&1 || fail "cmake no disponible en la imagen"
  cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" \
    -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DLLAMA_CURL=OFF
  cmake --build "$LLAMA_DIR/build" --config Release -j "$JOBS" \
    --target llama-server llama-cli
fi

# 4) Modelo GGUF: descargar solo si falta o el hash no coincide (AC1).
step "modelo GGUF (descarga + SHA-256)"
if [ -f "$MODEL" ] && echo "$SHA256  $MODEL" | sha256sum -c --status 2>/dev/null; then
  echo "OK: ya descargado y verificado ($(du -h "$MODEL" | cut -f1))"
else
  echo "descargando $MODEL_URL (9,8 GB, con reanudación)..."
  wget -c "$MODEL_URL" -O "$MODEL"
  echo "$SHA256  $MODEL" | sha256sum -c -
fi

# 5) Servir: reutiliza vastai-serve.sh si está (idempotente), sino arranca directo.
step "llama-server"
if [ -f /workspace/vastai-serve.sh ]; then
  LLAMA_PORT="$PORT" bash /workspace/vastai-serve.sh
else
  echo "(vastai-serve.sh no está en /workspace; arrancando directamente)"
  if curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "OK: ya está sirviendo en http://127.0.0.1:${PORT}"
  else
    nohup "$BIN" \
      --model "$MODEL" \
      --ctx-size 8192 \
      --n-gpu-layers 999 \
      --host 0.0.0.0 \
      --port "$PORT" \
      > /workspace/llama-server.log 2>&1 &
    for _ in $(seq 1 60); do
      curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 && \
        { echo "OK: sirviendo en http://127.0.0.1:${PORT}"; exit 0; }
      sleep 2
    done
    fail "el servidor no respondió /health en 120 s; revisá /workspace/llama-server.log"
  fi
fi

printf '\nBootstrap completo. Túnel desde la máquina local:\n  ssh -p <puerto_ssh> -N -L 8080:localhost:%s root@<host>\n' "$PORT"
