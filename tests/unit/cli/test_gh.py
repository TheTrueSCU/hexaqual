"""Unit tests for Hexaqual GitHub inspection CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.gh import gh_app

runner = CliRunner()


def test_gh_help() -> None:
    """Test gh help output."""
    res = runner.invoke(gh_app, ["--help"])
    assert res.exit_code == 0
    assert "GitHub repository, PR, and security" in res.stdout


def test_gh_pr() -> None:
    """Test gh pr command."""
    mock_bus = MagicMock()
    mock_rep = MagicMock()
    mock_bus.dispatch.return_value = mock_rep
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.adapters.presenters.github.create_github_presenter") as mock_create_pres,
    ):
        mock_pres = MagicMock()
        mock_pres.present_pr_summary.return_value = 0
        mock_create_pres.return_value = mock_pres

        res = runner.invoke(gh_app, ["pr", "42"])
        assert res.exit_code == 0
        assert mock_pres.present_pr_summary.called


def test_gh_checks() -> None:
    """Test gh checks command."""
    mock_bus = MagicMock()
    mock_rep = MagicMock()
    mock_bus.dispatch.return_value = mock_rep
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.adapters.presenters.github.create_github_presenter") as mock_create_pres,
    ):
        mock_pres = MagicMock()
        mock_pres.present_checks.return_value = 0
        mock_create_pres.return_value = mock_pres

        res = runner.invoke(gh_app, ["checks", "main"])
        assert res.exit_code == 0
        assert mock_pres.present_checks.called


def test_gh_repo() -> None:
    """Test gh repo command."""
    mock_bus = MagicMock()
    mock_rep = MagicMock()
    mock_bus.dispatch.return_value = mock_rep
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.adapters.presenters.github.create_github_presenter") as mock_create_pres,
    ):
        mock_pres = MagicMock()
        mock_pres.present_repo_status.return_value = 0
        mock_create_pres.return_value = mock_pres

        res = runner.invoke(gh_app, ["repo", "owner/repo"])
        assert res.exit_code == 0
        assert mock_pres.present_repo_status.called


def test_gh_security() -> None:
    """Test gh security command."""
    mock_bus = MagicMock()
    mock_rep = MagicMock()
    mock_bus.dispatch.return_value = mock_rep
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.adapters.presenters.github.create_github_presenter") as mock_create_pres,
    ):
        mock_pres = MagicMock()
        mock_pres.present_security_comments.return_value = 0
        mock_create_pres.return_value = mock_pres

        res = runner.invoke(gh_app, ["security"])
        assert res.exit_code == 0
        assert mock_pres.present_security_comments.called


def test_gh_code_scanning() -> None:
    """Test gh code-scanning command."""
    mock_bus = MagicMock()
    mock_rep = MagicMock()
    mock_bus.dispatch.return_value = mock_rep
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.adapters.presenters.github.create_github_presenter") as mock_create_pres,
    ):
        mock_pres = MagicMock()
        mock_pres.present_code_scanning.return_value = 0
        mock_create_pres.return_value = mock_pres

        res = runner.invoke(gh_app, ["code-scanning"])
        assert res.exit_code == 0
        assert mock_pres.present_code_scanning.called
