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


def test_gh_codeql_success() -> None:
    """Test gh codeql command dispatches ScanCodeQlCommand across governance bus."""
    mock_bus = MagicMock()
    mock_report = MagicMock()
    mock_bus.dispatch.return_value = mock_report
    mock_pres = MagicMock()
    mock_pres.present_codeql.return_value = 0

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.analysis.create_analysis_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(
            gh_app,
            [
                "codeql",
                "-s",
                "custom-suite",
                "-o",
                "report.sarif",
                "-t",
                "4",
                "-f",
                "json",
            ],
        )
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.query_suite == "custom-suite"
        assert str(cmd.output_sarif) == "report.sarif"
        assert cmd.threads == 4
        assert mock_pres.present_codeql.called


def test_gh_codeql_failure() -> None:
    """Test gh codeql command handles failure exit code."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_codeql.return_value = 1

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.analysis.create_analysis_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(gh_app, ["codeql"])
        assert res.exit_code == 1
