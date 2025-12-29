"""Data models for Makefile parsing and execution."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MakeTarget:
    """Represents a single Makefile target."""

    name: str
    description: str
    category: str | None = None
    dependencies: list[str] = field(default_factory=list)
    is_phony: bool = False
    is_internal: bool = False  # Marked with @internal or @skip

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "dependencies": self.dependencies,
            "is_phony": self.is_phony,
            "is_internal": self.is_internal,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MakeTarget":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            category=data.get("category"),
            dependencies=data.get("dependencies", []),
            is_phony=data.get("is_phony", False),
            is_internal=data.get("is_internal", False),
        )


@dataclass
class MakefileMetadata:
    """Metadata about a parsed Makefile."""

    path: Path
    targets: dict[str, MakeTarget] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)

    def get_target(self, name: str) -> MakeTarget | None:
        """Get target by name."""
        return self.targets.get(name)

    def get_targets_by_category(self, category: str) -> list[MakeTarget]:
        """Get all targets in a category."""
        return [t for t in self.targets.values() if t.category == category]

    def get_exposed_targets(self) -> dict[str, MakeTarget]:
        """Get targets that should be exposed via MCP (not internal)."""
        return {name: target for name, target in self.targets.items() if not target.is_internal}

    def get_internal_targets(self) -> dict[str, MakeTarget]:
        """Get targets marked as internal."""
        return {name: target for name, target in self.targets.items() if target.is_internal}


@dataclass
class ExecutionResult:
    """Result of executing a make target."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    target: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "target": self.target,
            "timestamp": self.timestamp.isoformat(),
        }
