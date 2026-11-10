"""Unit tests for standardized CLI options and step summary helpers."""

from __future__ import annotations

import os
from unittest.mock import patch

from hexaqual.cli.options import (
    OutputFormat,
    append_step_summary,
    format_option,
    is_interactive_terminal,
    resolve_format,
    summary_option,
)


def test_append_step_summary_when_env_not_set() -> None:
    """Verify append_step_summary safely returns False when GITHUB_STEP_SUMMARY is not set."""
    with patch.dict(os.environ, {}, clear=True):
        res = append_step_summary("### Markdown Header")
        assert res is False


def test_append_step_summary_writes_to_file(tmp_path) -> None:
    """Verify append_step_summary appends Markdown to the configured path."""
    summary_file = tmp_path / "step_summary.md"
    summary_file.write_text("# Initial Summary\n", encoding="utf-8")

    with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
        res = append_step_summary("### Appended Section")
        assert res is True

    content = summary_file.read_text(encoding="utf-8")
    assert "# Initial Summary" in content
    assert "### Appended Section" in content


def test_append_step_summary_handles_os_error() -> None:
    """Verify append_step_summary returns False when file writing encounters an OSError."""
    with (
        patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/dummy/summary.md"}),
        patch("builtins.open", side_effect=OSError("Read-only filesystem")),
    ):
        res = append_step_summary("### Appended Section")
        assert res is False


def test_summary_option_factory() -> None:
    """Verify summary_option returns a valid Typer option default."""
    opt = summary_option("Custom summary help")
    assert opt.default is False
    assert opt.help == "Custom summary help"


def test_is_interactive_terminal_force_watch() -> None:
    """Verify is_interactive_terminal returns True when HEXAQUAL_FORCE_WATCH is enabled."""
    with patch.dict(os.environ, {"HEXAQUAL_FORCE_WATCH": "1"}):
        res = is_interactive_terminal()
        assert res is True


def test_is_interactive_terminal_ci_environment() -> None:
    """Verify is_interactive_terminal returns False in CI environment."""
    with patch.dict(os.environ, {"HEXAQUAL_FORCE_WATCH": "0", "CI": "true"}):
        res = is_interactive_terminal()
        assert res is False


def test_is_interactive_terminal_tty() -> None:
    """Verify is_interactive_terminal returns True when both stdout and stdin are tty."""
    with (
        patch.dict(os.environ, {"HEXAQUAL_FORCE_WATCH": "0"}, clear=True),
        patch("sys.stdout.isatty", return_value=True),
        patch("sys.stdin.isatty", return_value=True),
    ):
        res = is_interactive_terminal()
        assert res is True


def test_resolve_format_explicit() -> None:
    """Verify resolve_format preserves explicit format string."""
    res = resolve_format("json")
    assert res == "json"


def test_resolve_format_auto_tty() -> None:
    """Verify resolve_format returns default_tty when stdout isatty."""
    with patch("sys.stdout.isatty", return_value=True):
        res = resolve_format(OutputFormat.AUTO, default_tty="table", default_pipe="json")
        assert res == "table"


def test_resolve_format_auto_pipe() -> None:
    """Verify resolve_format returns default_pipe when stdout is not a tty."""
    with patch("sys.stdout.isatty", return_value=False):
        res = resolve_format(OutputFormat.AUTO, default_tty="table", default_pipe="json")
        assert res == "json"


def test_format_option_factory() -> None:
    """Verify format_option returns configured Typer option."""
    opt = format_option("json", "Format help")
    assert opt.default == "json"
    assert opt.help == "Format help"
