"""Standardized CLI option factories and formatting resolvers.

Notes/Architectural Intent:
    Centralizes option definitions and output formatting rules across all CLI entrypoints.
    Provides automatic pipe-detection when format is 'auto' so stdout streams cleanly into
    jq, grep, or file redirections.
"""

from __future__ import annotations

import os
import sys
from enum import Enum, StrEnum
from typing import Any

import typer


class OutputFormat(StrEnum):
    """Supported output presentation formats for CLI diagnostic commands."""

    AUTO = "auto"
    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN = "plain"
    RICH = "rich"
    TABLE = "table"


def resolve_format(
    format_type: str | OutputFormat,
    default_tty: str = "table",
    default_pipe: str = "json",
) -> str:
    """Resolve an output format string, handling auto-detection for pipes.

    Args:
        format_type: The format chosen by user or default ('auto', 'table', 'json', etc.).
        default_tty: Default format when connected to a terminal.
        default_pipe: Default format when stdout is piped/redirected.

    Returns:
        Normalized format string (e.g. 'table', 'json', 'rich').

    Notes/Architectural Intent:
        When format_type is 'auto', inspects sys.stdout.isatty() to choose between
        structured machine-readable format for pipelines or visual format for humans.
    """
    raw = format_type.value if isinstance(format_type, Enum) else str(format_type).lower().strip()
    if raw == OutputFormat.AUTO.value:
        if not sys.stdout.isatty():
            return default_pipe
        return default_tty
    return raw


def format_option(
    default: str = "table",
    help_text: str = "Output presentation format (table, json, markdown, rich, plain, auto).",
) -> Any:
    """Construct a standardized Typer option for format selection.

    Args:
        default: Default format option value.
        help_text: Help string to render in CLI usage catalogs.

    Returns:
        Configured Typer Option specification.

    Notes/Architectural Intent:
        Standardizes '-f' / '--format' flag across all Hexaqual CLI commands.
    """
    return typer.Option(default, "-f", "--format", help=help_text)


def summary_option(
    help_text: str = "Append report directly to $GITHUB_STEP_SUMMARY.",
) -> Any:
    """Construct a standardized Typer option for appending step summaries.

    Args:
        help_text: Help string to render in CLI usage catalogs.

    Returns:
        Configured Typer Option specification.

    Notes/Architectural Intent:
        Standardizes '-s' / '--summary' (or '--step-summary') flag for GitHub Actions
        markdown job summaries across all Hexaqual CLI commands.
    """
    return typer.Option(False, "-s", "--summary", help=help_text)


def append_step_summary(content: str) -> bool:
    """Append Markdown content to the file specified in $GITHUB_STEP_SUMMARY if set.

    Args:
        content: The Markdown string to append.

    Returns:
        True if content was written to $GITHUB_STEP_SUMMARY, False otherwise.

    Notes/Architectural Intent:
        Encapsulates safe step summary generation in CI environments without
        crashing or raising errors when running locally outside of GitHub Actions.
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return False
    try:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(f"\n{content.strip()}\n")
        return True
    except OSError:
        return False


def is_interactive_terminal() -> bool:
    """Determine whether standard output is connected to an interactive TTY.

    Returns:
        True if running in an interactive terminal with TTY attached to stdin/stdout;
        False if output is piped, redirected, running in CI, or headless.

    Notes/Architectural Intent:
        Prevents infinite polling loops in automated subagents, background jobs,
        and headless CI environments while respecting HEXAQUAL_FORCE_WATCH=1.
    """
    if os.environ.get("HEXAQUAL_FORCE_WATCH", "").lower() in ("1", "true", "yes"):
        return True

    if os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true":
        return False

    return sys.stdout.isatty() and sys.stdin.isatty()


__all__ = [
    "append_step_summary",
    "format_option",
    "is_interactive_terminal",
    "OutputFormat",
    "resolve_format",
    "summary_option",
]
