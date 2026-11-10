#!/usr/bin/env bash
# AC4 de HU-09: bloquea archivos de pesos antes de cada commit.
# pre-commit pasa como argumentos los archivos que coinciden con `files:`
# en .pre-commit-config.yaml; si hay al menos uno, el commit se detiene.
# Los pesos viven en models/ (ignorado por git) y se descargan con
# `make model-fetch`; nunca viajan en el historial.
set -euo pipefail

if [ "$#" -gt 0 ]; then
  printf 'Archivos de pesos no se versionan:\n' >&2
  printf '  %s\n' "$@" >&2
  printf 'Se descargan con `make model-fetch` y quedan en models/ (ignorado por git).\n' >&2
  exit 1
fi
