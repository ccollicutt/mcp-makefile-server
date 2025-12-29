"""Tests for custom exceptions."""

from mcp_makefile.exceptions import (
    ExecutionError,
    MakefileNotFoundError,
    MakefileParseError,
    MCPMakefileError,
    TargetNotFoundError,
)


class TestExceptions:
    """Tests for exception classes."""

    def test_base_exception(self) -> None:
        """Base exception can be raised."""
        exc = MCPMakefileError("Test error")

        assert str(exc) == "Test error"
        assert isinstance(exc, Exception)

    def test_makefile_not_found_error(self) -> None:
        """MakefileNotFoundError formats message correctly."""
        exc = MakefileNotFoundError("/path/to/Makefile")

        assert exc.path == "/path/to/Makefile"
        assert "Makefile not found: /path/to/Makefile" in str(exc)
        assert isinstance(exc, MCPMakefileError)

    def test_makefile_parse_error(self) -> None:
        """MakefileParseError formats message correctly."""
        exc = MakefileParseError("/path/to/Makefile", "Invalid syntax")

        assert exc.path == "/path/to/Makefile"
        assert "Failed to parse /path/to/Makefile: Invalid syntax" in str(exc)
        assert isinstance(exc, MCPMakefileError)

    def test_target_not_found_error(self) -> None:
        """TargetNotFoundError formats message correctly."""
        exc = TargetNotFoundError("deploy")

        assert exc.target == "deploy"
        assert "Target not found: deploy" in str(exc)
        assert isinstance(exc, MCPMakefileError)

    def test_execution_error(self) -> None:
        """ExecutionError formats message correctly."""
        exc = ExecutionError("build", 1, "make: *** [build] Error 1")

        assert exc.target == "build"
        assert exc.exit_code == 1
        assert exc.stderr == "make: *** [build] Error 1"
        assert "Target 'build' failed with exit code 1" in str(exc)
        assert isinstance(exc, MCPMakefileError)
