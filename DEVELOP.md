# Development Guide

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ccollicutt/mcp-makefile-server.git
cd mcp-makefile-server

# Install dependencies
make sync

# View available commands
make help
```

## Project Structure

```
src/mcp_makefile/
├── core/
│   ├── models.py      # Data models
│   ├── parser.py      # Makefile parsing
│   └── executor.py    # Command execution
├── server.py          # MCP server
└── exceptions.py      # Custom exceptions

tests/
├── unit/              # Unit tests
├── fixtures/          # Test Makefiles
└── conftest.py        # Test configuration
```

## Testing

```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run all quality checks (format, lint, type-check, security-scan)
make check
```

## Quality Checks

The project includes comprehensive quality checks:

| Check | Tool | Description |
|-------|------|-------------|
| Formatting | Ruff | Code formatting |
| Linting | Ruff | Code quality checks |
| Type checking | Pyright | Static type analysis |
| Security | Bandit | Python security issues |
| Dependencies | Safety | Known vulnerabilities |
| Dead code | Vulture | Unused code detection |
| Duplication | Pylint | Code duplication |

Run all checks:
```bash
make check
```

## Usage from Python

### Basic Usage

```python
from pathlib import Path
from mcp_makefile import MakefileMCPServer

# Create server
server = MakefileMCPServer(
    makefile_path=Path("./Makefile"),
    allowed_targets=["test", "build", "deploy-staging"]  # Optional allowlist
)

# Initialize and run
await server.initialize()
# Server is now ready to handle MCP requests
```

### Tool Parameters

When calling targets through MCP, you can pass optional parameters:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `variables` | object | Make variables to pass (e.g., `{"DEBUG": "1"}`) | `{}` |
| `timeout` | integer | Timeout in seconds (min: 1, max recommended: 3600) | `300` |

**Example:**
```python
# Call a target with custom timeout for long-running operations
await mcp_client.call_tool("deploy", {
    "variables": {"ENV": "production"},
    "timeout": 1800  # 30 minutes for deployment
})
```

### Dry-Run Mode (Testing)

Use `DryRunMakeExecutor` to validate targets without actually running commands:

```python
from pathlib import Path
from mcp_makefile import MakefileMCPServer, DryRunMakeExecutor

# Create executor that doesn't run commands
executor = DryRunMakeExecutor(
    mock_success=True,
    mock_output="Simulated output"
)

# Create server with dry-run executor
server = MakefileMCPServer(
    makefile_path=Path("./Makefile"),
    executor=executor
)

await server.initialize()

# Calls will be logged but not executed
# Check what would have been executed:
print(executor.executed_targets)  # List of target names that were called
```

## Example Makefiles

See `tests/fixtures/` for example Makefiles:

| File | Description |
|------|-------------|
| `simple.mk` | Basic targets |
| `categorized.mk` | With category organization |
| `mixed.mk` | Shows internal targets and filtering |

## Contributing

When contributing:

1. Run `make check` before committing
2. Add tests for new features
3. Update documentation as needed
4. Follow existing code patterns
5. Keep commit messages clear and descriptive
