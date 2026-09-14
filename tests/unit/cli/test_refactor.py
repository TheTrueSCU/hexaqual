"""Unit tests for Hexaqual refactor CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.refactor import refactor_app

runner = CliRunner()


def test_refactor_help() -> None:
    """Test refactor help output."""
    res = runner.invoke(refactor_app, ["--help"])
    assert res.exit_code == 0
    assert "AST symbol alphabetization and Python code refactoring" in res.stdout


def test_refactor_alphabetize_success() -> None:
    """Test refactor alphabetize dispatches AlphabetizeCodeCommand across bus."""
    mock_bus = MagicMock()
    mock_report = MagicMock()
    mock_bus.dispatch.return_value = mock_report
    mock_pres = MagicMock()
    mock_pres.present_alphabetize.return_value = 0

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.refactoring.create_refactoring_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(refactor_app, ["alphabetize", "-p", "core", "--dry-run", "-f", "json"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.dry_run is True
        assert mock_pres.present_alphabetize.called


def test_refactor_alphabetize_failure() -> None:
    """Test refactor alphabetize handles non-zero presenter exit code."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_alphabetize.return_value = 1

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.refactoring.create_refactoring_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(refactor_app, ["alphabetize"])
        assert res.exit_code == 1


def test_refactor_rename_success() -> None:
    """Test refactor rename invokes handle_rename."""
    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.commands.rope.handle_rename") as mock_rename,
    ):
        res = runner.invoke(
            refactor_app,
            ["rename", "-f", "test.py", "-l", "10", "-c", "5", "-n", "new_name"],
        )
        assert res.exit_code == 0
        assert mock_rename.called


def test_refactor_rename_failure() -> None:
    """Test refactor rename handles exceptions cleanly."""
    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.commands.rope.handle_rename", side_effect=ValueError("Invalid offset")),
    ):
        res = runner.invoke(
            refactor_app,
            ["rename", "-f", "test.py", "-l", "10", "-c", "5", "-n", "new_name"],
        )
        assert res.exit_code == 1


def test_refactor_extract_success() -> None:
    """Test refactor extract invokes handle_extract_method."""
    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.commands.rope.handle_extract_method") as mock_extract,
    ):
        res = runner.invoke(
            refactor_app,
            ["extract", "-f", "test.py", "-s", "10", "-e", "15", "-n", "extracted_fn"],
        )
        assert res.exit_code == 0
        assert mock_extract.called


def test_refactor_extract_failure() -> None:
    """Test refactor extract handles exceptions cleanly."""
    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch(
            "hexaqual.commands.rope.handle_extract_method",
            side_effect=ValueError("Cannot extract"),
        ),
    ):
        res = runner.invoke(
            refactor_app,
            ["extract", "-f", "test.py", "-s", "10", "-e", "15", "-n", "extracted_fn"],
        )
        assert res.exit_code == 1


def test_refactor_move_success() -> None:
    """Test refactor move invokes handle_move_symbol."""
    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.commands.rope.handle_move_symbol") as mock_move,
    ):
        res = runner.invoke(
            refactor_app,
            ["move", "-s", "a.py", "-d", "b.py", "-l", "5", "-c", "0"],
        )
        assert res.exit_code == 0
        assert mock_move.called


def test_refactor_move_failure() -> None:
    """Test refactor move handles exceptions cleanly."""
    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.commands.rope.handle_move_symbol", side_effect=ValueError("Cannot move")),
    ):
        res = runner.invoke(
            refactor_app,
            ["move", "-s", "a.py", "-d", "b.py", "-l", "5", "-c", "0"],
        )
        assert res.exit_code == 1


def test_refactor_run_success() -> None:
    """Test refactor run invokes run_main."""
    with patch("hexaqual.commands.rope.run_main", return_value=0) as mock_run:
        res = runner.invoke(refactor_app, ["run", "--", "rename", "--help"])
        assert res.exit_code == 0
        assert mock_run.called


def test_refactor_run_failure() -> None:
    """Test refactor run handles non-zero exit code."""
    with patch("hexaqual.commands.rope.run_main", return_value=2):
        res = runner.invoke(refactor_app, ["run"])
        assert res.exit_code == 2
