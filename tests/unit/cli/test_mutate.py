"""Unit tests for Hexaqual mutation testing CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from hexaqual.cli.mutate import mutate_app

runner = CliRunner()


def test_mutate_help() -> None:
    """Test mutate help output."""
    res = runner.invoke(mutate_app, ["--help"])
    assert res.exit_code == 0
    assert "Mutation testing execution" in res.stdout


def test_mutate_run() -> None:
    """Test mutate run command delegates to mutmut runner."""
    with patch("hexaqual.commands.mutmut.run_mutmut_on_package", return_value=0) as mock_run:
        res = runner.invoke(mutate_app, ["run", "-p", "core"])
        assert res.exit_code == 0
        assert mock_run.called


def test_mutate_inspect() -> None:
    """Test mutate inspect command delegates to mutmut inspector."""
    with (
        patch("hexaqual.commands.mutmut.get_db_connection") as mock_conn,
        patch("hexaqual.commands.mutmut.show_summary") as mock_summary,
    ):
        res = runner.invoke(mutate_app, ["inspect", "--summary"])
        assert res.exit_code == 0
        assert mock_conn.called
        assert mock_summary.called
