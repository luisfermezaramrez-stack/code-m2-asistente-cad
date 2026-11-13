#!/usr/bin/env bash
# HEREDADO (HU-01): desde HU-14 el modelo es la API de DeepSeek. Este script solo
# sirve para reproducir la línea base con Gemma 4 12B ConstraintKit.
# HU-01 AC2 — Verifica que llama.cpp sirva el modelo con contexto de 8192 tokens
# y que la VRAM ocupada por el proceso no supere los 16 GB.
#
# Uso: bash scripts/verify-serve.sh
#   LLAMA_PORT=8080       puerto publicado por el servicio `llama`
#   LLAMA_BASE_URL=...    URL base del servidor (default: http://127.0.0.1:$LLAMA_PORT)
#   LLAMA_REMOTE=1        modo remoto (modelo en Vast.ai vía túnel SSH): se salta el
#                         chequeo de VRAM local; la evidencia de VRAM se captura
#                         ejecutando este mismo script DENTRO de la instancia.
#   EXPECTED_CTX=8192     contexto exigido por AC2
#   MAX_VRAM_MIB=16384    tope de VRAM exigido por AC2
set -euo pipefail

PORT="${LLAMA_PORT:-8080}"
EXPECTED_CTX="${EXPECTED_CTX:-8192}"
MAX_VRAM_MIB="${MAX_VRAM_MIB:-16384}"
BASE_URL="${LLAMA_BASE_URL:-http://127.0.0.1:${PORT}}"
REMOTE="${LLAMA_REMOTE:-0}"

fail() { printf 'FALLA: %s\n' "$*" >&2; exit 1; }

# 1) El servidor responde y el modelo está cargado.
health="$(curl -fsS --max-time 10 "${BASE_URL}/health" 2>/dev/null)" \
  || fail "el servidor llama.cpp no responde en ${BASE_URL}/health (¿'docker compose up -d llama'?)"

# 2) Contexto efectivo reportado por el servidor.
ctx="$(curl -fsS --max-time 10 "${BASE_URL}/props" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["default_generation_settings"]["n_ctx"])')" \
  || fail "no se pudo leer /props"
[ "${ctx}" = "${EXPECTED_CTX}" ] || fail "n_ctx=${ctx}, se esperaban ${EXPECTED_CTX} tokens"

# 3) VRAM ocupada por los procesos de cómputo de la GPU.
#    En modo remoto (LLAMA_REMOTE=1) la máquina local puede no tener GPU;
#    la evidencia de VRAM se captura corriendo este script en la instancia.
used_mib=""
if [ "${REMOTE}" = "1" ]; then
  printf 'AVISO: modo remoto — chequeo de VRAM diferido a la instancia.\n'
elif command -v nvidia-smi >/dev/null 2>&1; then
  used_mib="$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits \
    | awk '{s+=$1} END{print s+0}')"
  [ "${used_mib}" -le "${MAX_VRAM_MIB}" ] \
    || fail "VRAM usada ${used_mib} MiB, tope ${MAX_VRAM_MIB} MiB"
else
  fail "nvidia-smi no está disponible en esta máquina (¿modo remoto? export LLAMA_REMOTE=1)"
fi

model="$(curl -fsS --max-time 10 "${BASE_URL}/v1/models" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')"

if [ -n "${used_mib}" ]; then
  printf 'OK AC2: modelo=%s n_ctx=%s VRAM=%s MiB (tope %s MiB) health=%s\n' \
    "${model}" "${ctx}" "${used_mib}" "${MAX_VRAM_MIB}" "$(printf '%s' "${health}" | tr -d '\n')"
else
  printf 'OK AC2 (parcial remoto): modelo=%s n_ctx=%s VRAM=(verificar en la instancia) health=%s\n' \
    "${model}" "${ctx}" "$(printf '%s' "${health}" | tr -d '\n')"
fi
