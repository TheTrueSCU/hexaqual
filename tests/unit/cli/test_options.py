"""Unit tests for standardized CLI options and step summary helpers."""

from __future__ import annotations

import os
from unittest.mock import patch

from hexaqual.cli.options import (
    append_step_summary,
    summary_option,
)


def test_append_step_summary_when_env_not_set():
    """Verify append_step_summary safely returns False when GITHUB_STEP_SUMMARY is not set."""
    with patch.dict(os.environ, {}, clear=True):
        res = append_step_summary("### Markdown Header")
        assert res is False


def test_append_step_summary_writes_to_file(tmp_path):
    """Verify append_step_summary appends Markdown to the configured path."""
    summary_file = tmp_path / "step_summary.md"
    summary_file.write_text("# Initial Summary\n", encoding="utf-8")

    with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
        res = append_step_summary("### Appended Section")
        assert res is True

    content = summary_file.read_text(encoding="utf-8")
    assert "# Initial Summary" in content
    assert "### Appended Section" in content


def test_summary_option_factory():
    """Verify summary_option returns a valid Typer option default."""
    opt = summary_option("Custom summary help")
    assert opt.default is False
    assert opt.help == "Custom summary help"
