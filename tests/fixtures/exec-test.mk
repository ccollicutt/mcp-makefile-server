# Makefile for executor testing
.PHONY: success fail slow echo-var

success: ## Always succeeds
	@echo "Success!"

fail: ## Always fails
	@echo "Failing..." && exit 1

slow: ## Takes 2 seconds
	@sleep 2 && echo "Done"

echo-var: ## Echo a variable
	@echo "VAR=$(VAR)"
