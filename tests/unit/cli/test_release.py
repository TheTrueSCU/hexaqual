"""Unit tests for Hexaqual release engineering CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.release import release_app
from hexaqual.domain.pypi import (
    PackageBuildResult,
    PackageMetadata,
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleBuildReport,
)

runner = CliRunner()


def test_release_help() -> None:
    """Test release help output."""
    res = runner.invoke(release_app, ["--help"])
    assert res.exit_code == 0
    assert "Distribution package building" in res.stdout


def test_release_build() -> None:
    """Test release build command."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = PyPiBuildReport(
        target_dist=Path("dist"),
        results=(
            PackageBuildResult(
                package=PackageMetadata(
                    name="pkg",
                    version="1.0",
                    dir_path=Path("."),
                    pyproject_path=Path("pyproject.toml"),
                ),
                success=True,
            ),
        ),
    )
    mock_pres = MagicMock()
    mock_pres.present_build.return_value = 0
    with (
        patch("hexaqual.cli.release.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.cli.release.create_pypi_presenter", return_value=mock_pres),
    ):
        res = runner.invoke(release_app, ["build"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called


def test_release_check() -> None:
    """Test release check command."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = PyPiCheckReport(checks=())
    mock_pres = MagicMock()
    mock_pres.present_check.return_value = 0
    with (
        patch("hexaqual.cli.release.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.cli.release.create_pypi_presenter", return_value=mock_pres),
    ):
        res = runner.invoke(release_app, ["check"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        assert mock_pres.present_check.called


def test_release_publish() -> None:
    """Test release publish command."""
    mock_bus = MagicMock()
    mock_bus.dispatch.side_effect = [
        PyPiBuildReport(
            target_dist=Path("dist"),
            results=(
                PackageBuildResult(
                    package=PackageMetadata(
                        name="pkg",
                        version="1.0",
                        dir_path=Path("."),
                        pyproject_path=Path("pyproject.toml"),
                    ),
                    success=True,
                ),
            ),
        ),
        PyPiPublishReport(results=()),
    ]
    mock_pres = MagicMock()
    mock_pres.present_build.return_value = 0
    mock_pres.present_publish.return_value = 0
    with (
        patch("hexaqual.cli.release.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.cli.release.create_pypi_presenter", return_value=mock_pres),
    ):
        res = runner.invoke(release_app, ["publish", "--token", "secret"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called


def test_release_reproducible() -> None:
    """Test release reproducible verification command."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = ReproducibleBuildReport(epoch="0", results=())
    mock_pres = MagicMock()
    mock_pres.present_reproducible.return_value = 0
    with (
        patch("hexaqual.cli.release.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.cli.release.create_pypi_presenter", return_value=mock_pres),
    ):
        res = runner.invoke(release_app, ["reproducible"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
