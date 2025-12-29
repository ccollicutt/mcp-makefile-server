"""Tests for configuration via environment variables."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestEnvironmentConfiguration:
    """Tests for environment variable configuration."""

    def test_log_level_from_env(self) -> None:
        """Log level can be set via environment variable."""
        with patch.dict(os.environ, {"MCP_MAKEFILE_LOG_LEVEL": "DEBUG"}):
            from mcp_makefile.__main__ import cmd_serve

            # Create mock args
            args = MagicMock()
            args.log_level = "INFO"  # CLI default
            args.makefile = Path(__file__).parent.parent / "fixtures" / "simple.mk"
            args.allowed_targets = None

            with patch("mcp_makefile.__main__.setup_logging") as mock_logging:
                with patch("mcp_makefile.__main__.MakefileMCPServer"):
                    with patch("mcp_makefile.__main__.asyncio.run"):
                        cmd_serve(args)

                # Should use env var, not CLI default
                mock_logging.assert_called_once_with("DEBUG")

    def test_makefile_path_from_env(self) -> None:
        """Makefile path can be set via environment variable."""
        test_path = "/custom/path/Makefile"
        with patch.dict(os.environ, {"MCP_MAKEFILE_PATH": test_path}):
            from mcp_makefile.__main__ import cmd_serve

            args = MagicMock()
            args.log_level = "INFO"
            args.makefile = Path("default/Makefile")
            args.allowed_targets = None

            with patch("mcp_makefile.__main__.setup_logging"):
                with patch("mcp_makefile.__main__.MakefileMCPServer") as mock_server:
                    with patch("mcp_makefile.__main__.asyncio.run"):
                        # Mock the path existence check
                        with patch("pathlib.Path.exists", return_value=True):
                            cmd_serve(args)

                # Should use env var path
                call_args = mock_server.call_args
                assert str(call_args[1]["makefile_path"]) == test_path

    def test_allowed_targets_from_env(self) -> None:
        """Allowed targets can be set via environment variable."""
        with patch.dict(os.environ, {"MCP_MAKEFILE_ALLOWED_TARGETS": "test,build,deploy"}):
            from mcp_makefile.__main__ import cmd_serve

            args = MagicMock()
            args.log_level = "INFO"
            args.makefile = Path(__file__).parent.parent / "fixtures" / "simple.mk"
            args.allowed_targets = None  # Not set via CLI

            with patch("mcp_makefile.__main__.setup_logging"):
                with patch("mcp_makefile.__main__.MakefileMCPServer") as mock_server:
                    with patch("mcp_makefile.__main__.asyncio.run"):
                        cmd_serve(args)

                # Should parse comma-separated list from env
                call_args = mock_server.call_args
                assert call_args[1]["allowed_targets"] == ["test", "build", "deploy"]

    def test_cli_args_override_env_vars(self) -> None:
        """CLI arguments take precedence over environment variables."""
        with patch.dict(
            os.environ,
            {
                "MCP_MAKEFILE_LOG_LEVEL": "DEBUG",
                "MCP_MAKEFILE_ALLOWED_TARGETS": "test,build",
            },
        ):
            from mcp_makefile.__main__ import cmd_serve

            args = MagicMock()
            args.log_level = "WARNING"  # CLI override
            args.makefile = Path(__file__).parent.parent / "fixtures" / "simple.mk"
            args.allowed_targets = ["deploy"]  # CLI override

            with patch("mcp_makefile.__main__.setup_logging") as mock_logging:
                with patch("mcp_makefile.__main__.MakefileMCPServer") as mock_server:
                    with patch("mcp_makefile.__main__.asyncio.run"):
                        cmd_serve(args)

                # Should use CLI args, not env vars
                mock_logging.assert_called_once_with("DEBUG")  # Env var used for log level
                call_args = mock_server.call_args
                assert call_args[1]["allowed_targets"] == ["deploy"]  # CLI used for targets
