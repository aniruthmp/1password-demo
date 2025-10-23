.PHONY: install test lint format clean coverage help

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using Poetry
	poetry install

install-dev: ## Install dependencies including dev tools
	poetry install --with dev

test: ## Run all tests
	poetry run pytest

test-v: ## Run tests with verbose output
	poetry run pytest -v

test-cov: ## Run tests with coverage report
	poetry run pytest --cov=src --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode
	poetry run pytest-watch

lint: ## Run linters (ruff)
	poetry run ruff check src/ tests/

lint-fix: ## Run linters and fix issues
	poetry run ruff check --fix src/ tests/

format: ## Format code with black
	poetry run black src/ tests/

format-check: ## Check code formatting without making changes
	poetry run black --check src/ tests/

typecheck: ## Run type checking with mypy
	poetry run mypy src/

qa: format lint typecheck test ## Run all quality checks (format, lint, typecheck, test)

clean: ## Clean up temporary files and caches
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

shell: ## Start Poetry shell
	poetry shell

update: ## Update dependencies
	poetry update

lock: ## Update poetry.lock file
	poetry lock

build: ## Build the package
	poetry build

.DEFAULT_GOAL := help

