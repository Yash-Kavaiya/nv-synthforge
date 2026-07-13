SHELL := /bin/sh

PYTHON ?= python
UV ?= uv
PNPM ?= pnpm
DOCKER_COMPOSE ?= docker compose
BACKEND_DIR ?= backend
FRONTEND_DIR ?= frontend

.DEFAULT_GOAL := help

.PHONY: help install install-backend install-frontend backend-dev frontend-dev test test-backend test-frontend lint lint-frontend build build-frontend validate-infra smoke e2e-smoke compose-config compose-up compose-down clean

help: ## Show available commands
	@printf '%s\n' \
	  'NV-SynthForge commands:' \
	  '  make install          Install backend and frontend dependencies' \
	  '  make backend-dev      Start FastAPI on port 8000' \
	  '  make frontend-dev     Start Next.js on port 3000' \
	  '  make test             Run backend tests' \
	  '  make lint             Run frontend lint' \
	  '  make build            Build the frontend production bundle' \
	  '  make validate-infra   Validate YAML and infrastructure contracts' \
	  '  make smoke            Probe running API and frontend services' \
	  '  make e2e-smoke        Generate/render/benchmark an offline API batch' \
	  '  make compose-config   Validate resolved Compose configuration' \
	  '  make compose-up       Build and start both containers' \
	  '  make compose-down     Stop the Compose stack' \
	  '' \
	  'Windows: run with Git Bash/WSL; use PYTHON=py if needed.'

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies
	cd $(BACKEND_DIR) && $(UV) sync

install-frontend: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && corepack enable && $(PNPM) install --frozen-lockfile

backend-dev: ## Start the backend development server
	cd $(BACKEND_DIR) && $(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev: ## Start the frontend development server
	cd $(FRONTEND_DIR) && $(PNPM) run dev

test: test-backend test-frontend ## Run all automated tests

test-backend: ## Run backend tests
	cd $(BACKEND_DIR) && $(UV) run pytest -q

test-frontend: ## Run frontend tests
	cd $(FRONTEND_DIR) && $(PNPM) run test

lint: lint-frontend ## Run all configured linters

lint-frontend: ## Run frontend ESLint
	cd $(FRONTEND_DIR) && $(PNPM) run lint

build: build-frontend ## Build production assets

build-frontend: ## Build the Next.js application
	cd $(FRONTEND_DIR) && $(PNPM) run build

validate-infra: ## Validate YAML and infrastructure contracts
	$(UV) run --no-project --with PyYAML==6.0.3 python scripts/validate-infra.py

smoke: ## Probe a running local or deployed stack
	sh scripts/smoke-test.sh

e2e-smoke: ## Generate, render, download, persist, and benchmark two offline invoices
	$(PYTHON) scripts/e2e-smoke.py

compose-config: ## Render and validate Compose configuration
	$(DOCKER_COMPOSE) config

compose-up: ## Build and start the local stack
	$(DOCKER_COMPOSE) up --build

compose-down: ## Stop the local stack
	$(DOCKER_COMPOSE) down

clean: ## Remove local caches/build outputs (not artifacts)
	$(PYTHON) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('backend/.pytest_cache','backend/.ruff_cache','frontend/.next')]"
