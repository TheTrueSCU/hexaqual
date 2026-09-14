"""CLI subcommands for USAGE.md documentation generation and freshness verification.

Notes/Architectural Intent:
    Driving adapter exposing documentation generation and validation subcommands,
    unrolling the complete command hierarchy into standardized Markdown catalogs.
"""

from __future__ import annotations

from pathlib import Path

import typer

__all__ = [
    "docs_app",
    "docs_usage",
]

docs_app = typer.Typer(
    name="docs",
    help="Documentation generation and verification.",
    no_args_is_help=True,
)


@docs_app.command("usage")
def docs_usage(
    check_only: bool = typer.Option(False, "--check", help="Verify USAGE.md is up to date."),
    fix: bool = typer.Option(False, "--fix", help="Regenerate USAGE.md."),
    package: str | None = typer.Option(None, "-p", "--package", help="Target package."),
    root: Path | None = typer.Option(None, "--root", help="Workspace root directory."),
) -> None:
    """Generate or verify USAGE.md documentation catalogs.

    Args:
        check_only: Check freshness without writing files.
        fix: Regenerate USAGE.md on disk.
        package: Target package name.
        root: Workspace root directory.

    Raises:
        typer.Exit: If documentation is stale in check mode.

    Notes/Architectural Intent:
        Driving adapter executing usage documentation generator.
    """
    from hexaqual.adapters.presenters.generators import create_generator_presenter
    from hexaqual.domain.generators import GenerateUsageDocsCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    repo_root = root or get_repo_root()
    bus = create_governance_bus(repo_root=repo_root)
    cmd = GenerateUsageDocsCommand(
        package=package,
        affected_only=False,
        check_only=check_only,
        fix=fix or (not check_only),
    )
    rep = bus.dispatch(cmd)
    presenter = create_generator_presenter("table")
    exit_code = presenter.present_usage_docs(rep) or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
