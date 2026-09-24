"""PyPI Monorepo Distribution Builder and Package Publisher Adapter.

Notes/Architectural Intent:
    Adapter implementing PackagePublisherPort (PyPiClientPort) and providing metadata
    discovery and version check functions without coupling to higher infrastructure layers.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from hexaqual.adapters.runners.pypi_runner import SubprocessPyPiRunnerAdapter
from hexaqual.adapters.workspace import get_package_directories, get_repo_root
from hexaqual.domain.pypi import PackageMetadata
from hexaqual.ports.publishers import PackagePublisherPort

__all__ = [
    "check_pypi_version_exists",
    "get_workspace_packages_metadata",
    "PackageMetadata",
    "PyPiPublisherAdapter",
]


class PyPiPublisherAdapter(SubprocessPyPiRunnerAdapter, PackagePublisherPort):
    """Adapter implementing PackagePublisherPort via SubprocessPyPiRunnerAdapter."""

    def __init__(self, repo_root: Path | None = None) -> None:
        super().__init__(repo_root=repo_root or get_repo_root())


def check_pypi_version_exists(package_name: str, version: str) -> bool:
    """Check if a specific package version is already released on PyPI.

    Args:
        package_name: Name of the distribution package.
        version: Version string to check.

    Returns:
        True if package version exists on PyPI, False otherwise.
    """
    runner = SubprocessPyPiRunnerAdapter()
    return runner.check_version_exists(package_name, version)


def get_workspace_packages_metadata(root: Path | None = None) -> list[PackageMetadata]:
    """Discover all packages in the workspace and extract their name and version.

    Args:
        root: Optional repository root directory.

    Returns:
        Sorted list of PackageMetadata domain models.
    """
    repo_root = root or get_repo_root()
    pkg_dirs = get_package_directories(repo_root)
    packages: list[PackageMetadata] = []

    for pkg_dir in pkg_dirs:
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue

        try:
            content = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = content.get("project", {})
            name = project.get("name")
            version = project.get("version")
            if name and version:
                packages.append(
                    PackageMetadata(
                        name=name,
                        version=version,
                        dir_path=pkg_dir,
                        pyproject_path=pyproject,
                    )
                )
        except Exception:
            continue
    return sorted(packages, key=lambda p: p.name)
