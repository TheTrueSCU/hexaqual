"""Unit tests for Hexaqual release engineering CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from hexaqual.cli.release import release_app

runner = CliRunner()


def test_release_help() -> None:
    """Test release help output."""
    res = runner.invoke(release_app, ["--help"])
    assert res.exit_code == 0
    assert "Distribution package building" in res.stdout


def test_release_build() -> None:
    """Test release build command."""
    with patch("hexaqual.commands.pypi.build_all_packages", return_value=0) as mock_build:
        res = runner.invoke(release_app, ["build"])
        assert res.exit_code == 0
        assert mock_build.called


def test_release_check() -> None:
    """Test release check command."""
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus") as mock_bus,
        patch("hexaqual.adapters.presenters.pypi.create_pypi_presenter") as mock_pres,
    ):
        res = runner.invoke(release_app, ["check"])
        assert res.exit_code == 0
        assert mock_bus.called
        assert mock_pres.called


def test_release_publish() -> None:
    """Test release publish command."""
    with (
        patch("hexaqual.commands.pypi.build_all_packages", return_value=0),
        patch("hexaqual.commands.pypi.publish_packages", return_value=0) as mock_pub,
    ):
        res = runner.invoke(release_app, ["publish", "--token", "secret"])
        assert res.exit_code == 0
        assert mock_pub.called


def test_release_reproducible() -> None:
    """Test release reproducible verification command."""
    with patch("hexaqual.commands.pypi.verify_reproducible_builds", return_value=0) as mock_ver:
        res = runner.invoke(release_app, ["reproducible"])
        assert res.exit_code == 0
        assert mock_ver.called
