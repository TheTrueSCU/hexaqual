"""Unit tests for Hexaqual docs CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.docs import docs_app
from hexaqual.cli.main import app

runner = CliRunner()


def test_docs_help() -> None:
    """Test docs help output."""
    res = runner.invoke(app, ["docs", "--help"])
    assert res.exit_code == 0
    assert "Documentation generation and verification" in res.stdout


def test_docs_usage() -> None:
    """Test docs usage subcommand."""
    from hexaqual.domain.generators import UsageDocsReport

    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = UsageDocsReport(is_valid=True, up_to_date_files=("USAGE.md",))
    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        res = runner.invoke(app, ["docs", "usage", "--check"])
        assert res.exit_code == 0


def test_docs_app_structure() -> None:
    """Verify docs_app Typer configuration."""
    assert docs_app.info.name == "docs"


def test_docs_publish_success() -> None:
    """Test docs publish dispatches PublishMediumArticlesCommand across governance bus."""
    mock_bus = MagicMock()
    mock_report = MagicMock()
    mock_bus.dispatch.return_value = mock_report
    mock_pres = MagicMock()
    mock_pres.present_medium_publish.return_value = 0

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.refactoring.create_refactoring_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(docs_app, ["publish", "--publish", "-f", "json"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.publish is True
        assert mock_pres.present_medium_publish.called


def test_docs_publish_failure() -> None:
    """Test docs publish handles non-zero presenter exit code."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_medium_publish.return_value = 1

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.refactoring.create_refactoring_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(docs_app, ["publish"])
        assert res.exit_code == 1
