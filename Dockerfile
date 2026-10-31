# Imagen base del autor de constraint-kit (CadQuery, build123d, OpenCascade,
# SolveSpace). Ajustá la etiqueta según la imagen publicada en
# github.com/jajmangold/constraint-kit.
FROM jajmangold/constraint-kit:latest

WORKDIR /app

# Copiar el código propio
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data

# Instalar dependencias del proyecto con uv (sin pip install ni requirements.txt)
RUN uv sync --frozen --no-dev

EXPOSE 8000 7860

CMD ["uv", "run", "uvicorn", "m2_cad.api:app", "--host", "0.0.0.0", "--port", "8000"]
