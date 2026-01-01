"""MCP server that exposes Makefile targets as tools."""

import asyncio
import logging
import sys
import time as time_module
import uuid
from pathlib import Path

from mcp.server import Server
from mcp.types import TextContent, Tool

from mcp_makefile.core.executor import MakeExecutor, SubprocessMakeExecutor
from mcp_makefile.core.models import MakefileMetadata
from mcp_makefile.core.parser import MakefileParser, RegexMakefileParser
from mcp_makefile.exceptions import TargetNotFoundError

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


class MakefileMCPServer:
    """MCP server that exposes Makefile targets as tools."""

    def __init__(
        self,
        makefile_path: Path,
        parser: MakefileParser | None = None,
        executor: MakeExecutor | None = None,
        allowed_targets: list[str] | None = None,
        max_output_chars: int = 0,
        write_to_file: bool = False,
        temp_dir: str = "/tmp",  # nosec B108 - Standard default, configurable by user
    ):
        self.makefile_path = makefile_path
        self.parser = parser or RegexMakefileParser()
        self.executor = executor or SubprocessMakeExecutor()
        self.allowed_targets = set(allowed_targets) if allowed_targets else None
        self.max_output_chars = max_output_chars
        self.write_to_file = write_to_file
        self.temp_dir = temp_dir
        self.output_dir: Path | None = None  # Will be created on first use
        self.metadata: MakefileMetadata | None = None
        self.server = Server("mcp-makefile-server")

        # Register handlers
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return await self._handle_list_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            return await self._handle_call_tool(name, arguments)

    async def initialize(self) -> None:
        """Initialize server by parsing Makefile."""
        logger.info(f"Parsing Makefile: {self.makefile_path}")
        self.metadata = self.parser.parse(self.makefile_path)
        logger.info(f"Found {len(self.metadata.targets)} targets")

        # Validate we have at least one exposed target
        exposed_targets = self.metadata.get_exposed_targets()
        if not exposed_targets:
            logger.warning(
                f"No exposed targets found in {self.makefile_path}. "
                "Add '## Description' comments to targets to expose them as MCP tools."
            )

        # Validate allowed_targets if specified
        if self.allowed_targets:
            logger.info(f"Allowed targets filter: {len(self.allowed_targets)} targets")

            # Check that all allowed targets exist in the Makefile
            missing_targets = self.allowed_targets - set(self.metadata.targets.keys())
            if missing_targets:
                missing_list = ", ".join(sorted(missing_targets))
                raise ValueError(
                    f"Allowed targets not found in Makefile: {missing_list}. "
                    f"Available targets: {', '.join(sorted(self.metadata.targets.keys()))}"
                )

            # Warn if allowed_targets includes internal targets
            internal_in_allowed = self.allowed_targets & set(self.metadata.get_internal_targets().keys())
            if internal_in_allowed:
                internal_list = ", ".join(sorted(internal_in_allowed))
                logger.warning(
                    f"Allowed targets includes internal targets (marked @internal/@skip): {internal_list}. "
                    "These will not be exposed."
                )

            # Check if the filter results in zero exposed targets
            filtered_exposed = {name for name, target in exposed_targets.items() if name in self.allowed_targets}
            if not filtered_exposed:
                logger.warning(
                    "No targets will be exposed after applying allowed_targets filter. "
                    f"Filter: {', '.join(sorted(self.allowed_targets))} "
                    f"Exposed: {', '.join(sorted(exposed_targets.keys()))}"
                )

    def _ensure_output_directory(self) -> Path:
        """Ensure output directory exists, creating it if needed."""
        if self.output_dir is None:
            # Create a randomized subdirectory within temp_dir
            random_suffix = uuid.uuid4().hex[:8]
            self.output_dir = Path(self.temp_dir) / f"mcp-makefile-{random_suffix}"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directory: {self.output_dir}")
        return self.output_dir

    async def _handle_list_tools(self) -> list[Tool]:
        """Return all Makefile targets as MCP tools."""
        if not self.metadata:
            return []

        tools = []
        for target in self.metadata.targets.values():
            # Skip internal targets (marked with @internal or @skip)
            if target.is_internal:
                logger.debug(f"Skipping internal target: {target.name}")
                continue

            # Skip if not in allowed list
            if self.allowed_targets and target.name not in self.allowed_targets:
                logger.debug(f"Skipping non-allowed target: {target.name}")
                continue

            # Build tool description
            description = target.description
            if target.category:
                description = f"[{target.category}] {description}"
            if target.dependencies:
                deps = ", ".join(target.dependencies)
                description += f" (depends on: {deps})"

            tool = Tool(
                name=target.name,
                description=description,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "variables": {
                            "type": "object",
                            "description": "Make variables to pass (e.g., {'DEBUG': '1'})",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 300, max recommended: 3600)",
                            "default": 300,
                            "minimum": 1,
                        },
                    },
                },
            )
            tools.append(tool)

        logger.info(f"Exposing {len(tools)} targets as MCP tools")
        return tools

    async def _handle_call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        """Execute a make target."""
        try:
            target_name = name

            # Check if target exists
            if not self.metadata or target_name not in self.metadata.targets:
                available = ", ".join(sorted(self.metadata.targets.keys())) if self.metadata else "none"
                raise TargetNotFoundError(f"Target '{target_name}' not found. Available targets: {available}")

            target = self.metadata.targets[target_name]

            # Security: Prevent execution of internal targets
            if target.is_internal:
                raise ValueError(
                    f"Cannot execute target '{target_name}': marked as internal (@internal or @skip). "
                    "This target is not available for MCP execution for security reasons."
                )

            # Check if allowed
            if self.allowed_targets and target_name not in self.allowed_targets:
                allowed = ", ".join(sorted(self.allowed_targets))
                raise ValueError(f"Target '{target_name}' is not in the allowlist. Allowed targets: {allowed}")
        except (TargetNotFoundError, ValueError) as e:
            # User-facing errors - return clean message
            logger.warning(f"Tool call rejected: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            # Unexpected errors - log details but return generic message
            logger.exception(f"Unexpected error in tool call: {e}")
            return [
                TextContent(type="text", text="An unexpected error occurred. Please check the server logs for details.")
            ]

        # Build environment from variables
        env = {}
        if variables := arguments.get("variables"):
            env.update(variables)

        # Get timeout (default to 300 seconds)
        timeout = arguments.get("timeout", 300)

        logger.info(f"Executing target: {target_name} (timeout: {timeout}s)")

        # Generate progress token for this execution
        progress_token = str(uuid.uuid4())

        # Send "running" notification
        try:
            await self.server.request_context.session.send_progress_notification(
                progress_token=progress_token,
                progress=0,
                total=1,
            )
        except Exception:
            # If progress notifications fail, just log and continue
            logger.debug("Could not send progress notification (client may not support it)")

        # Execute
        try:
            result = await self.executor.execute(
                target=target_name,
                makefile=self.makefile_path,
                env=env,
                timeout=timeout,
            )

            # Send "completed" notification
            try:
                await self.server.request_context.session.send_progress_notification(
                    progress_token=progress_token,
                    progress=1,
                    total=1,
                )
            except Exception:
                logger.debug("Could not send completion notification")

        except asyncio.CancelledError:
            # Operation was cancelled by client
            logger.info(f"Target '{target_name}' was cancelled")
            try:
                await self.server.request_context.session.send_progress_notification(
                    progress_token=progress_token,
                    progress=1,
                    total=1,
                )
            except Exception:
                logger.debug("Could not send cancellation notification")

            return [TextContent(type="text", text=f"Target '{target_name}' was cancelled before completion.")]

        except FileNotFoundError as e:
            # File not found - likely Makefile or working directory issue
            logger.error(f"File not found during execution: {e}")
            try:
                await self.server.request_context.session.send_progress_notification(
                    progress_token=progress_token,
                    progress=1,
                    total=1,
                )
            except Exception:  # nosec B110
                pass  # Intentionally ignore progress notification failures

            return [
                TextContent(type="text", text=f"Error: {str(e)}. Check that the Makefile exists and is accessible.")
            ]

        except PermissionError as e:
            # Permission denied
            logger.error(f"Permission denied during execution: {e}")
            try:
                await self.server.request_context.session.send_progress_notification(
                    progress_token=progress_token,
                    progress=1,
                    total=1,
                )
            except Exception:  # nosec B110
                pass  # Intentionally ignore progress notification failures

            return [
                TextContent(
                    type="text",
                    text="Error: Permission denied. Check file permissions for the Makefile and working directory.",
                )
            ]

        except Exception as e:
            # Send "failed" notification
            logger.exception(f"Execution failed for target '{target_name}': {e}")
            try:
                await self.server.request_context.session.send_progress_notification(
                    progress_token=progress_token,
                    progress=1,
                    total=1,
                )
            except Exception:
                logger.debug("Could not send failure notification")

            return [TextContent(type="text", text=f"Execution failed: {str(e)}. Check server logs for details.")]

        # Format response
        output = f"Target: {target_name}\n"
        output += f"Exit Code: {result.exit_code}\n"
        output += f"Duration: {result.duration:.2f}s\n\n"

        # Write to file if enabled
        if self.write_to_file:
            # Ensure output directory exists
            output_dir = self._ensure_output_directory()

            # Create filename with timestamp
            timestamp = int(time_module.time())
            output_file = output_dir / f"{target_name}-{timestamp}.log"

            # Write output to file
            with open(output_file, "w") as f:
                f.write(f"Target: {target_name}\n")
                f.write(f"Exit Code: {result.exit_code}\n")
                f.write(f"Duration: {result.duration:.2f}s\n")
                f.write(f"Timestamp: {timestamp}\n\n")
                if result.stdout:
                    f.write("STDOUT:\n")
                    f.write(result.stdout)
                    f.write("\n\n")
                if result.stderr:
                    f.write("STDERR:\n")
                    f.write(result.stderr)
                    f.write("\n")

            output += f"Full output written to: {output_file}\n\n"
            logger.info(f"Wrote full output to {output_file}")

        # Truncate output if needed to avoid token overload
        stdout_text = result.stdout or ""
        stderr_text = result.stderr or ""

        total_output_len = len(stdout_text) + len(stderr_text)
        if self.max_output_chars > 0 and total_output_len > self.max_output_chars:
            # Calculate how much to show from each stream
            truncate_at = self.max_output_chars // 2

            if stdout_text:
                if len(stdout_text) > truncate_at:
                    stdout_text = (
                        stdout_text[:truncate_at]
                        + f"\n\n... (truncated, {len(result.stdout) - truncate_at} chars omitted)"
                    )
                output += "STDOUT:\n" + stdout_text + "\n"

            if stderr_text:
                if len(stderr_text) > truncate_at:
                    stderr_text = (
                        stderr_text[:truncate_at]
                        + f"\n\n... (truncated, {len(result.stderr) - truncate_at} chars omitted)"
                    )
                output += "STDERR:\n" + stderr_text + "\n"

            output += f"\nNote: Output exceeded {self.max_output_chars} characters and was truncated. "
            output += "Configure targets to log verbose output to files and return summaries instead.\n"
        else:
            if stdout_text:
                output += "STDOUT:\n" + stdout_text + "\n"
            if stderr_text:
                output += "STDERR:\n" + stderr_text + "\n"

        return [TextContent(type="text", text=output)]

    async def run(self) -> None:
        """Run the MCP server with stdio transport."""
        from mcp.server.stdio import stdio_server

        await self.initialize()

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
