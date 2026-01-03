# Makefile for mcp-makefile-server development

.PHONY: help version bump bump-minor bump-major release sync test lint format type-check security-scan check clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

version: ## Show current version from VERSION file
	@cat VERSION

bump: ## @internal Bump patch version (0.1.0 -> 0.1.1)
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "Version: $$CURRENT -> $$NEW_VERSION"

bump-minor: ## @internal Bump minor version (0.1.0 -> 0.2.0)
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "Version: $$CURRENT -> $$NEW_VERSION"

bump-major: ## @internal Bump major version (0.1.0 -> 1.0.0)
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "Version: $$CURRENT -> $$NEW_VERSION"

release: ## Create new release with version bump, tests, git tag, and push. Prompts for version type: [p]atch, [m]inor, [M]ajor, or [n]o bump. Use DRY_RUN=1 to preview without making changes
	@CURRENT=$$(cat VERSION); \
	DRY=$${DRY_RUN:-0}; \
	if [ "$$DRY" = "1" ]; then echo "[DRY RUN MODE - No changes will be made]"; echo ""; fi; \
	echo "Current version: $$CURRENT"; \
	echo ""; \
	echo "Bump version? [p]atch, [m]inor, [M]ajor, [n]o (use current): "; \
	read -r BUMP; \
	case "$$BUMP" in \
		p|patch) \
			if [ "$$DRY" = "1" ]; then \
				MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
				MINOR=$$(echo $$CURRENT | cut -d. -f2); \
				PATCH=$$(echo $$CURRENT | cut -d. -f3); \
				NEW_PATCH=$$((PATCH + 1)); \
				VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
				echo "[DRY RUN] Would bump to $$VERSION"; \
			else \
				$(MAKE) bump; VERSION=$$(cat VERSION); \
			fi;; \
		m|minor) \
			if [ "$$DRY" = "1" ]; then \
				MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
				MINOR=$$(echo $$CURRENT | cut -d. -f2); \
				NEW_MINOR=$$((MINOR + 1)); \
				VERSION="$$MAJOR.$$NEW_MINOR.0"; \
				echo "[DRY RUN] Would bump to $$VERSION"; \
			else \
				$(MAKE) bump-minor; VERSION=$$(cat VERSION); \
			fi;; \
		M|major) \
			if [ "$$DRY" = "1" ]; then \
				MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
				NEW_MAJOR=$$((MAJOR + 1)); \
				VERSION="$$NEW_MAJOR.0.0"; \
				echo "[DRY RUN] Would bump to $$VERSION"; \
			else \
				$(MAKE) bump-major; VERSION=$$(cat VERSION); \
			fi;; \
		n|no|"") VERSION=$$CURRENT;; \
		*) echo "Invalid option"; exit 1;; \
	esac; \
	TAG="v$$VERSION"; \
	echo ""; \
	echo "Releasing $$TAG..."; \
	echo ""; \
	if [ "$$DRY" = "1" ]; then \
		echo "[DRY RUN] Would run: make check test"; \
		echo "[DRY RUN] Would commit changes with message: Release $$TAG"; \
		echo "[DRY RUN] Would push to origin main"; \
		echo "[DRY RUN] Would create tag: $$TAG"; \
		echo "[DRY RUN] Would push tag: $$TAG"; \
		echo ""; \
		echo "[DRY RUN] Complete - no changes made"; \
	else \
		echo "Running checks and tests..."; \
		$(MAKE) check test || { echo "FAIL: Checks/tests failed, aborting release"; exit 1; }; \
		echo ""; \
		echo "Committing changes..."; \
		git add -A && git commit -m "Release $$TAG" || true; \
		echo "Pushing to origin..."; \
		git push origin main || { echo "FAIL: Push failed"; exit 1; }; \
		echo ""; \
		echo "Creating tag $$TAG..."; \
		git tag -a "$$TAG" -m "Release $$TAG" || { echo "FAIL: Tag creation failed (may already exist)"; exit 1; }; \
		echo "Pushing tag $$TAG..."; \
		git push origin "$$TAG" || { echo "FAIL: Tag push failed"; exit 1; }; \
		echo ""; \
		echo "PASS: Released $$TAG"; \
	fi

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
