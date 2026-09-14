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
    "docs_publish",
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


@docs_app.command("publish")
def docs_publish(
    manifest: Path | None = typer.Option(
        None, "-m", "--manifest", help="Path to articles manifest or directory."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate without making live HTTP requests."
    ),
    publish: bool = typer.Option(
        False, "--publish", help="Publish live articles (otherwise draft upload mode)."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
) -> None:
    """Syndicate or publish documentation articles to DEV.to / Medium.

    Args:
        manifest: Optional path to article markdown files.
        dry_run: Validate without network writes.
        publish: Publish live articles.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If publication fails.

    Notes/Architectural Intent:
        Driving adapter dispatching PublishMediumArticlesCommand across the governance bus.
    """
    from hexaqual.adapters.presenters.refactoring import create_refactoring_presenter
    from hexaqual.domain.refactoring import PublishMediumArticlesCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    root = get_repo_root()
    bus = create_governance_bus(repo_root=root)
    presenter = create_refactoring_presenter(format_type)
    cmd = PublishMediumArticlesCommand(
        manifest_path=manifest,
        dry_run=dry_run,
        publish=publish,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_medium_publish(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
