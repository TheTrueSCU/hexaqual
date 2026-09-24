"""Unit tests for WorkspaceDiscoveryPort ABC."""

from pathlib import Path

import pytest

from hexaqual.ports.workspace import WorkspaceDiscoveryPort


class DummyWorkspaceDiscovery(WorkspaceDiscoveryPort):
    def get_repo_root(self, start_path: Path | None = None) -> Path:
        return Path("/repo")

    def get_package_directories(self, root: Path | None = None) -> list[Path]:
        return [Path("/repo/packages/a")]

    def get_packages_directory(self, root: Path | None = None) -> Path:
        return Path("/repo/packages")

    def get_package_directory(self, name: str, root: Path | None = None) -> Path:
        return Path(f"/repo/packages/{name}")

    def is_multipackage_workspace(self, root: Path | None = None) -> bool:
        return True


def test_workspace_discovery_port_instantiation() -> None:
    impl = DummyWorkspaceDiscovery()
    assert impl.get_repo_root() == Path("/repo")
    assert impl.get_package_directories() == [Path("/repo/packages/a")]
    assert impl.get_packages_directory() == Path("/repo/packages")
    assert impl.get_package_directory("pkg") == Path("/repo/packages/pkg")
    assert impl.is_multipackage_workspace() is True


def test_workspace_discovery_port_abstract() -> None:
    with pytest.raises(TypeError):
        WorkspaceDiscoveryPort()  # type: ignore[abstract]
