"""Tests for data models."""

from pathlib import Path

from mcp_makefile.core.models import ExecutionResult, MakefileMetadata, MakeTarget


class TestMakeTarget:
    """Tests for MakeTarget class."""

    def test_create_basic_target(self) -> None:
        """Can create a basic target."""
        target = MakeTarget(name="test", description="Run tests")

        assert target.name == "test"
        assert target.description == "Run tests"
        assert target.category is None
        assert target.dependencies == []
        assert target.is_phony is False
        assert target.is_internal is False

    def test_create_target_with_category(self) -> None:
        """Can create target with category."""
        target = MakeTarget(name="test", description="Run tests", category="Testing")

        assert target.category == "Testing"

    def test_create_target_with_dependencies(self) -> None:
        """Can create target with dependencies."""
        target = MakeTarget(name="deploy", description="Deploy", dependencies=["build", "test"])

        assert target.dependencies == ["build", "test"]

    def test_create_internal_target(self) -> None:
        """Can create internal target."""
        target = MakeTarget(name="dangerous", description="Dangerous operation", is_internal=True)

        assert target.is_internal is True

    def test_to_dict(self) -> None:
        """Can serialize to dictionary."""
        target = MakeTarget(
            name="build",
            description="Build package",
            category="Building",
            dependencies=["clean"],
            is_phony=True,
            is_internal=False,
        )

        result = target.to_dict()

        assert result == {
            "name": "build",
            "description": "Build package",
            "category": "Building",
            "dependencies": ["clean"],
            "is_phony": True,
            "is_internal": False,
        }

    def test_from_dict(self) -> None:
        """Can deserialize from dictionary."""
        data = {
            "name": "test",
            "description": "Run tests",
            "category": "Testing",
            "dependencies": ["build"],
            "is_phony": True,
            "is_internal": False,
        }

        target = MakeTarget.from_dict(data)

        assert target.name == "test"
        assert target.description == "Run tests"
        assert target.category == "Testing"
        assert target.dependencies == ["build"]
        assert target.is_phony is True
        assert target.is_internal is False

    def test_serialization_roundtrip(self) -> None:
        """Serialization round-trip preserves data."""
        original = MakeTarget(
            name="deploy", description="Deploy to prod", category="Deployment", dependencies=["test"], is_phony=True
        )

        result = MakeTarget.from_dict(original.to_dict())

        assert result.name == original.name
        assert result.description == original.description
        assert result.category == original.category
        assert result.dependencies == original.dependencies
        assert result.is_phony == original.is_phony


class TestMakefileMetadata:
    """Tests for MakefileMetadata class."""

    def test_create_empty_metadata(self) -> None:
        """Can create empty metadata."""
        metadata = MakefileMetadata(path=Path("Makefile"))

        assert metadata.path == Path("Makefile")
        assert metadata.targets == {}
        assert metadata.categories == []

    def test_add_target(self) -> None:
        """Can add target to metadata."""
        metadata = MakefileMetadata(path=Path("Makefile"))
        target = MakeTarget(name="test", description="Run tests")

        metadata.targets["test"] = target

        assert "test" in metadata.targets
        assert metadata.targets["test"] == target

    def test_get_target(self) -> None:
        """Can get target by name."""
        metadata = MakefileMetadata(path=Path("Makefile"))
        target = MakeTarget(name="test", description="Run tests")
        metadata.targets["test"] = target

        result = metadata.get_target("test")

        assert result == target

    def test_get_nonexistent_target(self) -> None:
        """Returns None for nonexistent target."""
        metadata = MakefileMetadata(path=Path("Makefile"))

        result = metadata.get_target("nonexistent")

        assert result is None

    def test_get_targets_by_category(self) -> None:
        """Can get targets by category."""
        metadata = MakefileMetadata(path=Path("Makefile"))
        test1 = MakeTarget(name="test", description="Run tests", category="Testing")
        test2 = MakeTarget(name="lint", description="Run linter", category="Testing")
        build = MakeTarget(name="build", description="Build", category="Building")

        metadata.targets["test"] = test1
        metadata.targets["lint"] = test2
        metadata.targets["build"] = build

        result = metadata.get_targets_by_category("Testing")

        assert len(result) == 2
        assert test1 in result
        assert test2 in result
        assert build not in result

    def test_get_exposed_targets(self) -> None:
        """Returns only non-internal targets."""
        metadata = MakefileMetadata(path=Path("Makefile"))
        public = MakeTarget(name="test", description="Run tests", is_internal=False)
        internal = MakeTarget(name="dangerous", description="Dangerous", is_internal=True)

        metadata.targets["test"] = public
        metadata.targets["dangerous"] = internal

        result = metadata.get_exposed_targets()

        assert len(result) == 1
        assert "test" in result
        assert "dangerous" not in result

    def test_get_internal_targets(self) -> None:
        """Returns only internal targets."""
        metadata = MakefileMetadata(path=Path("Makefile"))
        public = MakeTarget(name="test", description="Run tests", is_internal=False)
        internal = MakeTarget(name="dangerous", description="Dangerous", is_internal=True)

        metadata.targets["test"] = public
        metadata.targets["dangerous"] = internal

        result = metadata.get_internal_targets()

        assert len(result) == 1
        assert "dangerous" in result
        assert "test" not in result


class TestExecutionResult:
    """Tests for ExecutionResult class."""

    def test_create_success_result(self) -> None:
        """Can create successful execution result."""
        result = ExecutionResult(
            success=True, exit_code=0, stdout="Build successful", stderr="", duration=1.5, target="build"
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Build successful"
        assert result.stderr == ""
        assert result.duration == 1.5
        assert result.target == "build"
        assert result.timestamp is not None

    def test_create_failure_result(self) -> None:
        """Can create failed execution result."""
        result = ExecutionResult(
            success=False, exit_code=1, stdout="", stderr="Build failed", duration=0.5, target="build"
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "Build failed"

    def test_to_dict(self) -> None:
        """Can serialize to dictionary."""
        result = ExecutionResult(success=True, exit_code=0, stdout="output", stderr="", duration=1.0, target="test")

        data = result.to_dict()

        assert data["success"] is True
        assert data["exit_code"] == 0
        assert data["stdout"] == "output"
        assert data["stderr"] == ""
        assert data["duration"] == 1.0
        assert data["target"] == "test"
        assert "timestamp" in data
