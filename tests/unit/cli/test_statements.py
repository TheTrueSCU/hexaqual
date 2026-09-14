"""Unit tests for Hexaqual statements CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from hexaqual.cli.statements import statements_app

runner = CliRunner()


def test_statements_help() -> None:
    """Test statements help output."""
    res = runner.invoke(statements_app, ["--help"])
    assert res.exit_code == 0
    assert "Audit and format __all__ statements" in res.stdout


def test_statements_check_clean() -> None:
    """Test statements check with zero errors."""
    with patch("hexaqual.utils.all_statements.check_file_all", return_value=[]):
        res = runner.invoke(statements_app, ["check"])
        assert res.exit_code == 0


def test_statements_check_failure() -> None:
    """Test statements check with violations raises Exit."""
    with patch(
        "hexaqual.utils.all_statements.check_file_all", return_value=["Error: unsorted __all__"]
    ):
        res = runner.invoke(statements_app, ["check"])
        assert res.exit_code == 1


def test_statements_fix() -> None:
    """Test statements fix command."""
    with patch("hexaqual.utils.all_statements.fix_file_all", return_value=1):
        res = runner.invoke(statements_app, ["fix"])
        assert res.exit_code == 0
