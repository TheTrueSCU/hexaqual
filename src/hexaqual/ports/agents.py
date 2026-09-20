"""Abstract ports for .agents assets synchronization and presentation.

Notes/Architectural Intent:
    Decouples package asset loading, filesystem synchronization, and drift
    detection from CLI presentation and specific terminal renderers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from hexaqual.domain.agents import (
    AgentAsset,
    AgentCheckReport,
    AgentSyncReport,
)

__all__ = [
    "AgentAssetPort",
    "AgentPresenterPort",
]


class AgentAssetPort(ABC):
    """Abstract port for managing and inspecting .agents assets."""

    @abstractmethod
    def load_bundled_assets(self) -> tuple[AgentAsset, ...]:
        """Load all bundled rules, workflows, and skills from package resources.

        Returns:
            Tuple of AgentAsset models containing name, kind, path, and text.

        Raises:
            RuntimeError: If bundled assets cannot be discovered or loaded.

        Notes/Architectural Intent:
            Package asset reader decoupling filesystem locations from consumption.
        """

    @abstractmethod
    def sync_assets(self, target_dir: Path, dry_run: bool = False) -> AgentSyncReport:
        """Synchronize managed agent assets to the target repository directory.

        Args:
            target_dir: Path to the target repository root or .agents directory.
            dry_run: Whether to simulate changes without writing to disk.

        Returns:
            AgentSyncReport summarizing created, updated, and preserved files.

        Raises:
            OSError: If file read or write operations encounter I/O errors.

        Notes/Architectural Intent:
            Overwrites managed files (matching hexaqual-* or hexaqual_*) while
            strictly preserving repo-specific local assets.
        """

    @abstractmethod
    def check_drift(self, target_dir: Path) -> AgentCheckReport:
        """Check for drift between target directory and bundled assets.

        Args:
            target_dir: Path to the target repository root or .agents directory.

        Returns:
            AgentCheckReport indicating whether assets match and listing differences.

        Raises:
            OSError: If files cannot be read for comparison.

        Notes/Architectural Intent:
            Powers pre-commit checks and CI validation to detect out-of-sync guardrails.
        """


class AgentPresenterPort(ABC):
    """Abstract port for presenting agent synchronization and check outcomes."""

    @abstractmethod
    def present_sync(self, report: AgentSyncReport) -> int:
        """Render the results of an agent assets synchronization run.

        Args:
            report: The AgentSyncReport data to present.

        Returns:
            Exit code (0 for success).

        Notes/Architectural Intent:
            Formats sync summaries for human-readable terminal or machine output.
        """

    @abstractmethod
    def present_check(self, report: AgentCheckReport) -> int:
        """Render the results of an agent drift check.

        Args:
            report: The AgentCheckReport data to present.

        Returns:
            Exit code (0 if clean, 1 if drift detected).

        Notes/Architectural Intent:
            Enforces strict returncode 1 when managed files have drifted.
        """

    @abstractmethod
    def present_list(self, assets: tuple[AgentAsset, ...]) -> int:
        """Render a catalog of bundled agent assets.

        Args:
            assets: Tuple of available bundled AgentAsset items.

        Returns:
            Exit code (0 for success).

        Notes/Architectural Intent:
            Displays available rules, workflows, and skills.
        """
