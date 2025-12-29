"""Tests for Makefile parser."""

from pathlib import Path

import pytest

from mcp_makefile.core.parser import RegexMakefileParser
from mcp_makefile.exceptions import MakefileNotFoundError, MakefileParseError

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestRegexMakefileParser:
    """Tests for RegexMakefileParser."""

    def test_parse_simple_makefile(self) -> None:
        """Parse simple Makefile with 2 documented targets."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "simple.mk"

        metadata = parser.parse(makefile)

        assert len(metadata.targets) == 2
        assert "test" in metadata.targets
        assert "build" in metadata.targets

        test_target = metadata.targets["test"]
        assert test_target.name == "test"
        assert test_target.description == "Run tests"
        assert test_target.is_phony is True

        build_target = metadata.targets["build"]
        assert build_target.name == "build"
        assert build_target.description == "Build package"
        assert build_target.dependencies == ["test"]

    def test_parse_makefile_with_categories(self) -> None:
        """Parse Makefile with categories."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "categorized.mk"

        metadata = parser.parse(makefile)

        assert len(metadata.categories) == 2
        assert "Testing" in metadata.categories
        assert "Building" in metadata.categories

        test_target = metadata.targets["test"]
        assert test_target.category == "Testing"

        build_target = metadata.targets["build"]
        assert build_target.category == "Building"

    def test_parse_targets_with_dependencies(self) -> None:
        """Parse targets with dependencies."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "simple.mk"

        metadata = parser.parse(makefile)

        build_target = metadata.targets["build"]
        assert build_target.dependencies == ["test"]

    def test_parse_phony_declarations(self) -> None:
        """Parse .PHONY declarations."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "simple.mk"

        metadata = parser.parse(makefile)

        assert metadata.targets["test"].is_phony is True
        assert metadata.targets["build"].is_phony is True

    def test_parse_internal_tag(self) -> None:
        """Parse targets with @internal tag."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "mixed.mk"

        metadata = parser.parse(makefile)

        dangerous_target = metadata.targets["deploy-dangerous"]
        assert dangerous_target.is_internal is True
        assert dangerous_target.description == "Deploy without safety checks"
        assert "@internal" not in dangerous_target.description

    def test_parse_skip_tag(self) -> None:
        """Parse targets with @skip tag."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "mixed.mk"

        metadata = parser.parse(makefile)

        cleanup_target = metadata.targets["cleanup-prod"]
        assert cleanup_target.is_internal is True
        assert cleanup_target.description == "Clean production database"
        assert "@skip" not in cleanup_target.description

    def test_ignore_undocumented_targets(self) -> None:
        """Ignore targets without ## descriptions."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "mixed.mk"

        metadata = parser.parse(makefile)

        assert "internal-helper" not in metadata.targets
        assert "_private_target" not in metadata.targets

    def test_mix_of_documented_and_internal(self) -> None:
        """Mix of documented, undocumented, and internal targets."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "mixed.mk"

        metadata = parser.parse(makefile)

        # Total targets (including internal)
        assert len(metadata.targets) == 5  # test, clean, deploy-dangerous, cleanup-prod, deploy

        # Exposed targets (not internal)
        exposed = metadata.get_exposed_targets()
        assert len(exposed) == 3  # test, clean, deploy
        assert "test" in exposed
        assert "clean" in exposed
        assert "deploy" in exposed

        # Internal targets
        internal = metadata.get_internal_targets()
        assert len(internal) == 2  # deploy-dangerous, cleanup-prod
        assert "deploy-dangerous" in internal
        assert "cleanup-prod" in internal

    def test_parse_empty_makefile(self) -> None:
        """Handle empty Makefile (returns empty metadata, no error)."""
        parser = RegexMakefileParser()

        metadata = parser.parse_string("", Path("Empty.mk"))

        assert len(metadata.targets) == 0
        assert len(metadata.categories) == 0

    def test_parse_makefile_no_documented_targets(self) -> None:
        """Handle Makefile with no documented targets."""
        parser = RegexMakefileParser()
        content = """
# No documented targets here
undocumented:
\techo "No description"
"""
        metadata = parser.parse_string(content, Path("Undocumented.mk"))

        assert len(metadata.targets) == 0

    def test_parse_nonexistent_file(self) -> None:
        """Handle non-existent file (raises MakefileNotFoundError)."""
        parser = RegexMakefileParser()
        makefile = Path("/nonexistent/Makefile")

        with pytest.raises(MakefileNotFoundError) as exc_info:
            parser.parse(makefile)

        assert exc_info.value.path == str(makefile)

    def test_parse_string_basic(self) -> None:
        """Parse Makefile from string."""
        parser = RegexMakefileParser()
        content = """
.PHONY: test

test: ## Run tests
\tpytest
"""
        metadata = parser.parse_string(content, Path("Test.mk"))

        assert len(metadata.targets) == 1
        assert "test" in metadata.targets
        assert metadata.targets["test"].description == "Run tests"

    def test_get_targets_by_category(self) -> None:
        """Get targets by category."""
        parser = RegexMakefileParser()
        makefile = FIXTURES_DIR / "categorized.mk"

        metadata = parser.parse(makefile)

        testing_targets = metadata.get_targets_by_category("Testing")
        assert len(testing_targets) == 2
        assert any(t.name == "test" for t in testing_targets)
        assert any(t.name == "lint" for t in testing_targets)

        building_targets = metadata.get_targets_by_category("Building")
        assert len(building_targets) == 2
        assert any(t.name == "build" for t in building_targets)
        assert any(t.name == "clean" for t in building_targets)

    def test_handle_malformed_lines(self) -> None:
        """Handle malformed lines gracefully (skip and continue)."""
        parser = RegexMakefileParser()
        content = """
test: ## Run tests
\tpytest

This is a malformed line
And another one

build: ## Build package
\tpython -m build
"""
        metadata = parser.parse_string(content, Path("Malformed.mk"))

        # Should still parse the valid targets
        assert len(metadata.targets) == 2
        assert "test" in metadata.targets
        assert "build" in metadata.targets

    def test_parse_directory_path(self, tmp_path: Path) -> None:
        """Parsing a directory raises MakefileParseError."""
        parser = RegexMakefileParser()
        directory = tmp_path / "some_dir"
        directory.mkdir()

        with pytest.raises(MakefileParseError, match="not a file"):
            parser.parse(directory)

    def test_parse_unreadable_file(self, tmp_path: Path) -> None:
        """Parsing an unreadable file raises MakefileParseError."""
        parser = RegexMakefileParser()
        makefile = tmp_path / "Makefile"
        makefile.write_text("test: ## Test\n\techo test")
        makefile.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(MakefileParseError, match="not readable|Permission denied"):
                parser.parse(makefile)
        finally:
            makefile.chmod(0o644)  # Restore permissions for cleanup

    def test_parse_non_utf8_file(self, tmp_path: Path) -> None:
        """Parsing a non-UTF-8 file raises MakefileParseError."""
        parser = RegexMakefileParser()
        makefile = tmp_path / "Makefile"
        # Write invalid UTF-8 bytes
        makefile.write_bytes(b"test: ## \xff\xfe Invalid UTF-8\n")

        with pytest.raises(MakefileParseError, match="not valid UTF-8"):
            parser.parse(makefile)
