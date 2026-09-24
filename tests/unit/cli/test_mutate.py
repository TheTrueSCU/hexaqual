"""Unit tests for Hexaqual mutation testing CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.mutate import mutate_app
from hexaqual.domain.testing import MutationAuditReport

runner = CliRunner()


def test_mutate_help() -> None:
    """Test mutate help output."""
    res = runner.invoke(mutate_app, ["--help"])
    assert res.exit_code == 0
    assert "Mutation testing execution" in res.stdout


def test_mutate_run() -> None:
    """Test mutate run command dispatches RunMutationTestsCommand."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = 0
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed"),
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(mutate_app, ["run", "-p", "core"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called


def test_mutate_inspect() -> None:
    """Test mutate inspect command dispatches InspectMutationCacheCommand."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = MutationAuditReport(
        summaries=(),
        actionable_mutants=(),
    )
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed"),
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(mutate_app, ["inspect", "--summary"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
