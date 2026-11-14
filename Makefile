# Makefile del asistente CAD (uv + pytest + Ruff + Docker)
# Uso: `make <objetivo>` — `make help` lista todo.

.PHONY: help install lock vendor test cov lint format check \
        precommit-install precommit build up down clean bench bench-report \
        model-fetch model-serve verify-serve kernel-image kernel-test cloud-setup \
        frontend-install frontend-test frontend-typecheck frontend-build frontend-check \
        mlflow

help: ## Lista los objetivos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependencias (dev incluidas) con uv
	uv sync --locked --dev

vendor: ## Vendea y parchea constraint-kit (necesario antes de uv sync/build)
	bash scripts/vendor-constraint-kit.sh

lock: ## Regenera uv.lock
	uv lock

test: frontend-build ## Corre pytest con el build integrado
	uv run --locked pytest

kernel-image: ## Construye la imagen del contenedor del autor de constraint-kit (AC3)
	docker build -t cadkit:0.1 vendor/constraint-kit/cadkit

kernel-test: kernel-image ## Corre las 113 pruebas del kernel en el contenedor del autor (AC3)
	docker run --rm --user "$$(id -u):$$(id -g)" \
		-v "$$(pwd)/vendor/constraint-kit:/tmp/constraint-kit" \
		-w /tmp/constraint-kit -e PYTHONPATH=/tmp/constraint-kit -e HOME=/tmp \
		cadkit:0.1 python3 tests/test_kernel.py

bench: ## HU-14 AC7: corre el banco HU-02 contra el modelo (gasta tokens; IDS=...)
	uv run python -m m2_cad.banco $(if $(IDS),--ids $(IDS))

bench-report: ## HU-07: evalúa 40 solicitudes HTTP y genera reporte por familia (gasta tokens)
	uv run --locked python -m m2_cad.evaluacion

cov: frontend-build ## Corre pytest con reporte de cobertura
	uv run --locked pytest --cov=src/m2_cad --cov-report=term-missing

lint: ## Ruff con reglas E, F, I, B
	uv run ruff check src tests scripts/verify_hu15_deployment.py

format: ## Aplica ruff format
	uv run ruff format src tests

check: lint frontend-check cov ## Ruff, SPA y pytest con cobertura (paridad con CI)

frontend-install: ## Instala dependencias Node exactamente desde el lockfile
	npm --prefix frontend ci

frontend-test: ## Pruebas Vitest de la SPA
	npm --prefix frontend test

frontend-typecheck: ## Comprobación TypeScript y componentes Vue
	npm --prefix frontend run typecheck

frontend-build: ## Build Vue servido por FastAPI
	npm --prefix frontend run build

frontend-check: frontend-test frontend-typecheck frontend-build ## Verifica frontend completo

precommit-install: ## Instala los hooks de pre-commit
	uv run pre-commit install

precommit: ## Corre pre-commit sobre todos los archivos
	uv run pre-commit run --all-files

build: ## Construye la imagen Docker
	docker compose build

model-fetch: ## [Heredado HU-01] Descarga y verifica el modelo GGUF
	bash scripts/fetch-model.sh

model-serve: ## [Heredado HU-01] Levanta solo el servidor llama.cpp
	docker compose -f docker-compose.yml -f docker-compose.gemma.yml up llama

verify-serve: ## [Heredado HU-01] AC2: contexto 8192 y VRAM <= 16 GB del servicio llama en ejecución
	bash scripts/verify-serve.sh

cloud-setup: ## [Heredado HU-01] Prepara una instancia de Lambda: Docker + NVIDIA Container Toolkit
	bash scripts/cloud/lambda-bootstrap.sh

mlflow: ## HU-16: levanta solo el servidor MLflow (UI en http://127.0.0.1:5000)
	docker compose up -d mlflow

up: ## Levanta Vue/FastAPI con DeepSeek (requiere DEEPSEEK_API_KEY)
	docker compose up

down: ## Detiene el servicio
	docker compose down

clean: ## Borra cachés y artefactos generados
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov build dist \
		outputs data/outputs artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
