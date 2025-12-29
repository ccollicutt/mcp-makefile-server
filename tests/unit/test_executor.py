"""Tests for command executor."""

from pathlib import Path

import pytest

from mcp_makefile.core.executor import DryRunMakeExecutor, SubprocessMakeExecutor

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestMakeExecutorValidation:
    """Tests for target name validation."""

    def test_valid_target_names(self) -> None:
        """Valid target names pass validation."""
        executor = DryRunMakeExecutor()

        # Should not raise
        executor.validate_target_name("test")
        executor.validate_target_name("build")
        executor.validate_target_name("test-all")
        executor.validate_target_name("test_unit")
        executor.validate_target_name("_private")

    def test_invalid_target_names(self) -> None:
        """Invalid target names raise ValueError."""
        executor = DryRunMakeExecutor()

        with pytest.raises(ValueError, match="Invalid target name"):
            executor.validate_target_name("")

        with pytest.raises(ValueError, match="Invalid target name"):
            executor.validate_target_name("test;rm -rf /")

        with pytest.raises(ValueError, match="Invalid target name"):
            executor.validate_target_name("test && echo hack")

        with pytest.raises(ValueError, match="Invalid target name"):
            executor.validate_target_name("123invalid")


class TestDryRunMakeExecutor:
    """Tests for DryRunMakeExecutor."""

    @pytest.mark.anyio
    async def test_execute_success(self) -> None:
        """Dry run executor returns mock success."""
        executor = DryRunMakeExecutor(mock_success=True, mock_output="Mock output")
        makefile = Path("Makefile")

        result = await executor.execute("test", makefile)

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Mock output"
        assert result.stderr == ""
        assert result.target == "test"

    @pytest.mark.anyio
    async def test_execute_failure(self) -> None:
        """Dry run executor returns mock failure."""
        executor = DryRunMakeExecutor(mock_success=False)
        makefile = Path("Makefile")

        result = await executor.execute("test", makefile)

        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "Mock error"

    @pytest.mark.anyio
    async def test_tracks_executed_targets(self) -> None:
        """Dry run executor tracks executed targets."""
        executor = DryRunMakeExecutor()
        makefile = Path("Makefile")

        await executor.execute("test", makefile)
        await executor.execute("build", makefile)
        await executor.execute("deploy", makefile)

        assert executor.executed_targets == ["test", "build", "deploy"]

    @pytest.mark.anyio
    async def test_validates_target_name(self) -> None:
        """Dry run executor validates target names."""
        executor = DryRunMakeExecutor()
        makefile = Path("Makefile")

        with pytest.raises(ValueError, match="Invalid target name"):
            await executor.execute("invalid;target", makefile)


class TestSubprocessMakeExecutor:
    """Tests for SubprocessMakeExecutor."""

    @pytest.mark.anyio
    async def test_execute_success(self) -> None:
        """Execute successful target."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        result = await executor.execute("success", makefile)

        assert result.success is True
        assert result.exit_code == 0
        assert "Success!" in result.stdout
        assert result.target == "success"
        assert result.duration > 0

    @pytest.mark.anyio
    async def test_execute_failure(self) -> None:
        """Execute failing target."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        result = await executor.execute("fail", makefile)

        assert result.success is False
        assert result.exit_code == 2  # make returns 2 when a recipe fails
        assert "Failing..." in result.stdout
        assert result.target == "fail"

    @pytest.mark.anyio
    async def test_execute_with_timeout(self) -> None:
        """Timeout on long-running target."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        result = await executor.execute("slow", makefile, timeout=1)

        assert result.success is False
        assert result.exit_code == -1
        assert "timed out" in result.stderr.lower()

    @pytest.mark.anyio
    async def test_execute_with_environment_variables(self) -> None:
        """Environment variables passed to make."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        result = await executor.execute("echo-var", makefile, env={"VAR": "test-value"})

        assert result.success is True
        assert "VAR=test-value" in result.stdout

    @pytest.mark.anyio
    async def test_execute_with_working_directory(self) -> None:
        """Working directory used correctly."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"
        cwd = FIXTURES_DIR

        result = await executor.execute("success", makefile, cwd=cwd)

        assert result.success is True

    @pytest.mark.anyio
    async def test_validates_target_name(self) -> None:
        """Subprocess executor validates target names."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        with pytest.raises(ValueError, match="Invalid target name"):
            await executor.execute("test; echo hack", makefile)

    @pytest.mark.anyio
    async def test_capture_stdout_and_stderr(self) -> None:
        """Capture stdout and stderr separately."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        result = await executor.execute("success", makefile)

        assert result.stdout != ""
        # stderr might be empty for successful commands
        assert isinstance(result.stderr, str)

    @pytest.mark.anyio
    async def test_execute_with_nonexistent_makefile(self) -> None:
        """Execute fails when Makefile doesn't exist."""
        executor = SubprocessMakeExecutor()
        makefile = Path("/nonexistent/Makefile")

        with pytest.raises(FileNotFoundError, match="Makefile not found"):
            await executor.execute("test", makefile)

    @pytest.mark.anyio
    async def test_execute_with_directory_as_makefile(self, tmp_path: Path) -> None:
        """Execute fails when Makefile path is a directory."""
        executor = SubprocessMakeExecutor()
        directory = tmp_path / "some_dir"
        directory.mkdir()

        with pytest.raises(ValueError, match="not a file"):
            await executor.execute("test", directory)

    @pytest.mark.anyio
    async def test_execute_with_negative_timeout(self) -> None:
        """Execute fails with negative timeout."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        with pytest.raises(ValueError, match="Timeout must be positive"):
            await executor.execute("success", makefile, timeout=-1)

    @pytest.mark.anyio
    async def test_execute_with_zero_timeout(self) -> None:
        """Execute fails with zero timeout."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        with pytest.raises(ValueError, match="Timeout must be positive"):
            await executor.execute("success", makefile, timeout=0)

    @pytest.mark.anyio
    async def test_execute_with_nonexistent_working_directory(self) -> None:
        """Execute fails when working directory doesn't exist."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"
        cwd = Path("/nonexistent/directory")

        with pytest.raises(FileNotFoundError, match="Working directory does not exist"):
            await executor.execute("success", makefile, cwd=cwd)

    @pytest.mark.anyio
    async def test_execute_with_file_as_working_directory(self, tmp_path: Path) -> None:
        """Execute fails when working directory is a file."""
        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"
        cwd = tmp_path / "file.txt"
        cwd.write_text("not a directory")

        with pytest.raises(ValueError, match="not a directory"):
            await executor.execute("success", makefile, cwd=cwd)

    @pytest.mark.anyio
    async def test_execute_handles_cancellation(self) -> None:
        """Execute properly cleans up when cancelled."""
        import asyncio

        executor = SubprocessMakeExecutor()
        makefile = FIXTURES_DIR / "exec-test.mk"

        # Start a long-running task
        task = asyncio.create_task(executor.execute("slow", makefile, timeout=30))

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Cancel the task
        task.cancel()

        # Should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task
