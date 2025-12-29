#!/usr/bin/env python3
"""Entry point for MCP Makefile Server."""

import argparse
import asyncio
import sys
from pathlib import Path

from mcp_makefile.server import MakefileMCPServer, setup_logging


def main():
    """Run the MCP Makefile server."""
    parser = argparse.ArgumentParser(description="MCP server that exposes Makefile targets as tools")
    parser.add_argument(
        "makefile",
        type=Path,
        nargs="?",
        default=Path("Makefile"),
        help="Path to Makefile (default: ./Makefile)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--allowed-targets",
        nargs="+",
        help="Allowlist of allowed targets (default: all non-internal targets)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Validate Makefile exists
    if not args.makefile.exists():
        print(f"Error: Makefile not found: {args.makefile}", file=sys.stderr)
        sys.exit(1)

    # Create and run server
    server = MakefileMCPServer(
        makefile_path=args.makefile,
        allowed_targets=args.allowed_targets,
    )

    asyncio.run(server.run())


if __name__ == "__main__":
    main()
