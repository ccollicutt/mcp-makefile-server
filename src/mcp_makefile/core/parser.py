"""Makefile parsing functionality."""

import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path

from mcp_makefile.core.models import MakefileMetadata, MakeTarget
from mcp_makefile.exceptions import MakefileNotFoundError, MakefileParseError

logger = logging.getLogger(__name__)


class MakefileParser(ABC):
    """Abstract base class for Makefile parsing."""

    @abstractmethod
    def parse(self, makefile_path: Path) -> MakefileMetadata:
        """Parse Makefile and return metadata."""
        pass

    @abstractmethod
    def parse_string(self, content: str, path: Path | None = None) -> MakefileMetadata:
        """Parse Makefile from string content."""
        pass


class RegexMakefileParser(MakefileParser):
    """Parse Makefile using regex patterns."""

    # Pattern for targets with descriptions: target: deps ## description
    TARGET_PATTERN = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:([^#]*)##\s*(.+)$")

    # Pattern for category headers: ## Category: Name
    CATEGORY_PATTERN = re.compile(r"^##\s*Category:\s*(.+)$")

    # Pattern for .PHONY declarations
    PHONY_PATTERN = re.compile(r"^\.PHONY:\s*(.+)$")

    def parse(self, makefile_path: Path) -> MakefileMetadata:
        """Parse Makefile from file."""
        # Validate file exists
        if not makefile_path.exists():
            raise MakefileNotFoundError(str(makefile_path))

        # Validate it's a file, not a directory
        if not makefile_path.is_file():
            raise MakefileParseError(str(makefile_path), f"Path is not a file: {makefile_path}")

        # Validate file is readable
        if not os.access(makefile_path, os.R_OK):
            raise MakefileParseError(str(makefile_path), f"File is not readable: {makefile_path}")

        try:
            content = makefile_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise MakefileParseError(str(makefile_path), f"File is not valid UTF-8: {e}")
        except PermissionError as e:
            raise MakefileParseError(str(makefile_path), f"Permission denied reading file: {e}")
        except Exception as e:
            logger.exception("Failed to read Makefile")
            raise MakefileParseError(str(makefile_path), f"Failed to read file: {e}")

        try:
            return self.parse_string(content, makefile_path)
        except MakefileNotFoundError:
            raise
        except Exception as e:
            logger.exception("Failed to parse Makefile")
            raise MakefileParseError(str(makefile_path), str(e))

    def parse_string(self, content: str, path: Path | None = None) -> MakefileMetadata:
        """Parse Makefile from string content."""
        metadata = MakefileMetadata(path=path or Path("Makefile"))
        current_category: str | None = None
        phony_targets: set[str] = set()

        # First pass: collect .PHONY targets
        for line in content.splitlines():
            phony_match = self.PHONY_PATTERN.match(line.strip())
            if phony_match:
                targets = phony_match.group(1).split()
                phony_targets.update(targets)

        # Second pass: parse targets and categories
        for line in content.splitlines():
            line = line.rstrip()

            # Check for category header
            category_match = self.CATEGORY_PATTERN.match(line)
            if category_match:
                category_name = category_match.group(1)
                if category_name:  # Regex group 1 always exists for this pattern
                    current_category = category_name.strip()
                    if current_category not in metadata.categories:
                        metadata.categories.append(current_category)  # type: ignore[arg-type]
                continue

            # Check for target with description
            target_match = self.TARGET_PATTERN.match(line)
            if target_match:
                name = target_match.group(1).strip()
                deps_str = target_match.group(2).strip()
                description = target_match.group(3).strip()

                # Check for @internal or @skip tags (with or without description)
                is_internal = (
                    description.startswith("@internal ")
                    or description.startswith("@skip ")
                    or description == "@internal"
                    or description == "@skip"
                )

                # Remove tag from description if present
                if is_internal:
                    description = description.split(None, 1)[1] if " " in description else ""

                # Parse dependencies
                dependencies = [d.strip() for d in deps_str.split() if d.strip()]

                target = MakeTarget(
                    name=name,
                    description=description,
                    category=current_category,
                    dependencies=dependencies,
                    is_phony=name in phony_targets,
                    is_internal=is_internal,
                )
                metadata.targets[name] = target

        # Log summary
        total_targets = len(metadata.targets)
        exposed_targets = len(metadata.get_exposed_targets())
        internal_targets = len(metadata.get_internal_targets())

        logger.info(
            f"Parsed Makefile: {total_targets} targets ({exposed_targets} exposed, {internal_targets} internal)"
        )

        if total_targets == 0:
            logger.warning(f"No documented targets found in {metadata.path}")

        return metadata
