# Common tasks. Run `make help` for the list.
.DEFAULT_GOAL := help
SHELL := /bin/bash

API := api
WEB := web
PY := $(API)/.venv/bin/python

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install API (venv) and web dependencies
	python3 -m venv $(API)/.venv
	$(PY) -m pip install -e "$(API)[dev]"
	cd $(WEB) && npm ci

db: ## Start only PostgreSQL in Docker (port 5432)
	docker compose up -d db

demo-data: ## Import recent labels for a few common drugs from DailyMed
	$(API)/.venv/bin/pillmark import drug metformin lisinopril atorvastatin amlodipine ibuprofen \
		acetaminophen gabapentin sertraline omeprazole amoxicillin --per-name 20

api: ## Run the API with reload on :8000
	$(API)/.venv/bin/pillmark serve --reload

web: ## Run the web dev server on :5173
	cd $(WEB) && npm run dev

lint: ## Lint and type-check everything
	cd $(API) && .venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests && .venv/bin/mypy
	cd $(WEB) && npm run lint && npm run check

test: ## Run API and web tests (API tests need PILLMARK_TEST_DATABASE_URL)
	cd $(API) && .venv/bin/pytest
	cd $(WEB) && npm test

e2e: ## Browser tests against a running API (API_URL, default http://127.0.0.1:8000)
	cd $(WEB) && npx playwright test

up: ## Build and start the full stack with docker compose
	docker compose up -d --build

down: ## Stop the stack
	docker compose down

version: ## Show the current version
	@python3 scripts/version.py show

release-check: ## Check that every version number agrees
	python3 scripts/version.py check

bump-patch bump-minor bump-major: ## Bump the version everywhere (then edit CHANGELOG.md)
	python3 scripts/version.py bump $(subst bump-,,$@)

.PHONY: help install db demo-data api web lint test e2e up down version release-check bump-patch bump-minor bump-major
