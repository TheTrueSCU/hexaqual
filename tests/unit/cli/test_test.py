"""Unit tests for Hexaqual test execution CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from hexaqual.cli.test import test_app as cli_test_app

runner = CliRunner()


def test_test_help() -> None:
    """Test test help output."""
    res = runner.invoke(cli_test_app, ["--help"])
    assert res.exit_code == 0
    assert "Test execution, coverage audits" in res.stdout


def test_test_run() -> None:
    """Test test run command delegates to pytest runner."""
    with patch("hexaqual.commands.pytest_runner.run_main", return_value=0) as mock_run:
        res = runner.invoke(
            cli_test_app,
            [
                "run",
                "-p",
                "core",
                "-e",
                "demo",
                "-a",
                "-A",
                "-U",
                "-P",
                "--with-context",
                "--",
                "--verbose",
            ],
        )
        assert res.exit_code == 0
        assert mock_run.called
        call_argv = mock_run.call_args[0][0]
        assert "-p" in call_argv
        assert "core" in call_argv
        assert "-e" in call_argv
        assert "demo" in call_argv
        assert "-a" in call_argv
        assert "-A" in call_argv
        assert "-U" in call_argv
        assert "-P" in call_argv
        assert "--with-context" in call_argv
        assert "--verbose" in call_argv


def test_test_boundary() -> None:
    """Test test boundary audit command."""
    with patch("hexaqual.commands.coverage.boundary_audit_main", return_value=0) as mock_audit:
        res = runner.invoke(cli_test_app, ["boundary"])
        assert res.exit_code == 0
        assert mock_audit.called


def test_test_impact() -> None:
    """Test test impact command."""
    with patch("hexaqual.commands.coverage.impact_main", return_value=0) as mock_impact:
        res = runner.invoke(cli_test_app, ["impact"])
        assert res.exit_code == 0
        assert mock_impact.called


def test_test_redundancy() -> None:
    """Test test redundancy audit command."""
    with patch("hexaqual.commands.coverage.redundancy_audit_main", return_value=0) as mock_red:
        res = runner.invoke(cli_test_app, ["redundancy"])
        assert res.exit_code == 0
        assert mock_red.called
