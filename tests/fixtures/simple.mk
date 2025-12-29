# Simple Makefile for testing
.PHONY: test build

test: ## Run tests
	pytest

build: test ## Build package
	python -m build
