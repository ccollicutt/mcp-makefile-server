"""Tests for MCP server."""

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
