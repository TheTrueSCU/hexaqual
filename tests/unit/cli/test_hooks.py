"""Unit tests for hooks CLI subcommands.

Notes/Architectural Intent:
    Validates Typer CLI routing, option parsing, and exit code propagation
    for hooks install, uninstall, check, and commit-msg commands.
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from hexaqual.cli.hooks import hooks_app

runner = CliRunner()


def test_hooks_help() -> None:
    """Verify hooks CLI help displays available commands."""
    res = runner.invoke(hooks_app, ["--help"])
    exit_code = res.exit_code
    stdout = res.stdout

    assert exit_code == 0
    assert "install" in stdout
    assert "uninstall" in stdout
    assert "check" in stdout
    assert "commit-msg" in stdout


def test_hooks_install_invocation() -> None:
    """Verify hooks install delegates to service handler."""
    with patch("hexaqual.cli.hooks.install_hooks_command", return_value=0) as mock_cmd:
        res = runner.invoke(hooks_app, ["install", "--mode", "native"])
        exit_code = res.exit_code

        assert exit_code == 0
        assert mock_cmd.called is True


def test_hooks_install_invalid_mode() -> None:
    """Verify hooks install rejects invalid mode option."""
    res = runner.invoke(hooks_app, ["install", "--mode", "invalid_mode"])
    exit_code = res.exit_code

    assert exit_code == 2
    assert "Invalid mode" in res.stdout


def test_hooks_uninstall_invocation() -> None:
    """Verify hooks uninstall delegates to service handler."""
    with patch("hexaqual.cli.hooks.uninstall_hooks_command", return_value=0) as mock_cmd:
        res = runner.invoke(hooks_app, ["uninstall"])
        exit_code = res.exit_code

        assert exit_code == 0
        assert mock_cmd.called is True


def test_hooks_check_invocation() -> None:
    """Verify hooks check delegates to service handler."""
    with patch("hexaqual.cli.hooks.check_hooks_command", return_value=0) as mock_cmd:
        res = runner.invoke(hooks_app, ["check"])
        exit_code = res.exit_code

        assert exit_code == 0
        assert mock_cmd.called is True


def test_hooks_commit_msg_invocation() -> None:
    """Verify hooks commit-msg delegates to service handler."""
    with patch("hexaqual.cli.hooks.validate_commit_msg_command", return_value=0) as mock_cmd:
        res = runner.invoke(hooks_app, ["commit-msg", "--no-dco"])
        exit_code = res.exit_code

        assert exit_code == 0
        assert mock_cmd.called is True
