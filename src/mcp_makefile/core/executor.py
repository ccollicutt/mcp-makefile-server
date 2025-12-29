"""Command execution for make targets."""

import asyncio
import logging
import os
import re
import signal
import time
from abc import ABC, abstractmethod
from pathlib import Path

from mcp_makefile.core.models import ExecutionResult

logger = logging.getLogger(__name__)


class MakeExecutor(ABC):
    """Abstract base class for make command execution."""

    @abstractmethod
    async def execute(
        self,
        target: str,
        makefile: Path,
        cwd: Path | None = None,
        timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute make target and return result."""
        pass

    def validate_target_name(self, target: str) -> None:
        """Validate target name to prevent shell injection."""
        if not target or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", target):
            raise ValueError(f"Invalid target name: {target}")


class SubprocessMakeExecutor(MakeExecutor):
    """Execute make targets using subprocess."""

    async def execute(
        self,
        target: str,
        makefile: Path,
        cwd: Path | None = None,
        timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute make target."""
        # Validate inputs
        self.validate_target_name(target)

        # Validate Makefile exists
        if not makefile.exists():
            raise FileNotFoundError(f"Makefile not found: {makefile}")

        if not makefile.is_file():
            raise ValueError(f"Makefile path is not a file: {makefile}")

        # Validate timeout
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got: {timeout}")

        if timeout > 3600:  # 1 hour max
            logger.warning(f"Very long timeout specified: {timeout}s (max recommended: 3600s)")

        # Determine and validate working directory
        work_dir = cwd or makefile.parent

        if not work_dir.exists():
            raise FileNotFoundError(f"Working directory does not exist: {work_dir}")

        if not work_dir.is_dir():
            raise ValueError(f"Working directory is not a directory: {work_dir}")

        # Build command
        cmd = ["make", "-f", str(makefile), target]

        # Merge environment
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)

        logger.info(f"Executing: {' '.join(cmd)} in {work_dir}")

        # Execute
        start_time = time.time()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=proc_env,
                start_new_session=True,  # Create new process group for proper cleanup
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            duration = time.time() - start_time
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            logger.info(f"Target '{target}' completed in {duration:.2f}s with exit code {process.returncode}")

            return ExecutionResult(
                success=process.returncode == 0,
                exit_code=process.returncode or 0,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                target=target,
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.exception(f"Target '{target}' timed out after {timeout}s")
            try:
                # Kill entire process group to cleanup children
                if process.pid:
                    os.killpg(process.pid, signal.SIGKILL)  # Kill entire process tree
                # Wait for process with timeout to avoid hanging
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Process did not terminate within 5s after SIGKILL (may have orphaned children)")
            except ProcessLookupError:
                # Process already terminated
                pass
            except Exception:
                logger.exception("Failed to kill timed out process")

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                duration=duration,
                target=target,
            )
        except asyncio.CancelledError:
            duration = time.time() - start_time
            logger.info(f"Target '{target}' was cancelled, killing process")
            try:
                # Kill entire process group to cleanup children
                if process.pid:
                    os.killpg(process.pid, signal.SIGKILL)  # Kill entire process tree
                # Wait for process with timeout to avoid hanging
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Process did not terminate within 5s after SIGKILL (may have orphaned children)")
            except ProcessLookupError:
                # Process already terminated
                pass
            except Exception:
                logger.exception("Failed to kill cancelled process")
            raise  # Re-raise to propagate cancellation
        except Exception:
            duration = time.time() - start_time
            logger.exception(f"Failed to execute target '{target}'")
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Unexpected error during execution",
                duration=duration,
                target=target,
            )


class DryRunMakeExecutor(MakeExecutor):
    """Mock executor for testing - doesn't actually run commands."""

    def __init__(self, mock_success: bool = True, mock_output: str = "") -> None:
        self.mock_success = mock_success
        self.mock_output = mock_output
        self.executed_targets: list[str] = []

    async def execute(
        self,
        target: str,
        makefile: Path,
        cwd: Path | None = None,
        timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Return mock result without executing."""
        self.validate_target_name(target)
        self.executed_targets.append(target)

        logger.debug(f"DryRun: Would execute target '{target}'")

        return ExecutionResult(
            success=self.mock_success,
            exit_code=0 if self.mock_success else 1,
            stdout=self.mock_output,
            stderr="" if self.mock_success else "Mock error",
            duration=0.1,
            target=target,
        )
