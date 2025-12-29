# Makefile for mcp-makefile-server development

.PHONY: help sync test lint format type-check security-scan check clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

sync: ## Install dependencies and create lockfile
	uv sync --extra dev

test: ## Run all tests
	PYTHONPATH=src uv run --frozen pytest tests/ -v

test-coverage: ## Run tests with coverage report
	PYTHONPATH=src uv run --frozen pytest tests/ -v --cov=src/mcp_makefile --cov-report=html --cov-report=term

lint: ## Run ruff linter
	uv run --frozen ruff check src/ tests/

format: ## Format code with ruff
	uv run --frozen ruff format src/ tests/
	uv run --frozen ruff check --fix src/ tests/

type-check: ## Run pyright type checker
	PYTHONPATH=src uv run --frozen pyright src/

security-scan: ## Run security scans (bandit, safety, vulture, pylint)
	@echo "Running bandit security scan..."
	@uv run --frozen bandit -r src/ -f txt || true
	@echo ""
	@echo "Checking dependencies for known vulnerabilities..."
	@uv run --frozen safety check 2>&1 | grep -E "(vulnerabilities found|Checked|All good)" || echo "Safety check completed"
	@echo ""
	@echo "Checking for dead code..."
	@uv run --frozen vulture src/ --min-confidence 80 || true
	@echo ""
	@echo "Checking for code duplication..."
	@uv run --frozen pylint src/ --disable=all --enable=duplicate-code || true

check: format lint type-check security-scan ## Run all static checks and security scans

clean: ## Clean cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
