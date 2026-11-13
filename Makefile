# Makefile del asistente CAD (uv + pytest + Ruff + Docker)
# Uso: `make <objetivo>` — `make help` lista todo.

.PHONY: help install lock vendor test cov lint format check \
        precommit-install precommit build up down clean bench \
        model-fetch model-serve verify-serve kernel-image kernel-test cloud-setup

help: ## Lista los objetivos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias (dev incluidas) con uv
	uv sync --dev

vendor: ## Vendea y parchea constraint-kit (necesario antes de uv sync/build)
	bash scripts/vendor-constraint-kit.sh

lock: ## Regenera uv.lock
	uv lock

test: ## Corre la suite pytest
	uv run pytest

kernel-image: ## Construye la imagen del contenedor del autor de constraint-kit (AC3)
	docker build -t cadkit:0.1 vendor/constraint-kit/cadkit

kernel-test: kernel-image ## Corre las 113 pruebas del kernel en el contenedor del autor (AC3)
	docker run --rm --user "$$(id -u):$$(id -g)" \
		-v "$$(pwd)/vendor/constraint-kit:/tmp/constraint-kit" \
		-w /tmp/constraint-kit -e PYTHONPATH=/tmp/constraint-kit -e HOME=/tmp \
		cadkit:0.1 python3 tests/test_kernel.py

bench: ## HU-14 AC7: corre el banco HU-02 contra el modelo (gasta tokens; IDS=...)
	uv run python -m m2_cad.banco $(if $(IDS),--ids $(IDS))

cov: ## Corre pytest con reporte de cobertura
	uv run pytest --cov=src/m2_cad --cov-report=term-missing

lint: ## Ruff con reglas E, F, I, B
	uv run ruff check src tests

format: ## Aplica ruff format
	uv run ruff format src tests

check: lint test ## Ruff + pytest (lo que corre la CI)

precommit-install: ## Instala los hooks de pre-commit
	uv run pre-commit install

precommit: ## Corre pre-commit sobre todos los archivos
	uv run pre-commit run --all-files

build: ## Construye la imagen Docker
	docker compose build

model-fetch: ## Descarga y verifica el modelo GGUF (HU-01)
	bash scripts/fetch-model.sh

model-serve: ## Levanta solo el servidor llama.cpp (sin FastAPI)
	docker compose up llama

verify-serve: ## AC2: contexto 8192 y VRAM <= 16 GB del servicio llama en ejecución
	bash scripts/verify-serve.sh

cloud-setup: ## Prepara una instancia de Lambda: Docker + NVIDIA Container Toolkit
	bash scripts/cloud/lambda-bootstrap.sh

up: ## Levanta el servicio (llama + FastAPI + Gradio)
	docker compose up

down: ## Detiene el servicio
	docker compose down

clean: ## Borra cachés y artefactos generados
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov build dist \
		outputs data/outputs artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
