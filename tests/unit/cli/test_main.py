"""Unit tests for Hexaqual Typer CLI entrypoint."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from hexaqual.cli.main import app

runner = CliRunner()


def test_cli_version() -> None:
    """Test hexaqual version subcommand."""
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "0.2.1" in res.stdout


def test_cli_check_invokes_runner() -> None:
    """Test hexaqual check subcommand delegates to sanity check runner."""
    with patch("hexaqual.commands.sanity_check.run_sanity_check", return_value=0) as mock_run:
        res = runner.invoke(app, ["check", "--skip-tests"])
        assert res.exit_code == 0
        assert mock_run.called


def test_cli_sanity_alias_invokes_runner() -> None:
    """Test hexaqual sanity alias delegates to sanity check runner."""
    with patch("hexaqual.commands.sanity_check.run_sanity_check", return_value=0) as mock_run:
        res = runner.invoke(app, ["sanity", "--skip-tests"])
        assert res.exit_code == 0
        assert mock_run.called


def test_cli_statements_help() -> None:
    """Test statements command group help."""
    res = runner.invoke(app, ["statements", "--help"])
    assert res.exit_code == 0
    assert "Audit and format __all__ statements" in res.stdout


def test_cli_parity_help() -> None:
    """Test parity command group help."""
    res = runner.invoke(app, ["parity", "--help"])
    assert res.exit_code == 0
    assert "Audit test symmetry and optional extras parity" in res.stdout


def test_cli_test_help() -> None:
    """Test test command group help."""
    res = runner.invoke(app, ["test", "--help"])
    assert res.exit_code == 0
    assert "Test execution, coverage audits" in res.stdout


def test_cli_mutate_help() -> None:
    """Test mutate command group help."""
    res = runner.invoke(app, ["mutate", "--help"])
    assert res.exit_code == 0
    assert "Mutation testing execution" in res.stdout


def test_cli_release_help() -> None:
    """Test release command group help."""
    res = runner.invoke(app, ["release", "--help"])
    assert res.exit_code == 0
    assert "Distribution package building" in res.stdout


def test_cli_gh_help() -> None:
    """Test gh command group help."""
    res = runner.invoke(app, ["gh", "--help"])
    assert res.exit_code == 0
    assert "GitHub repository, PR, and security" in res.stdout


def test_cli_docs_help() -> None:
    """Test docs command group help."""
    res = runner.invoke(app, ["docs", "--help"])
    assert res.exit_code == 0
    assert "Documentation generation and verification" in res.stdout


def test_cli_statements_check() -> None:
    """Test statements check subcommand."""
    with patch("hexaqual.utils.all_statements.check_file_all", return_value=[]):
        res = runner.invoke(app, ["statements", "check"])
        assert res.exit_code == 0


def test_cli_parity_test() -> None:
    """Test parity test subcommand."""
    with (
        patch("hexaqual.utils.test_parity.check_test_directories_inits", return_value=[]),
        patch("hexaqual.utils.test_parity.check_src_to_test_symmetry", return_value=[]),
    ):
        res = runner.invoke(app, ["parity", "test"])
        assert res.exit_code == 0


def test_cli_docs_usage() -> None:
    """Test docs usage subcommand."""
    from unittest.mock import MagicMock

    from hexaqual.domain.generators import UsageDocsReport

    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = UsageDocsReport(is_valid=True, up_to_date_files=("USAGE.md",))
    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        res = runner.invoke(app, ["docs", "usage", "--check"])
        assert res.exit_code == 0
