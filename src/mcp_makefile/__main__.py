#!/usr/bin/env python3
"""Entry point for MCP Makefile Server."""

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

from mcp_makefile.core.parser import RegexMakefileParser
from mcp_makefile.server import MakefileMCPServer, setup_logging


def cmd_preview(args):
    """Preview what tools would be exposed from a Makefile."""
    if not args.makefile.exists():
        print(f"Error: Makefile not found: {args.makefile}", file=sys.stderr)
        sys.exit(1)

    # Parse Makefile
    parser = RegexMakefileParser()
    metadata = parser.parse(args.makefile)

    exposed = list(metadata.get_exposed_targets().values())
    internal = list(metadata.get_internal_targets().values())

    print(f"Makefile: {args.makefile}")
    print(f"Total targets: {len(metadata.targets)}")
    print(f"Exposed as MCP tools: {len(exposed)}")
    print(f"Internal (hidden): {len(internal)}")
    print()

    if not exposed:
        print("No targets would be exposed as MCP tools.")
        print("Add '## Description' comments to your Makefile targets.")
        return

    # Group by category
    by_category = defaultdict(list)
    for target in exposed:
        category = target.category or "Uncategorized"
        by_category[category].append(target)

    # Display by category
    for category in sorted(by_category.keys()):
        print(f"\n{'=' * 70}")
        print(f"  {category}")
        print("=" * 70)
        for target in sorted(by_category[category], key=lambda t: t.name):
            deps = f" → depends on: {', '.join(target.dependencies)}" if target.dependencies else ""
            print(f"\n  {target.name}")
            print(f"    {target.description}{deps}")

    # Show internal targets if any
    if internal:
        print(f"\n{'=' * 70}")
        print("  Internal Targets (NOT exposed)")
        print("=" * 70)
        for target in sorted(internal, key=lambda t: t.name):
            print(f"  {target.name} - {target.description}")

    print(f"\n{'=' * 70}")
    print("  Summary")
    print("=" * 70)
    print(f"Claude Code would see {len(exposed)} tools from this Makefile")
    print("Each tool is callable with optional 'variables' parameter")
    print()


def cmd_list(args):
    """List tool names that would be exposed."""
    if not args.makefile.exists():
        print(f"Error: Makefile not found: {args.makefile}", file=sys.stderr)
        sys.exit(1)

    parser = RegexMakefileParser()
    metadata = parser.parse(args.makefile)
    exposed = list(metadata.get_exposed_targets().values())

    for target in sorted(exposed, key=lambda t: t.name):
        print(f"{target.name}")


def cmd_serve(args):
    """Run the MCP server."""
    # Read configuration from environment variables (with CLI args as overrides)
    log_level = os.getenv("MCP_MAKEFILE_LOG_LEVEL", args.log_level)
    makefile_path = Path(os.getenv("MCP_MAKEFILE_PATH", str(args.makefile)))

    # Allowed targets from env (comma-separated) or args
    allowed_targets = args.allowed_targets
    if not allowed_targets and os.getenv("MCP_MAKEFILE_ALLOWED_TARGETS"):
        allowed_targets = [t.strip() for t in os.getenv("MCP_MAKEFILE_ALLOWED_TARGETS", "").split(",") if t.strip()]

    # Setup logging
    setup_logging(log_level)

    # Validate Makefile exists
    if not makefile_path.exists():
        print(f"Error: Makefile not found: {makefile_path}", file=sys.stderr)
        sys.exit(1)

    # Create and run server
    server = MakefileMCPServer(
        makefile_path=makefile_path,
        allowed_targets=allowed_targets,
    )

    asyncio.run(server.run())


def main():
    """Main entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="MCP server that exposes Makefile targets as tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what tools would be exposed
  mcp-makefile-server preview ./Makefile

  # List tool names only
  mcp-makefile-server list ./Makefile

  # Run MCP server (for use with Claude Code)
  mcp-makefile-server serve ./Makefile

  # Run with allowed targets filter
  mcp-makefile-server serve ./Makefile --allowed-targets test build deploy
        """,
    )

    # For backwards compatibility, if first arg is a path, treat it as 'serve'
    # This allows: mcp-makefile-server ./Makefile (old behavior)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        first_arg = Path(sys.argv[1])
        if first_arg.exists() or sys.argv[1] in ["preview", "list", "serve"]:
            # It's either a subcommand or a file path
            if sys.argv[1] not in ["preview", "list", "serve"]:
                # It's a file path, insert 'serve' subcommand
                sys.argv.insert(1, "serve")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Preview command
    preview_parser = subparsers.add_parser("preview", help="Preview what MCP tools would be exposed")
    preview_parser.add_argument(
        "makefile",
        type=Path,
        nargs="?",
        default=Path("Makefile"),
        help="Path to Makefile (default: ./Makefile)",
    )
    preview_parser.set_defaults(func=cmd_preview)

    # List command
    list_parser = subparsers.add_parser("list", help="List MCP tool names")
    list_parser.add_argument(
        "makefile",
        type=Path,
        nargs="?",
        default=Path("Makefile"),
        help="Path to Makefile (default: ./Makefile)",
    )
    list_parser.set_defaults(func=cmd_list)

    # Serve command (default)
    serve_parser = subparsers.add_parser("serve", help="Run MCP server")
    serve_parser.add_argument(
        "makefile",
        type=Path,
        nargs="?",
        default=Path("Makefile"),
        help="Path to Makefile (default: ./Makefile)",
    )
    serve_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    serve_parser.add_argument(
        "--allowed-targets",
        nargs="+",
        help="Allowlist of allowed targets (default: all non-internal targets)",
    )
    serve_parser.set_defaults(func=cmd_serve)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
