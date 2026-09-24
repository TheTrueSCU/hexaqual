"""Abstract port interfaces for workspace discovery and project inspection.

Notes/Architectural Intent:
    Defines abstract contract for discovering monorepo root paths, package directories,
    example directories, and workspace metadata without coupling to local filesystem or git.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

__all__ = [
    "WorkspaceDiscoveryPort",
]


class WorkspaceDiscoveryPort(ABC):
    """Abstract contract for workspace discovery and directory resolution."""

    @abstractmethod
    def get_repo_root(self, start_path: Path | None = None) -> Path:
        """Resolve repository root directory from start path or working directory."""
        raise NotImplementedError

    @abstractmethod
    def get_package_directories(self, root: Path | None = None) -> list[Path]:
        """Return list of all package directories within the workspace."""
        raise NotImplementedError

    @abstractmethod
    def get_packages_directory(self, root: Path | None = None) -> Path:
        """Return the base packages container directory."""
        raise NotImplementedError

    @abstractmethod
    def get_package_directory(self, name: str, root: Path | None = None) -> Path:
        """Resolve directory path for a specific named package."""
        raise NotImplementedError

    @abstractmethod
    def is_multipackage_workspace(self, root: Path | None = None) -> bool:
        """Determine if repository operates as a multi-package monorepo workspace."""
        raise NotImplementedError
