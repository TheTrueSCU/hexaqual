"""CLI subcommands for managing repository Git lifecycle hooks.

Notes/Architectural Intent:
    Driving adapter exposing install, uninstall, check, and commit-msg commands
    for Git hooks adhering to OpenSSF Scorecard Gold standards and hexagonal boundaries.
"""

from __future__ import annotations

from pathlib import Path

import typer

from hexaqual.adapters.hooks.service import (
    check_hooks_command,
    install_hooks_command,
    uninstall_hooks_command,
    validate_commit_msg_command,
)
from hexaqual.domain.hooks import HookInstallMode

__all__ = [
    "hooks_app",
    "hooks_check",
    "hooks_commit_msg",
    "hooks_install",
    "hooks_uninstall",
]

hooks_app = typer.Typer(
    name="hooks",
    help="Manage, install, and verify Git lifecycle hooks and commit message standards.",
    no_args_is_help=True,
)


@hooks_app.command("install")
def hooks_install(
    target: Path | None = typer.Option(
        None, "--target", "-t", help="Target repository root directory."
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        "-m",
        help="Installation strategy: 'auto' (pre-commit if available, else native), 'pre-commit', or 'native'.",
    ),
) -> None:
    """Install Git lifecycle hooks (pre-commit, commit-msg, pre-push, post-merge, post-checkout).

    Args:
        target: Optional path to repository root (defaults to CWD).
        mode: Installation mode ('auto', 'pre-commit', or 'native').

    Raises:
        typer.Exit: If hook installation fails.

    Notes/Architectural Intent:
        Ensures all 5 critical lifecycle stages are active to prevent broken builds,
        unsigned commits, and out-of-sync agent rules.
    """
    try:
        install_mode = HookInstallMode(mode.lower())
    except ValueError:
        valid_modes = ", ".join(m.value for m in HookInstallMode)
        typer.secho(
            f"Invalid mode '{mode}'. Choose from: {valid_modes}.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2) from None

    exit_code = install_hooks_command(target_dir=target, mode=install_mode)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@hooks_app.command("uninstall")
def hooks_uninstall(
    target: Path | None = typer.Option(
        None, "--target", "-t", help="Target repository root directory."
    ),
) -> None:
    """Uninstall managed Git hooks from the repository.

    Args:
        target: Optional path to repository root (defaults to CWD).

    Raises:
        typer.Exit: If uninstallation encounters an error.

    Notes/Architectural Intent:
        Safely removes managed native scripts and pre-commit hook wrappers.
    """
    exit_code = uninstall_hooks_command(target_dir=target)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@hooks_app.command("check")
def hooks_check(
    target: Path | None = typer.Option(
        None, "--target", "-t", help="Target repository root directory."
    ),
) -> None:
    """Check the installation and management status of all Git hook stages.

    Args:
        target: Optional path to repository root (defaults to CWD).

    Raises:
        typer.Exit: If any required hook is missing.

    Notes/Architectural Intent:
        Verifies all 5 stages and reports manager types in a terminal table.
    """
    exit_code = check_hooks_command(target_dir=target)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@hooks_app.command("commit-msg")
def hooks_commit_msg(
    commit_msg_file: Path | None = typer.Argument(
        None,
        help="Path to commit message file (e.g. .git/COMMIT_EDITMSG). Reads stdin if omitted.",
    ),
    no_dco: bool = typer.Option(
        False,
        "--no-dco",
        help="Disable Developer Certificate of Origin (Signed-off-by) verification.",
    ),
    no_conventional: bool = typer.Option(
        False,
        "--no-conventional",
        help="Disable Conventional Commits format verification.",
    ),
) -> None:
    """Validate a commit message against Conventional Commits and OpenSSF DCO standards.

    Args:
        commit_msg_file: Path to commit message file (provided by Git during commit-msg).
        no_dco: Whether to bypass DCO Signed-off-by trailer check.
        no_conventional: Whether to bypass Conventional Commits syntax check.

    Raises:
        typer.Exit: If commit message fails verification.

    Notes/Architectural Intent:
        Enforces OpenSSF Scorecard Gold DCO compliance and structured semantic commits.
    """
    exit_code = validate_commit_msg_command(
        msg_file=commit_msg_file,
        require_dco=not no_dco,
        require_conventional=not no_conventional,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
