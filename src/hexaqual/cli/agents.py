"""CLI subcommands for managing and synchronizing universal .agents guardrails.

Notes/Architectural Intent:
    Driving adapter exposing sync, check, and list subcommands for universal
    rules, workflows, and skills packaged inside hexaqual.
"""

from __future__ import annotations

from pathlib import Path

import typer

from hexaqual.commands.agents import (
    check_agents_command,
    list_agents_command,
    sync_agents_command,
)

__all__ = [
    "agents_app",
    "agents_check",
    "agents_list",
    "agents_sync",
]

agents_app = typer.Typer(
    name="agents",
    help="Manage, synchronize, and verify universal .agents guardrails.",
    no_args_is_help=True,
)


@agents_app.command("sync")
def agents_sync(
    target: Path | None = typer.Option(
        None, "--target", "-t", help="Target repository root or .agents directory."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate synchronization without writing files to disk."
    ),
    format_type: str = typer.Option(
        "table", "--format", "-f", help="Output format (table, json, markdown)."
    ),
) -> None:
    """Synchronize universal rules, workflows, and skills to target repository.

    Args:
        target: Optional path to the repository root or .agents directory.
        dry_run: Whether to simulate changes without writing to disk.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If synchronization fails.

    Notes/Architectural Intent:
        Overwrites managed assets (prefixed with hexaqual-) while strictly preserving
        unmanaged local repository rules and workflows (e.g. hexaqueue-*, hexaflow-*).
    """
    exit_code = sync_agents_command(
        target_dir=target,
        dry_run=dry_run,
        format_type=format_type,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@agents_app.command("check")
def agents_check(
    target: Path | None = typer.Option(
        None, "--target", "-t", help="Target repository root or .agents directory."
    ),
    format_type: str = typer.Option(
        "table", "--format", "-f", help="Output format (table, json, markdown)."
    ),
) -> None:
    """Check whether managed .agents assets in target repository match hexaqual.

    Args:
        target: Optional path to the repository root or .agents directory.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If drift or missing assets are detected (exit code 1).

    Notes/Architectural Intent:
        Deterministic pre-commit and CI verification gate.
    """
    exit_code = check_agents_command(
        target_dir=target,
        format_type=format_type,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@agents_app.command("list")
def agents_list(
    format_type: str = typer.Option(
        "table", "--format", "-f", help="Output format (table, json, markdown)."
    ),
) -> None:
    """List all universal agent rules, workflows, and skills bundled in hexaqual.

    Args:
        format_type: Output presentation format.

    Raises:
        typer.Exit: If catalog rendering fails.

    Notes/Architectural Intent:
        Informational inspection command for developers and AI agents.
    """
    exit_code = list_agents_command(format_type=format_type)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
