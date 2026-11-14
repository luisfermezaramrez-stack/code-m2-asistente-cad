# HU-15: compila Vue sin requerir Node en la imagen de ejecución.
FROM node:24-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
COPY design/tokens.css /build/design/tokens.css
RUN npm run typecheck && npm run build

# Vendor obtenido dentro del build, sin preparación manual del host.
FROM python:3.12-slim AS vendor-build
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY scripts/vendor-constraint-kit.sh ./scripts/vendor-constraint-kit.sh
RUN sed -i 's/\r$//' scripts/vendor-constraint-kit.sh \
    && bash scripts/vendor-constraint-kit.sh \
    && rm -rf vendor/constraint-kit/.git

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    CFLAGS="-std=gnu17" \
    M2_FRONTEND_DIST=/app/frontend/dist

# Dependencias de sistema para el kernel CAD (OpenCascade wheel manylinux + GL) y git.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglu1-mesa libxrender1 libxext6 libsm6 ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# uv (gestor de dependencias del proyecto)
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app

# Copiar manifiestos, lockfile y código propio
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data
COPY --from=vendor-build /app/vendor/constraint-kit ./vendor/constraint-kit
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

# python-solvespace es una extensión C++ sin wheel: se compila con build-essential
# y luego se purga el toolchain para mantener la imagen liviana (patrón de cadkit/Dockerfile).
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && uv sync --frozen --no-dev \
    && apt-get purge -y --auto-remove build-essential && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD ["/app/.venv/bin/python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3)"]

# Un worker: trabajos SSE y cancelación en memoria del proceso.
CMD ["uv", "run", "--no-sync", "uvicorn", "m2_cad.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
