# Phulax — the six-verb contract (build plan §6).
# Every phase assumes these verbs work from a clean clone.
# "Works on my machine" is banned by construction.

.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help bootstrap dev down migrate seed test demo

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Create venv, install locked dependencies, install git hooks
	uv sync --all-packages
	@# macOS/iCloud can set the UF_HIDDEN flag inside .venv; CPython 3.13+
	@# skips hidden .pth files, which silently breaks editable installs.
	@command -v chflags >/dev/null 2>&1 && find .venv -name '*.pth' -exec chflags nohidden {} + || true
	uv run pre-commit install
	@echo "bootstrap: done. Copy .env.example to .env before 'make dev'."

dev: ## Start local services (Day 0: postgres + redis only)
	docker compose up -d --wait postgres redis
	docker compose ps

down: ## Stop local services
	docker compose down

migrate: ## Apply database schema (Day 0 stub — Day 1 wires migrations)
	@echo "migrate: no migrations yet (Day 0 stub). Day 1 adds the first schema."

seed: ## Seed demo org, agent, tools, policies (Day 0 stub)
	@echo "seed: nothing to seed yet (Day 0 stub). Arrives with the first schema."

test: ## Run unit + integration tests
	uv run pytest

demo: ## One safe tool call through the gateway (Day 0 stub)
	@echo "demo: gateway not built yet (Day 0 stub)."
	@echo "Tomorrow's outcome: an authenticated agent call reaches the gateway"
	@echo "and produces a structured decision event."
