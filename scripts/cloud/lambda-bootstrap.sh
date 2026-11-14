#!/usr/bin/env bash
# HEREDADO (HU-01): desde HU-14 el modelo es la API de DeepSeek. Este script solo
# sirve para reproducir la línea base con Gemma 4 12B ConstraintKit.
# Prepara una instancia de Lambda (Ubuntu + GPU NVIDIA) para correr la HU-01.
# Deja driver -> Docker -> NVIDIA Container Toolkit listos y valida la GPU dentro
# de un contenedor. Es idempotente: se puede correr más de una vez.
#
# Uso (en la instancia, recién creada):
#   bash scripts/cloud/lambda-bootstrap.sh
set -euo pipefail

log() { printf '\n==> %s\n' "$*"; }

log "GPU y driver"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

if ! command -v docker >/dev/null 2>&1; then
  log "Instalando Docker"
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "${USER}" || true

if ! dpkg -s nvidia-container-toolkit >/dev/null 2>&1; then
  log "Instalando NVIDIA Container Toolkit"
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq nvidia-container-toolkit
fi

log "Registrando el runtime nvidia en Docker"
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

log "Smoke test: la GPU se ve desde dentro de un contenedor"
sudo docker run --rm --gpus all ubuntu:22.04 \
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

cat <<'FIN'

==> Listo. Siguiente paso en la instancia:

  git clone https://github.com/luisfermezaramrez-stack/code-m2-asistente-cad.git
  cd code-m2-asistente-cad
  git switch feature/hu-01-gemma-constraintkit-serve
  bash scripts/vendor-constraint-kit.sh   # o: make vendor
  make model-fetch                        # descarga 9,8 GB y verifica SHA-256 (AC1)
  docker compose up -d llama
  bash scripts/verify-serve.sh            # AC2: contexto 8192 y VRAM <= 16 GB

Nota: el grupo docker recién queda activo en una sesión nueva; si `docker` pide
permisos, salí y volvé a entrar por SSH (o usá `sudo docker ...`).
FIN
