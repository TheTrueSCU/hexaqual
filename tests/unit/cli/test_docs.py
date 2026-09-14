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
