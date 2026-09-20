"""Domain models and value objects for .agents assets management.

Notes/Architectural Intent:
    Pure domain models defining agent asset categories, synchronizer results,
    and drift verification reports with zero external framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "AgentAsset",
    "AgentAssetKind",
    "AgentCheckReport",
    "AgentSyncReport",
]


class AgentAssetKind(StrEnum):
    """Categorization of agent assets."""

    RULE = "rules"
    WORKFLOW = "workflows"
    SKILL = "skills"


@dataclass(frozen=True)
class AgentAsset:
    """Individual bundled agent asset specification."""

    name: str
    kind: AgentAssetKind
    relative_path: str
    content: str


@dataclass(frozen=True)
class AgentSyncReport:
    """Outcome and diagnostics from an agent assets synchronization run."""

    created_count: int
    updated_count: int
    unchanged_count: int
    preserved_unmanaged_count: int
    details: tuple[str, ...]

    @property
    def total_synced(self) -> int:
        """Total number of managed assets written or updated."""
        return self.created_count + self.updated_count


@dataclass(frozen=True)
class AgentCheckReport:
    """Diagnostics and status from an agent drift check."""

    is_clean: bool
    drifted_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    details: tuple[str, ...]
