"""Unit tests for Hexaqual Typer CLI entrypoint."""

from __future__ import annotations

from typer.testing import CliRunner

from hexaqual.cli.main import app

runner = CliRunner()


def test_cli_version() -> None:
    """Test hexaqual version subcommand."""
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "0.0.0" in res.stdout


def test_cli_check() -> None:
    """Test hexaqual check subcommand."""
    res = runner.invoke(app, ["check"])
    assert res.exit_code == 0
    assert "Sanity Pipeline" in res.stdout
