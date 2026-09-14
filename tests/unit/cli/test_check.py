"""Unit tests for Hexaqual check and sanity CLI commands."""

from __future__ import annotations

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexaqual.cli.check import register_check_commands

runner = CliRunner()


def test_register_check_commands() -> None:
    """Test registering check commands on a fresh Typer app."""
    test_app = typer.Typer()
    register_check_commands(test_app)

    with patch("hexaqual.commands.sanity_check.run_sanity_check", return_value=0) as mock_run:
        res = runner.invoke(test_app, ["check", "--skip-tests"])
        assert res.exit_code == 0
        assert mock_run.called


def test_sanity_alias_command() -> None:
    """Test sanity alias forwards to check command."""
    test_app = typer.Typer()
    register_check_commands(test_app)

    with patch("hexaqual.commands.sanity_check.run_sanity_check", return_value=0) as mock_run:
        res = runner.invoke(test_app, ["sanity", "--skip-tests"])
        assert res.exit_code == 0
        assert mock_run.called


def test_check_failure_exit_code() -> None:
    """Test non-zero exit code on sanity check failure."""
    test_app = typer.Typer()
    register_check_commands(test_app)

    with patch("hexaqual.commands.sanity_check.run_sanity_check", return_value=1):
        res = runner.invoke(test_app, ["check", "--skip-tests"])
        assert res.exit_code == 1
