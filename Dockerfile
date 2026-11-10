# Asistente CAD (HU-01).
# Base Python 3.12-slim, igual que el contenedor cadkit del autor de constraint-kit.
# El núcleo CAD (constraint-kit + cadquery/build123d/OpenCascade) se instala como
# dependencia git vía uv (extra [kernel,service,solver]), no desde una imagen Docker.
FROM python:3.12-slim

# Dependencias de sistema para el kernel CAD (OpenCascade wheel manylinux + GL) y git.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglu1-mesa libxrender1 libxext6 libsm6 ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# uv (gestor de dependencias del proyecto)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copiar manifiestos, lockfile y código propio
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data
COPY vendor ./vendor

# python-solvespace es una extensión C++ sin wheel: se compila con build-essential
# y luego se purga el toolchain para mantener la imagen liviana (patrón de cadkit/Dockerfile).
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && uv sync --frozen --no-dev \
    && apt-get purge -y --auto-remove build-essential && rm -rf /var/lib/apt/lists/*

EXPOSE 8000 7860

CMD ["uv", "run", "uvicorn", "m2_cad.api:app", "--host", "0.0.0.0", "--port", "8000"]
