#!/usr/bin/env bash
# HEREDADO (HU-01): desde HU-14 el modelo es la API de DeepSeek. Este script solo
# sirve para reproducir la línea base con Gemma 4 12B ConstraintKit.
# HU-01 — Arranca llama-server nativo en una instancia Vast.ai (ruta sin Docker).
#
# Contexto: las instancias Docker de Vast.ai no soportan docker-in-docker ni
# systemd, por lo que `docker compose up llama` no aplica dentro de la instancia.
# Este script levanta el binario compilado de llama.cpp directamente sobre la
# GPU alquilada, con el mismo contrato de puerto que el compose local (8080).
#
# Uso (dentro de la instancia Vast.ai):
#   bash scripts/cloud/vastai-serve.sh
#
# Variables de entorno:
#   LLAMA_BIN    ruta al binario llama-server
#                (default: /workspace/llama.cpp/build/bin/llama-server)
#   MODEL_PATH   ruta al GGUF Q6_K verificado
#                (default: /workspace/gemma4-12b-constraintkit-grpo-Q6_K.gguf)
#   LLAMA_PORT   puerto interno del servidor (default: 8080)
#   EXPECTED_CTX contexto exigido por AC2 (default: 8192)
#   NGL          capas offload a GPU (default: 999 = todas)
#
# El log del servidor queda en /workspace/llama-server.log.
set -euo pipefail

LLAMA_BIN="${LLAMA_BIN:-/workspace/llama.cpp/build/bin/llama-server}"
MODEL_PATH="${MODEL_PATH:-/workspace/gemma4-12b-constraintkit-grpo-Q6_K.gguf}"
PORT="${LLAMA_PORT:-8080}"
CTX="${EXPECTED_CTX:-8192}"
NGL="${NGL:-999}"
LOG="/workspace/llama-server.log"
BASE_URL="http://127.0.0.1:${PORT}"

fail() { printf 'FALLA: %s\n' "$*" >&2; exit 1; }

# 1) GPU visible para el contenedor.
command -v nvidia-smi >/dev/null 2>&1 \
  || fail "nvidia-smi no disponible (¿instancia sin GPU?)"
gpu="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)"
printf 'GPU: %s\n' "${gpu}"

# 2) Modelo GGUF presente (AC1: descargado y verificado con fetch-model).
[ -f "${MODEL_PATH}" ] \
  || fail "no está el modelo en ${MODEL_PATH} (descargalo con wget y valida el SHA-256 del AC1)"

# 3) Binario llama-server compilado con CUDA.
[ -x "${LLAMA_BIN}" ] \
  || fail "no está llama-server en ${LLAMA_BIN} (compilalo: git clone --depth 1 https://github.com/ggml-org/llama.cpp /workspace/llama.cpp && cmake -S /workspace/llama.cpp -B /workspace/llama.cpp/build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DLLAMA_CURL=OFF && cmake --build /workspace/llama.cpp/build --config Release -j 16 --target llama-server llama-cli)"

# 4) Idempotencia: si ya responde, no lo duplicamos.
if curl -fsS --max-time 5 "${BASE_URL}/health" >/dev/null 2>&1; then
  printf 'OK: llama-server ya está sirviendo en %s (no se inicia otro).\n' "${BASE_URL}"
  exit 0
fi

printf 'Iniciando llama-server (ctx=%s, ngl=%s, puerto %s)... log: %s\n' \
  "${CTX}" "${NGL}" "${PORT}" "${LOG}"
nohup "${LLAMA_BIN}" \
  --model "${MODEL_PATH}" \
  --ctx-size "${CTX}" \
  --n-gpu-layers "${NGL}" \
  --host 0.0.0.0 \
  --port "${PORT}" \
  > "${LOG}" 2>&1 &

# 5) Esperar a que cargue el modelo y responda /health (carga desde disco: ~1 min).
for i in $(seq 1 60); do
  if curl -fsS --max-time 5 "${BASE_URL}/health" >/dev/null 2>&1; then
    printf 'OK: llama-server sirviendo en %s (pid %s).\n' "${BASE_URL}" "$!"
    printf '     AC2: verificar VRAM y contexto con nvidia-smi + /props (scripts/verify-serve.sh).\n'
    exit 0
  fi
  sleep 2
done

fail "el servidor no respondió /health en 120 s; revisá ${LOG}"
