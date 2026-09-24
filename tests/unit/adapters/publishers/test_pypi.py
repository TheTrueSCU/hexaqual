"""Unit tests for PyPiPublisherAdapter and helper functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.adapters.publishers.pypi import (
    PyPiPublisherAdapter,
    check_pypi_version_exists,
    get_workspace_packages_metadata,
)


def test_pypi_callables() -> None:
    """Verify pypi distribution callables and adapter instantiation."""
    assert callable(check_pypi_version_exists)
    assert callable(get_workspace_packages_metadata)
    adapter = PyPiPublisherAdapter()
    assert isinstance(adapter, PyPiPublisherAdapter)


def test_check_pypi_version_exists():
    """Verify check_pypi_version_exists handles 200, 404, and exceptions."""
    with patch("httpx.Client.get") as mock_get:
        # 200 with release found
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"releases": {"0.3.5": [{}]}}
        mock_get.return_value = mock_resp
        assert check_pypi_version_exists("hexastack", "0.3.5") is True
        assert check_pypi_version_exists("hexastack", "0.4.0") is False

        # 404 not found
        mock_resp.status_code = 404
        assert check_pypi_version_exists("hexastack-new", "0.1.0") is False

        # Exception
        mock_get.side_effect = Exception("network error")
        assert check_pypi_version_exists("hexastack", "0.3.5") is False


def test_get_workspace_packages_metadata(tmp_path: Path):
    """Verify get_workspace_packages_metadata discovers pyproject.toml."""
    pkg_dir = tmp_path / "packages" / "demo_pkg"
    pkg_dir.mkdir(parents=True)
    pyproject = pkg_dir / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo-pkg"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )

    with patch("hexaqual.adapters.workspace.get_package_directories", return_value=[pkg_dir]):
        metadata = get_workspace_packages_metadata(root=tmp_path)
        assert len(metadata) == 1
        assert metadata[0].name == "demo-pkg"
        assert metadata[0].version == "0.1.0"
        assert metadata[0].dir_path == pkg_dir
