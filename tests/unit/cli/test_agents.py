"""Unit tests for agents CLI subcommands.

Notes/Architectural Intent:
    Validates typer CLI routing, flag handling, and exit code propagation for
    agents sync, check, and list commands.
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from hexaqual.cli.agents import agents_app

runner = CliRunner()


def test_agents_help() -> None:
    """Verify agents CLI help displays available commands.

    Notes/Architectural Intent:
        Confirms command catalog help documentation.
    """
    res = runner.invoke(agents_app, ["--help"])
    exit_code = res.exit_code
    stdout = res.stdout

    assert exit_code == 0
    assert "sync" in stdout
    assert "check" in stdout
    assert "list" in stdout


def test_agents_sync_invocation() -> None:
    """Verify agents sync command delegates to command handler.

    Notes/Architectural Intent:
        Asserts sync_agents_command is called and return code 0 propagates.
    """
    with patch("hexaqual.cli.agents.sync_agents_command", return_value=0) as mock_sync:
        res = runner.invoke(agents_app, ["sync", "--dry-run", "-f", "json"])
        exit_code = res.exit_code

        assert exit_code == 0
        assert mock_sync.called is True


def test_agents_check_clean() -> None:
    """Verify agents check command exits with code 0 when clean.

    Notes/Architectural Intent:
        Validates success exit code propagation.
    """
    with patch("hexaqual.cli.agents.check_agents_command", return_value=0):
        res = runner.invoke(agents_app, ["check"])
        exit_code = res.exit_code
        assert exit_code == 0


def test_agents_check_drift_detected() -> None:
    """Verify agents check command exits with code 1 when drift is detected.

    Notes/Architectural Intent:
        Validates non-zero exit code on drift.
    """
    with patch("hexaqual.cli.agents.check_agents_command", return_value=1):
        res = runner.invoke(agents_app, ["check"])
        exit_code = res.exit_code
        assert exit_code == 1


def test_agents_list_invocation() -> None:
    """Verify agents list command delegates to command handler.

    Notes/Architectural Intent:
        Asserts list_agents_command is invoked.
    """
    with patch("hexaqual.cli.agents.list_agents_command", return_value=0) as mock_list:
        res = runner.invoke(agents_app, ["list", "-f", "markdown"])
        exit_code = res.exit_code

        assert exit_code == 0
        assert mock_list.called is True
