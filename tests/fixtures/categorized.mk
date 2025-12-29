# Makefile with categories

## Category: Testing

test: ## Run tests
	pytest

lint: ## Run linter
	ruff check .

## Category: Building

build: ## Build package
	python -m build

clean: ## Clean build artifacts
	rm -rf dist/ build/
