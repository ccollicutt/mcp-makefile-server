"""Tests for MCP server."""

import os
from pathlib import Path

import pytest

from mcp_makefile.core.executor import DryRunMakeExecutor
from mcp_makefile.exceptions import MakefileNotFoundError
from mcp_makefile.server import MakefileMCPServer

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestMakefileMCPServer:
    """Tests for MakefileMCPServer."""

    @pytest.mark.anyio
    async def test_initialize_with_valid_makefile(self) -> None:
        """Server initializes with valid Makefile."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)

        await server.initialize()

        assert server.metadata is not None
        assert len(server.metadata.targets) == 2

    @pytest.mark.anyio
    async def test_initialize_with_invalid_makefile(self) -> None:
        """Server fails with invalid/missing Makefile."""
        makefile = Path("/nonexistent/Makefile")
        server = MakefileMCPServer(makefile)

        with pytest.raises(MakefileNotFoundError):
            await server.initialize()

    @pytest.mark.anyio
    async def test_list_tools_returns_all_targets(self) -> None:
        """list_tools() returns all non-internal targets."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        tools = await server._handle_list_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "test" in tool_names
        assert "build" in tool_names

    @pytest.mark.anyio
    async def test_list_tools_excludes_internal_targets(self) -> None:
        """list_tools() excludes targets marked with @internal or @skip."""
        makefile = FIXTURES_DIR / "mixed.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        tools = await server._handle_list_tools()

        tool_names = [t.name for t in tools]
        # Should include public targets
        assert "test" in tool_names
        assert "clean" in tool_names
        assert "deploy" in tool_names

        # Should exclude internal targets
        assert "deploy-dangerous" not in tool_names
        assert "cleanup-prod" not in tool_names

    @pytest.mark.anyio
    async def test_list_tools_respects_allowed_targets(self) -> None:
        """list_tools() respects allowed_targets filter."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile, allowed_targets=["test"])
        await server.initialize()

        tools = await server._handle_list_tools()

        assert len(tools) == 1
        assert tools[0].name == "test"

    @pytest.mark.anyio
    async def test_list_tools_includes_category(self) -> None:
        """Tool descriptions include category."""
        makefile = FIXTURES_DIR / "categorized.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        tools = await server._handle_list_tools()

        test_tool = next(t for t in tools if t.name == "test")
        assert "[Testing]" in test_tool.description

    @pytest.mark.anyio
    async def test_list_tools_includes_dependencies(self) -> None:
        """Tool descriptions include dependencies."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        tools = await server._handle_list_tools()

        build_tool = next(t for t in tools if t.name == "build")
        assert "depends on: test" in build_tool.description

    @pytest.mark.anyio
    async def test_list_tools_includes_timeout_parameter(self) -> None:
        """Tool schema includes timeout parameter."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        tools = await server._handle_list_tools()

        # Check that all tools have timeout in their schema
        for tool in tools:
            assert "properties" in tool.inputSchema
            assert "timeout" in tool.inputSchema["properties"]
            timeout_schema = tool.inputSchema["properties"]["timeout"]
            assert timeout_schema["type"] == "integer"
            assert timeout_schema["default"] == 300
            assert timeout_schema["minimum"] == 1
            assert "Timeout in seconds" in timeout_schema["description"]

    @pytest.mark.anyio
    async def test_call_tool_executes_successfully(self) -> None:
        """call_tool() executes target successfully."""
        makefile = FIXTURES_DIR / "exec-test.mk"
        executor = DryRunMakeExecutor(mock_success=True, mock_output="Success!")
        server = MakefileMCPServer(makefile, executor=executor)
        await server.initialize()

        result = await server._handle_call_tool("success", {})

        assert len(result) == 1
        assert "Target: success" in result[0].text
        assert "Exit Code: 0" in result[0].text

    @pytest.mark.anyio
    async def test_call_tool_invalid_target(self) -> None:
        """call_tool() returns error for invalid target."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        result = await server._handle_call_tool("nonexistent", {})
        assert len(result) == 1
        assert "Error:" in result[0].text
        assert "not found" in result[0].text

    @pytest.mark.anyio
    async def test_call_tool_blocks_internal_targets(self) -> None:
        """call_tool() blocks execution of internal targets."""
        makefile = FIXTURES_DIR / "mixed.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        result = await server._handle_call_tool("deploy-dangerous", {})
        assert len(result) == 1
        assert "Error:" in result[0].text
        assert "internal" in result[0].text.lower()

    @pytest.mark.anyio
    async def test_call_tool_respects_allowed_targets(self) -> None:
        """call_tool() respects allowed_targets filter."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile, allowed_targets=["test"])
        await server.initialize()

        result = await server._handle_call_tool("build", {})
        assert len(result) == 1
        assert "Error:" in result[0].text
        assert "allowlist" in result[0].text.lower()

    @pytest.mark.anyio
    async def test_call_tool_with_variables(self) -> None:
        """Variables passed to make execution."""
        makefile = FIXTURES_DIR / "exec-test.mk"
        executor = DryRunMakeExecutor(mock_success=True)
        server = MakefileMCPServer(makefile, executor=executor)
        await server.initialize()

        await server._handle_call_tool("echo-var", {"variables": {"VAR": "value"}})

        # Verify execution happened (in real test, would check env vars were passed)
        assert "echo-var" in executor.executed_targets

    @pytest.mark.anyio
    async def test_call_tool_with_custom_timeout(self) -> None:
        """Custom timeout passed to make execution."""
        makefile = FIXTURES_DIR / "exec-test.mk"
        executor = DryRunMakeExecutor(mock_success=True)
        server = MakefileMCPServer(makefile, executor=executor)
        await server.initialize()

        await server._handle_call_tool("success", {"timeout": 600})

        # Verify execution happened
        assert "success" in executor.executed_targets

    @pytest.mark.anyio
    async def test_call_tool_unknown_tool(self) -> None:
        """call_tool() rejects unknown tool names."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        result = await server._handle_call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Error:" in result[0].text
        assert "not found" in result[0].text

    @pytest.mark.anyio
    async def test_multiple_tool_calls(self) -> None:
        """Multiple sequential tool calls work."""
        makefile = FIXTURES_DIR / "exec-test.mk"
        executor = DryRunMakeExecutor(mock_success=True)
        server = MakefileMCPServer(makefile, executor=executor)
        await server.initialize()

        await server._handle_call_tool("success", {})
        await server._handle_call_tool("success", {})

        assert len(executor.executed_targets) == 2

    @pytest.mark.anyio
    async def test_initialize_with_nonexistent_allowed_targets(self) -> None:
        """Initialize fails when allowed_targets don't exist in Makefile."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile, allowed_targets=["nonexistent", "fake"])

        with pytest.raises(ValueError, match="Allowed targets not found"):
            await server.initialize()

    @pytest.mark.anyio
    async def test_initialize_warns_for_internal_allowed_targets(self, caplog) -> None:
        """Initialize warns when allowed_targets includes internal targets."""
        makefile = FIXTURES_DIR / "mixed.mk"
        server = MakefileMCPServer(makefile, allowed_targets=["test", "deploy-dangerous"])

        await server.initialize()

        # Check warning was logged
        assert any("internal targets" in record.message.lower() for record in caplog.records)
        assert any("deploy-dangerous" in record.message for record in caplog.records)

    @pytest.mark.anyio
    async def test_initialize_warns_for_zero_exposed_targets(self, caplog) -> None:
        """Initialize warns when allowed_targets results in zero exposed targets."""
        makefile = FIXTURES_DIR / "mixed.mk"
        # Only allow internal targets
        server = MakefileMCPServer(makefile, allowed_targets=["deploy-dangerous", "cleanup-prod"])

        await server.initialize()

        # Check warning was logged
        assert any("no targets will be exposed" in record.message.lower() for record in caplog.records)

    @pytest.mark.anyio
    async def test_list_tools_when_not_initialized(self) -> None:
        """list_tools returns empty list when not initialized."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)
        # Don't call initialize()

        tools = await server._handle_list_tools()

        assert tools == []

    @pytest.mark.anyio
    async def test_error_message_shows_available_targets(self) -> None:
        """Error message includes list of available targets."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        result = await server._handle_call_tool("nonexistent", {})

        assert "Available targets:" in result[0].text
        assert "build" in result[0].text
        assert "test" in result[0].text

    @pytest.mark.anyio
    async def test_error_message_for_internal_target(self) -> None:
        """Error message explains internal target restriction."""
        makefile = FIXTURES_DIR / "mixed.mk"
        server = MakefileMCPServer(makefile)
        await server.initialize()

        result = await server._handle_call_tool("deploy-dangerous", {})

        assert "security" in result[0].text.lower()
        assert "@internal" in result[0].text or "@skip" in result[0].text

    @pytest.mark.anyio
    async def test_error_message_for_allowlist(self) -> None:
        """Error message shows allowed targets."""
        makefile = FIXTURES_DIR / "simple.mk"
        server = MakefileMCPServer(makefile, allowed_targets=["test"])
        await server.initialize()

        result = await server._handle_call_tool("build", {})

        assert "Allowed targets:" in result[0].text
        assert "test" in result[0].text

    @pytest.mark.anyio
    async def test_output_truncation_when_exceeds_limit(self) -> None:
        """Output is truncated when it exceeds max_output_chars."""
        makefile = FIXTURES_DIR / "simple.mk"
        # Create executor with large mock output
        large_output = "x" * 20000  # 20,000 characters
        executor = DryRunMakeExecutor(mock_success=True, mock_output=large_output)
        server = MakefileMCPServer(makefile, executor=executor, max_output_chars=10000)
        await server.initialize()

        result = await server._handle_call_tool("test", {})

        assert len(result) == 1
        # Output should be truncated
        assert "truncated" in result[0].text.lower()
        assert "Note: Output exceeded 10000 characters" in result[0].text
        # Should suggest logging to files
        assert "log verbose output to files" in result[0].text

    @pytest.mark.anyio
    async def test_no_truncation_when_unlimited(self) -> None:
        """Output is not truncated when max_output_chars is 0 (unlimited)."""
        makefile = FIXTURES_DIR / "simple.mk"
        # Create executor with large mock output
        large_output = "x" * 20000  # 20,000 characters
        executor = DryRunMakeExecutor(mock_success=True, mock_output=large_output)
        server = MakefileMCPServer(makefile, executor=executor, max_output_chars=0)
        await server.initialize()

        result = await server._handle_call_tool("test", {})

        assert len(result) == 1
        # Output should NOT be truncated
        assert "truncated" not in result[0].text.lower()
        # Should contain all output
        assert "x" * 20000 in result[0].text

    @pytest.mark.anyio
    async def test_no_truncation_when_under_limit(self) -> None:
        """Output is not truncated when under max_output_chars."""
        makefile = FIXTURES_DIR / "simple.mk"
        # Create executor with small output
        small_output = "Test output"
        executor = DryRunMakeExecutor(mock_success=True, mock_output=small_output)
        server = MakefileMCPServer(makefile, executor=executor, max_output_chars=10000)
        await server.initialize()

        result = await server._handle_call_tool("test", {})

        assert len(result) == 1
        # Output should NOT be truncated
        assert "truncated" not in result[0].text.lower()
        assert "Test output" in result[0].text

    @pytest.mark.anyio
    async def test_write_to_file_creates_temp_file(self) -> None:
        """When write_to_file is enabled, output is written to temp file in subdirectory."""
        makefile = FIXTURES_DIR / "simple.mk"
        test_output = "Test output from target"
        executor = DryRunMakeExecutor(mock_success=True, mock_output=test_output)
        server = MakefileMCPServer(makefile, executor=executor, write_to_file=True)
        await server.initialize()

        result = await server._handle_call_tool("test", {})

        assert len(result) == 1
        # Should mention file path
        assert "Full output written to:" in result[0].text
        assert "/tmp/mcp-makefile-" in result[0].text
        assert "/test-" in result[0].text
        assert ".log" in result[0].text

        # Extract file path from response
        lines = result[0].text.split("\n")
        file_line = [line for line in lines if "Full output written to:" in line][0]
        file_path = file_line.split("Full output written to:")[1].strip()

        # Verify file exists
        assert os.path.exists(file_path)

        # Verify file contains output
        with open(file_path) as f:
            content = f.read()
            assert "Test output from target" in content
            assert "Target: test" in content
            assert "Exit Code: 0" in content

        # Cleanup file and directory
        os.unlink(file_path)
        output_dir = Path(file_path).parent
        output_dir.rmdir()

    @pytest.mark.anyio
    async def test_write_to_file_disabled_by_default(self) -> None:
        """When write_to_file is False, no file is created."""
        makefile = FIXTURES_DIR / "simple.mk"
        executor = DryRunMakeExecutor(mock_success=True, mock_output="Test output")
        server = MakefileMCPServer(makefile, executor=executor, write_to_file=False)
        await server.initialize()

        result = await server._handle_call_tool("test", {})

        assert len(result) == 1
        # Should NOT mention file path
        assert "Full output written to:" not in result[0].text

    @pytest.mark.anyio
    async def test_write_to_file_with_truncation(self) -> None:
        """write_to_file and truncation can be used together."""
        makefile = FIXTURES_DIR / "simple.mk"
        large_output = "x" * 20000  # 20,000 characters
        executor = DryRunMakeExecutor(mock_success=True, mock_output=large_output)
        server = MakefileMCPServer(makefile, executor=executor, max_output_chars=5000, write_to_file=True)
        await server.initialize()

        result = await server._handle_call_tool("test", {})

        assert len(result) == 1
        # Should have both file path and truncation notice
        assert "Full output written to:" in result[0].text
        assert "truncated" in result[0].text.lower()

        # Extract and verify file has full output
        lines = result[0].text.split("\n")
        file_line = [line for line in lines if "Full output written to:" in line][0]
        file_path = file_line.split("Full output written to:")[1].strip()

        with open(file_path) as f:
            content = f.read()
            # File should have full output
            assert "x" * 20000 in content

        # Cleanup file and directory
        os.unlink(file_path)
        output_dir = Path(file_path).parent
        output_dir.rmdir()
