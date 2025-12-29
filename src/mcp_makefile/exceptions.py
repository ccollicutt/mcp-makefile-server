"""Custom exceptions for MCP Makefile server."""


class MCPMakefileError(Exception):
    """Base exception for all MCP Makefile errors."""

    pass


class MakefileNotFoundError(MCPMakefileError):
    """Makefile not found at specified path."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Makefile not found: {path}")


class MakefileParseError(MCPMakefileError):
    """Error parsing Makefile."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        super().__init__(f"Failed to parse {path}: {message}")


class TargetNotFoundError(MCPMakefileError):
    """Target not found in Makefile."""

    def __init__(self, target: str) -> None:
        self.target = target
        super().__init__(f"Target not found: {target}")


class ExecutionError(MCPMakefileError):
    """Error executing make target."""

    def __init__(self, target: str, exit_code: int, stderr: str) -> None:
        self.target = target
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"Target '{target}' failed with exit code {exit_code}")
