# =============================================================================
# MyHanout AI — raccourcis dev. `make help` pour la liste.
# =============================================================================
.DEFAULT_GOAL := help
COMPOSE := docker compose
BACKEND := $(COMPOSE) exec api

.PHONY: help up down logs build restart ps \
        lint format typecheck test check \
        migrate makemigration seed shell

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Démarre toute la stack (postgres, redis, api, worker, frontend)
	$(COMPOSE) up -d --build

down: ## Stoppe et supprime les conteneurs
	$(COMPOSE) down

logs: ## Suit les logs de tous les services
	$(COMPOSE) logs -f

build: ## (Re)build les images
	$(COMPOSE) build

restart: down up ## Redémarre la stack

ps: ## Liste les services
	$(COMPOSE) ps

lint: ## Ruff (lint)
	ruff check backend

format: ## Black + ruff --fix
	black backend && ruff check --fix backend

typecheck: ## mypy
	mypy backend/app

test: ## pytest
	pytest

check: lint typecheck test ## Lint + typecheck + tests

migrate: ## Applique les migrations Alembic
	$(BACKEND) alembic upgrade head

makemigration: ## Génère une migration (m="message")
	$(BACKEND) alembic revision --autogenerate -m "$(m)"

seed: ## Charge les données de seed
	$(BACKEND) python -m app.db.seed

shell: ## Shell Python dans le conteneur api
	$(BACKEND) python
