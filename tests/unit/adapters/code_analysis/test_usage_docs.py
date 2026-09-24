"""Unit tests for usage_docs code analysis adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.adapters.code_analysis.usage_docs import (
    UsageDocsAnalyzer,
    clean_help_output,
    extract_command_help,
    extract_subcommands_from_help,
)


def test_clean_help_output() -> None:
    """Verify ANSI escape stripping and usage extraction."""
    raw = "\x1b[31mUsage:\x1b[0m tool [OPTIONS] COMMAND [ARGS]...\n\nCommands:\n  run  Run tool"
    cleaned = clean_help_output(raw)
    assert "\x1b" not in cleaned
    assert "Usage:" in cleaned
    assert "Commands:" in cleaned


def test_extract_subcommands_from_help() -> None:
    """Verify parsing subcommands from help output."""
    help_text = """
Usage: app [OPTIONS] COMMAND [ARGS]...

Commands:
  build    Build package artifacts
  publish  Publish packages to PyPI
"""
    subcmds = extract_subcommands_from_help(help_text)
    assert "build" in subcmds
    assert "publish" in subcmds


@patch("subprocess.run")
def test_extract_command_help(mock_run: MagicMock) -> None:
    """Verify execution of subprocess and output capture."""
    mock_run.return_value = MagicMock(
        stdout="Usage: cli [OPTIONS]\n",
        stderr="",
    )
    result = extract_command_help(["my-cli"])
    assert "Usage: cli" in result


def test_usage_docs_analyzer(tmp_path: Path) -> None:
    """Verify UsageDocsAnalyzer verifying usage files."""
    analyzer = UsageDocsAnalyzer()
    usage_file = tmp_path / "USAGE.md"
    usage_file.write_text("# Usage\n\nContent\n", encoding="utf-8")

    in_sync, diff = analyzer.verify_usage_file(usage_file, "# Usage\n\nContent\n")
    assert in_sync is True
    assert diff == ""

    out_of_sync, diff2 = analyzer.verify_usage_file(usage_file, "# Usage\n\nDifferent\n")
    assert out_of_sync is False
    assert "-Content" in diff2
