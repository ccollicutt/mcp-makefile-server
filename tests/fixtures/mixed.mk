# Mix of documented, undocumented, and internal targets

.PHONY: test clean internal-helper deploy-dangerous

test: ## Run tests
	pytest

clean: ## Clean build artifacts
	rm -rf dist/ build/

# This target has no ## description, should NOT be exposed
internal-helper:
	@echo "Internal use only"

# This target also has no ## description
_private_target: internal-helper
	@echo "Private"

# Documented but marked as internal - NOT exposed to MCP
deploy-dangerous: ## @internal Deploy without safety checks
	./deploy-dangerous.sh

# Documented but marked to skip - NOT exposed to MCP
cleanup-prod: ## @skip Clean production database
	./cleanup-prod.sh

# This WILL be exposed (has ## and no @internal/@skip)
deploy: test ## Deploy to production with all checks
	./deploy-safe.sh
