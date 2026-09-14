"""Sanity and verification commands for the Hexaqual CLI.

Notes/Architectural Intent:
    Driving adapter exposing the multi-stage quality sanity check pipeline,
    supporting both 'check' and legacy 'sanity' command entrypoints.
"""

from __future__ import annotations

import typer

__all__ = [
    "check",
    "register_check_commands",
    "sanity",
]


def check(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    examples: list[str] | None = typer.Option(None, "-e", "--example", help="Target example(s)."),
    all_targets: bool = typer.Option(False, "-a", "--all", help="Run across all packages."),
    fix: bool = typer.Option(False, "--fix", help="Automatically apply autofixes."),
    skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip pytest suites."),
    max_complexity: int = typer.Option(
        25, "-mx", "--max-complexity", help="Cognitive complexity ceiling."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
    files: list[str] | None = typer.Argument(None, help="Specific files or directories to verify."),
) -> None:
    """Execute the sanity check pipeline.

    Args:
        packages: Optional sequence of package names to audit.
        examples: Optional sequence of example project names to audit.
        all_targets: Whether to audit all packages unconditionally.
        fix: Whether to auto-apply formatting and lint fixes.
        skip_tests: Whether to skip test suites.
        max_complexity: Cognitive complexity ceiling.
        format_type: Output presentation format.
        files: Optional explicit file or directory targets.

    Raises:
        typer.Exit: If any sanity checks fail.

    Notes/Architectural Intent:
        Primary entrypoint for local pre-commit verification and CI pipelines.
    """
    from hexaqual.commands.sanity_check import resolve_targets, run_sanity_check
    from hexaqual.utils.workspace import get_repo_root

    repo_root = get_repo_root()
    targets = resolve_targets(
        packages=packages,
        examples=examples,
        files=files or [],
        all_targets=all_targets,
        repo_root=repo_root,
    )
    exit_code = run_sanity_check(
        targets=targets,
        repo_root=repo_root,
        fix=fix,
        skip_tests=skip_tests,
        max_complexity=max_complexity,
        format_type=format_type,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def sanity(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    examples: list[str] | None = typer.Option(None, "-e", "--example", help="Target example(s)."),
    all_targets: bool = typer.Option(False, "-a", "--all", help="Run across all packages."),
    fix: bool = typer.Option(False, "--fix", help="Automatically apply autofixes."),
    skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip pytest suites."),
    max_complexity: int = typer.Option(
        25, "-mx", "--max-complexity", help="Cognitive complexity ceiling."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
    files: list[str] | None = typer.Argument(None, help="Specific files or directories to verify."),
) -> None:
    """Execute the sanity check pipeline (alias for 'check').

    Args:
        packages: Optional sequence of package names to audit.
        examples: Optional sequence of example project names to audit.
        all_targets: Whether to audit all packages unconditionally.
        fix: Whether to auto-apply formatting and lint fixes.
        skip_tests: Whether to skip test suites.
        max_complexity: Cognitive complexity ceiling.
        format_type: Output presentation format.
        files: Optional explicit file or directory targets.

    Raises:
        typer.Exit: If any sanity checks fail.

    Notes/Architectural Intent:
        Convenience alias matching legacy sanity-check naming.
    """
    check(
        packages=packages,
        examples=examples,
        all_targets=all_targets,
        fix=fix,
        skip_tests=skip_tests,
        max_complexity=max_complexity,
        format_type=format_type,
        files=files,
    )


def register_check_commands(app: typer.Typer) -> None:
    """Register check and sanity commands on the root Typer application.

    Args:
        app: Target root Typer application.

    Notes/Architectural Intent:
        Attaches top-level root commands without introducing sub-app nesting.
    """
    app.command("check")(check)
    app.command("sanity")(sanity)
