"""MCP Makefile Server - Expose Makefile targets as MCP tools."""

from mcp_makefile.core.executor import DryRunMakeExecutor, MakeExecutor, SubprocessMakeExecutor
from mcp_makefile.core.models import ExecutionResult, MakefileMetadata, MakeTarget
from mcp_makefile.core.parser import MakefileParser, RegexMakefileParser
from mcp_makefile.exceptions import (
    ExecutionError,
    MakefileNotFoundError,
    MakefileParseError,
    MCPMakefileError,
    TargetNotFoundError,
)
from mcp_makefile.server import MakefileMCPServer, setup_logging

__version__ = "0.1.0"

__all__ = [
    "MakeTarget",
    "MakefileMetadata",
    "ExecutionResult",
    "MakefileParser",
    "RegexMakefileParser",
    "MakeExecutor",
    "SubprocessMakeExecutor",
    "DryRunMakeExecutor",
    "MakefileMCPServer",
    "setup_logging",
    "MCPMakefileError",
    "MakefileNotFoundError",
    "MakefileParseError",
    "TargetNotFoundError",
    "ExecutionError",
]
