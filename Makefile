# Entry point for every common task. Prefer adding a target over documenting a long command.
#
# Node 24 and Python 3.13 are required; the system defaults are too old (node 12, python 3.9).
# NODE_BIN pins the nvm-installed toolchain so targets work without `nvm use` first.

NODE_BIN := $(HOME)/.nvm/versions/node/v24.12.0/bin
export PATH := $(NODE_BIN):$(PATH)

PLATFORM := apps/platform
SITE     := apps/site
EXAMPLES := apps/examples
GRADER   := packages/autograder

.DEFAULT_GOAL := help
.PHONY: help setup platform site test test-platform test-grader lint fmt check clean

help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Install both toolchains
	cd $(PLATFORM) && uv sync
	cd $(GRADER) && uv sync
	cd $(SITE) && npm ci

platform: ## Run the Django dev server
	cd $(PLATFORM) && uv run python manage.py runserver

site: ## Run the Astro dev server
	cd $(SITE) && npm run dev

site-build: ## Build the site to static output
	cd $(SITE) && npm run build

test: test-platform test-grader ## Run every test suite

test-platform: ## Platform tests
	cd $(PLATFORM) && uv run pytest

test-grader: ## Autograder tests
	cd $(GRADER) && uv run pytest

lint: ## Lint everything
	cd $(PLATFORM) && uv run ruff check .
	cd $(GRADER) && uv run ruff check .
	cd $(SITE) && npm run lint --if-present

fmt: ## Format everything
	cd $(PLATFORM) && uv run black .
	cd $(GRADER) && uv run black .

check: lint test ## What CI runs

clean: ## Remove build artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	rm -rf $(SITE)/dist $(SITE)/.astro
