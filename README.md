# MCP Makefile Server

> [!TIP]
> Use this MCP server to easily expose Makefile targets as MCP tools. Let AI agents execute your Makefile targets through the Model Context Protocol.

## Table of Contents

- [What is the Value of mcp-makefile-server?](#what-is-the-value-of-mcp-makefile-server)
- [Features](#features)
- [TL;DR - Simplest Setup](#tldr---simplest-setup)
- [Usage Patterns](#usage-patterns)
  - [Project-Scoped vs Global Configuration](#project-scoped-vs-global-configuration)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation Method 1: Using uvx (Recommended)](#installation-method-1-using-uvx-recommended)
  - [Installation Method 2: Local Installation](#installation-method-2-local-installation)
  - [Claude Code Setup](#claude-code-setup)
- [Advanced Configuration](#advanced-configuration)
  - [Allowed Targets Filter](#allowed-targets-filter)
  - [Defaults](#defaults)
  - [Environment Variables](#environment-variables)
  - [Output Management](#output-management)
- [Removing and Uninstalling](#removing-and-uninstalling)
- [Troubleshooting](#troubleshooting)
- [Makefile Format](#makefile-format)
- [Development](#development)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [License](#license)

## What is the Value of mcp-makefile-server?

| Value                                          | What you get (benefit)                                                                                    | Why it matters in practice                                                                      |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **Turn your workflow into tools instantly**    | Anything you can run from a Makefile: scripts, CLIs, one-liners, pipelines, etc. become a first-class MCP tool      | You stop “rewriting tooling” for every assistant/client and just *expose what already works*    |
| **Tooling without building a tool platform**   | An MCP server that “just works” off your existing Make targets                                            | You avoid bespoke MCP coding, schemas, and glue logic because your Makefile *is* the integration layer  |
| **No need to remind the coding tool about the Makefile** | The coding tool doesn't need to know about the Makefile, it finds out what tools it has automatically via MCP. | You can simply add new targets to the Makefile and the coding tool will automatically know about them. |
| **Self-service automation**                    | Your assistant can add/adjust targets as needs evolve (you review + merge like normal code)               | Tooling grows at the speed of your project    |
| **One source of truth for “how we do things”** | The Makefile becomes the canonical catalog of project actions (build, test, lint, release, migrate, etc.) | No drift between docs, tribal knowledge, CI steps, etc.              |
| **Safer execution by design**                  | You expose only what you want (allowlists, internal/skip markers) and keep dangerous stuff hidden         | Only give the coding tool access to what it needs to do its job             |
| **Better guidance at the point of use**        | `##` comments become the tool’s instructions: options, inputs, side effects, outputs                      | The “how to use it” travels with the command, so it stays accurate as the target evolves        |
| **Composable building blocks**                 | Targets can depend on other targets (e.g., `build: test lint`) and form reliable workflows                | You get a clean, modular automation graph   |
| **Tooling portability**                        | Makefiles work almost everywhere; you’re not locked into a specific agent ecosystem                       | Your automation survives client churn. New assistant? Same Make targets |


## Features

| Feature | Description |
|---------|-------------|
| **Automatic Tool Discovery** | Parses Makefile and exposes documented targets as MCP tools |
| **Target Filtering** | Use allowlists to control which targets are exposed |
| **Progress Notifications** | MCP clients receive start/completion status updates for long-running targets |
| **Category Support** | Organize targets with `## Category:` headers |
| **Internal Targets** | Mark targets with `@internal` or `@skip` to exclude them |
| **Async Execution** | Non-blocking target execution with timeout support |
| **Output Management** | Optional truncation, file output with organized subdirectories, customizable temp location |
| **Configurable Timeouts** | Set custom timeout per target execution (default: 300s) |

## TL;DR - Simplest Setup

**In your project directory with a Makefile:**

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add MCP server to your project
claude mcp add-json --scope project makefile-server '{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/ccollicutt/mcp-makefile-server",
    "mcp-makefile-server",
    "./Makefile"
  ]
}'

# Restart Claude Code
```

**Done!** Your Makefile targets with `##` comments are now available as tools.

---

## Usage Patterns

### Project-Scoped vs Global Configuration

**Recommended: Project-Scoped**

The best way to use this MCP server is to point it at your **current project's Makefile** using `--scope project`. This approach:
- Gives Claude Code access to project-specific targets
- Keeps each project's automation isolated and relevant
- Allows different projects to have different Makefile targets

**Alternative: Global Configuration**

You can use `--scope global` to make the server available across all projects. This is useful if you have:
- A shared utilities Makefile with common tasks
- Cross-project tooling that you want available everywhere

**Both Configurations**

You can configure **both** a global instance and project-specific instances:
- **Global instance**: Points to a shared utilities Makefile (`~/makefiles/common.mk`)
- **Project instances**: Each project points to its own `./Makefile`

Each instance can point to a different Makefile and expose different targets. The global instance provides shared tools, while project instances provide project-specific automation.

---

## Quick Start

### Prerequisites

**Install uv** (if you don't have it):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

This gives you both `uv` and `uvx` commands.

---

### Installation Method 1: Using uvx (Recommended)

**No cloning needed!** `uvx` runs directly from GitHub:

```bash
# Test it works - preview your Makefile targets
uvx --from git+https://github.com/ccollicutt/mcp-makefile-server mcp-makefile-server preview ./Makefile
```

**What this does:**
- Downloads and caches the server from GitHub
- Runs the `preview` command on your `./Makefile`
- Shows what tools would be exposed

**Example output:**
```
Found 3 targets in ./Makefile:
  • test - Run test suite
  • build - Build package
  • deploy - Deploy to production
```

That's it! Now skip to [Claude Code Setup](#claude-code-setup) below.

---

### Installation Method 2: Local Installation

**Use this if you need to modify the code.**

**Step 1: Clone and install**
```bash
git clone https://github.com/ccollicutt/mcp-makefile-server.git
cd mcp-makefile-server
uv pip install .
```

**Step 2: Test it works**
```bash
# Preview your Makefile targets
uv run python -m mcp_makefile preview /path/to/your/Makefile

# Or just list tool names
uv run python -m mcp_makefile list /path/to/your/Makefile
```

---

**For Development:** See [DEVELOP.md](DEVELOP.md) for development setup instructions.

### Claude Code Setup

**Configure the MCP server for your project:**

**If you used Method 1 (uvx):**

```bash
cd ~/projects/my-app

claude mcp add-json --scope project makefile-server '{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/ccollicutt/mcp-makefile-server",
    "mcp-makefile-server",
    "./Makefile"
  ]
}'
```

**If you used Method 2 (local installation):**

```bash
cd ~/projects/my-app

claude mcp add-json --scope project makefile-server '{
  "type": "stdio",
  "command": "uv",
  "args": [
    "--directory",
    "/path/to/mcp-makefile-server",
    "run",
    "python",
    "-m",
    "mcp_makefile",
    "./Makefile"
  ]
}'
```

**What this does:**
- Creates `.mcp.json` in your project root (project-scoped)
- Configures Claude Code to use your Makefile targets as tools when working in this project

**For global setup (available in all projects):**

Replace `--scope project` with `--scope global` in the commands above. This creates a global MCP configuration, though **project-scoped is recommended** since each project typically has its own Makefile with project-specific targets.

**You can configure both:** A global instance for shared utilities and project-specific instances for each project's Makefile.

**Next step:** Restart Claude Code to load the server.

### Advanced Configuration

#### Allowed Targets Filter

Restrict which targets can be executed:

**Using uvx:**
```bash
claude mcp add-json --scope project makefile-server '{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/ccollicutt/mcp-makefile-server",
    "mcp-makefile-server",
    "./Makefile",
    "--allowed-targets",
    "test",
    "build",
    "lint"
  ]
}'
```

**Using local installation:**
```bash
claude mcp add-json --scope project makefile-server '{
  "type": "stdio",
  "command": "uv",
  "args": [
    "--directory",
    "/path/to/mcp-makefile-server",
    "run",
    "python",
    "-m",
    "mcp_makefile",
    "./Makefile",
    "--allowed-targets",
    "test",
    "build",
    "lint"
  ]
}'
```

#### Defaults

The server works out of the box with sensible defaults:

| Setting | Default Value | What it means |
|---------|---------------|---------------|
| **Output Length** | Unlimited (`0`) | All output is returned without truncation |
| **File Output** | Disabled | Output is not written to files (only returned in response) |
| **Temp Directory** | `/tmp` | Where temporary files are created (if file output is enabled) |
| **Timeout** | 300 seconds | Maximum execution time per target |
| **Allowed Targets** | All non-internal | All targets with `##` comments are exposed (except `@internal`/`@skip`) |
| **Log Level** | `INFO` | Standard logging verbosity |

**In other words:** The server returns all output directly to the client with no truncation or file writing, executes any documented target, and times out after 5 minutes.

#### Environment Variables

The server can also be configured via environment variables:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `MCP_MAKEFILE_PATH` | Path to Makefile | `./Makefile` |
| `MCP_MAKEFILE_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `MCP_MAKEFILE_ALLOWED_TARGETS` | Comma-separated list of allowed targets | All non-internal targets |
| `MCP_MAKEFILE_MAX_OUTPUT_CHARS` | Maximum characters to return from target output (0 = unlimited) | `0` (unlimited) |
| `MCP_MAKEFILE_WRITE_TO_FILE` | Write full output to temporary files (true/false) | `false` |
| `MCP_MAKEFILE_TEMP_DIR` | Base directory for temporary files | `/tmp` |

**Using environment variables in Claude Code:**

You can set environment variables in your `.mcp.json` configuration:

```bash
claude mcp add-json --scope project makefile-server '{
  "type": "stdio",
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/ccollicutt/mcp-makefile-server",
    "mcp-makefile-server",
    "./Makefile"
  ],
  "env": {
    "MCP_MAKEFILE_LOG_LEVEL": "DEBUG",
    "MCP_MAKEFILE_MAX_OUTPUT_CHARS": "5000",
    "MCP_MAKEFILE_WRITE_TO_FILE": "true",
    "MCP_MAKEFILE_TEMP_DIR": "/var/tmp"
  }
}'
```

This configures the server to:
- Use DEBUG logging
- Truncate output at 5000 characters
- Write full output to files in `/var/tmp/mcp-makefile-{random-id}/`

See [Claude Code Settings Documentation](https://code.claude.com/docs/en/settings) for more information.

**Setting environment variables in your shell:**
```bash
export MCP_MAKEFILE_PATH=/path/to/Makefile
export MCP_MAKEFILE_LOG_LEVEL=DEBUG
export MCP_MAKEFILE_ALLOWED_TARGETS="test,build,lint"
export MCP_MAKEFILE_MAX_OUTPUT_CHARS=5000
export MCP_MAKEFILE_WRITE_TO_FILE=true
export MCP_MAKEFILE_TEMP_DIR=/var/tmp
```

#### Output Management

The server provides two options for managing large output:

**Option 1: Truncate Output (Optional)**

By default, output is **unlimited**. To prevent token overload, you can enable truncation:

**Via environment variable:**
```bash
export MCP_MAKEFILE_MAX_OUTPUT_CHARS=5000  # Set >0 to truncate, 0 = unlimited
```

**Via command-line argument:**
```bash
mcp-makefile-server serve ./Makefile --max-output-chars 5000
```

When output is truncated, you'll see a message like:
```
Note: Output exceeded 5000 characters and was truncated.
Configure targets to log verbose output to files and return summaries instead.
```

**Option 2: Write to Temporary File**

Write full output to temporary files and return the file path. The server creates a unique subdirectory for each session to organize output files.

**Via environment variable:**
```bash
export MCP_MAKEFILE_WRITE_TO_FILE=true
```

**Via command-line argument:**
```bash
mcp-makefile-server serve ./Makefile --write-to-file
```

When enabled, you'll see:
```
Full output written to: /tmp/mcp-makefile-4a3f2e1b/test-1234567890.log
```

**Customize temp directory location:**
```bash
# Via environment variable
export MCP_MAKEFILE_TEMP_DIR=/var/tmp

# Via command-line argument
mcp-makefile-server serve ./Makefile --write-to-file --temp-dir /var/tmp
```

The server automatically creates a randomized subdirectory (e.g., `mcp-makefile-{random-id}`) within the temp directory to organize all output files for that session.

**You can combine both options** to truncate the returned output while keeping a full copy in a file.

---

### Removing and Uninstalling

#### Remove from Claude Code

To remove the MCP server from your project:

```bash
cd ~/projects/my-app
claude mcp remove "makefile-server" -s project
```

This removes the server from `.mcp.json`. Restart Claude Code to apply changes.

#### Uninstall the Server

**If you used Method 1 (uvx):**

The server is cached automatically. To clear it:
```bash
# Clear specific package from cache
uv cache clean mcp-makefile-server

# Or clear entire uv cache
uv cache clean
```

**If you used Method 2 (local installation):**

```bash
# Uninstall the package
uv pip uninstall mcp-makefile-server

# Optionally, remove the cloned directory
rm -rf /path/to/mcp-makefile-server
```

---

### Troubleshooting

#### Connection Failed

If Claude Code shows "Failed to reconnect to makefile-server":

1. Check the command name is `mcp-makefile-server` (not `mcp-makefile`)
2. Verify the Makefile path is correct
3. Check the server logs: Look at Claude Code's output panel
4. Test the server manually:
   ```bash
   uvx --from git+https://github.com/ccollicutt/mcp-makefile-server mcp-makefile-server preview ./Makefile
   ```

---

### Makefile Format

Your Makefile must use the standard self-documenting format with `##` comments:

```makefile
.PHONY: test build deploy

## Category: Testing
test: ## Run test suite with pytest (outputs results to stdout)
	pytest

lint: ## Check code style and formatting with ruff (reports issues found)
	ruff check .

## Category: Building
build: test ## Build Python package distribution (runs tests first, creates dist/ directory with wheel and sdist)
	python -m build

# Mark targets as internal (NOT exposed)
deploy-prod: ## @internal Deploy to production
	./deploy.sh --prod

# Regular targets ARE exposed
deploy-staging: test ## Deploy to staging environment (runs tests first, creates deploy.log)
	./deploy.sh --staging
```

**Format Rules:**

| Target Type | Result |
|-------------|--------|
| Targets with `##` descriptions | Exposed as MCP tools |
| Targets with `## @internal` or `## @skip` | NOT exposed |
| Targets without `##` | Ignored |

## Development

For development setup, testing, Python API usage, and contributing guidelines, see [DEVELOP.md](DEVELOP.md).

## Best Practices

### Efficient Output (Token Usage)

MCP responses consume tokens and bandwidth. Keep output concise:

**Good practices:**
```makefile
# Use variables for options, not separate targets
VERBOSE ?= 0
LOG_FILE ?= test-results.log

test: ## Run test suite with pytest (VERBOSE=1 for detailed output, LOG_FILE=path to save results, default: quiet mode with summary)
	@echo "Running tests..."
	@if [ "$(VERBOSE)" = "1" ]; then \
		pytest -v > $(LOG_FILE) 2>&1 && echo "✓ Tests complete (verbose). Full output in $(LOG_FILE)"; \
	else \
		pytest --quiet --tb=short > $(LOG_FILE) 2>&1 && echo "✓ Tests complete. Full output in $(LOG_FILE)" || \
		(echo "✗ Tests failed. Check $(LOG_FILE) for errors" && exit 1); \
	fi

build: ## Build Python package distribution (creates dist/ with wheel and sdist, full output saved to build.log)
	@echo "Building package..."
	@python -m build --quiet > build.log 2>&1 && echo "✓ Build complete. See build.log" || \
		(echo "✗ Build failed. Check build.log for errors" && exit 1)

lint: ## Check code style with ruff (reports only issues found, use FIX=1 to auto-fix problems)
	@if [ "$(FIX)" = "1" ]; then \
		ruff check --fix . && echo "✓ Linting complete (auto-fixed)"; \
	else \
		ruff check . --quiet && echo "✓ No linting issues" || echo "✗ Linting failed"; \
	fi
```

**Avoid:**
```makefile
# DON'T: Create many similar targets
test: ## Run tests
	pytest --quiet

test-verbose: ## Run tests verbosely
	pytest -vvv  # Separate target for same thing!

test-coverage: ## Run tests with coverage
	pytest --cov  # Another target!

# DON'T: Poor descriptions
build: ## Build  # What does it build? What are the options?
	python -m build

# DON'T: Print everything
deploy: ## Deploy
	npm install  # Prints hundreds of lines
	npm run build  # Prints more lines
	kubectl apply -f .  # Even more output
```

**Description Best Practices:**

The `##` description is sent to the MCP client/AI, so make it informative:

```makefile
# GOOD: Clear description with options explained
test: ## Run test suite (VERBOSE=1 for details, TEST=pattern to filter, COVERAGE=1 for coverage report)
	...

# GOOD: Explains what it does and what happens
deploy-staging: ## Deploy to staging environment (runs tests first, creates deploy.log with details)
	...

# BAD: Too vague
test: ## Test
	...

# BAD: Missing important info
deploy: ## Deploy
	...
```

**Tips:**

| Tip | Description | Example |
|-----|-------------|---------|
| **Write AI-friendly descriptions** | Use human-readable comments (`#`) for developers, but make `##` comments verbose natural language instructions for the AI. Include all variables, options, and capabilities. Keep targets multi-purpose to reduce total count. | `test: ## Run test suite with pytest. Options: VERBOSE=1 for detailed output, TEST=pattern to filter, COVERAGE=1 for coverage report, PARALLEL=1 for parallel execution. Creates test-results.log with full output.` |
| **Mark helper targets as internal** | Sub-functions and helpers the AI doesn't need should be marked `@internal` or `@skip` to keep the tool list focused | `_setup-env: ## @internal Initialize environment variables` |
| **Use variables, not multiple targets** | Pass options via variables instead of creating separate targets | `make test VERBOSE=1` instead of `make test-verbose` |
| **Write clear descriptions** | Explain what it does and what options are available | See Description Best Practices above |
| **Log verbose output to files** | Commands that produce lots of output should log to a file and return only a summary to avoid overloading tokens | `command > output.log 2>&1 && echo "✓ Done. See output.log"` |
| **Use `@` prefix** | Suppress command echo to reduce output noise | `@pytest` instead of `pytest` |
| **Use `--quiet`/`-q` flags** | Use quiet flags when available | `pytest --quiet`, `ruff check --quiet` |
| **Redirect to log files** | Save verbose output for later analysis | `pytest -v > test.log 2>&1` |
| **Print concise summaries** | Show brief success/failure instead of full output | `echo "✓ Tests passed (23 tests, 2.5s)"` |
| **Combine redirect + summary** | Redirect full output to file, then echo summary message | `pytest -v > test.log 2>&1 && echo "✓ Done. See test.log"` |
| **Exit codes matter** | Return non-zero on failure for AI to detect errors | Always preserve exit codes |

## Examples

See `tests/fixtures/` for example Makefiles:

| File | Description |
|------|-------------|
| `simple.mk` | Basic targets |
| `categorized.mk` | With category organization |
| `mixed.mk` | Shows internal targets and filtering |

## License

MIT License
