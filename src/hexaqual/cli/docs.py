"""CLI subcommands for USAGE.md documentation generation and freshness verification.

Notes/Architectural Intent:
    Driving adapter exposing documentation generation and validation subcommands,
    unrolling the complete command hierarchy into standardized Markdown catalogs.
"""

from __future__ import annotations

from pathlib import Path

import typer

from hexaqual.cli.options import format_option, resolve_format

__all__ = [
    "blog_app",
    "docs_app",
    "docs_blog_medium",
    "docs_drift",
    "docs_links",
    "docs_publish",
    "docs_usage",
]

docs_app = typer.Typer(
    name="docs",
    help="Documentation generation and verification.",
    no_args_is_help=True,
)

blog_app = typer.Typer(
    name="blog",
    help="Blog publishing and Medium syndication commands.",
    no_args_is_help=True,
)


@blog_app.command("medium")
def docs_blog_medium(
    slug: str = typer.Argument(
        ..., help="Article filename stem (e.g. 'ai-guardrails-manifesto') or path."
    ),
    url: str = typer.Argument(..., help="Syndicated Medium post URL."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without writing files."),
    root: Path | None = typer.Option(None, "--root", help="Workspace root directory."),
) -> None:
    """Record canonical syndicated Medium URL for an article.

    Args:
        slug: Article slug identifier.
        url: Canonical syndicated Medium post URL.
        dry_run: Validate without disk modifications.
        root: Workspace root directory.

    Notes/Architectural Intent:
        Driving adapter updating article front matter with medium_url and
        regenerating the syndication registry table in docs/medium/README.md.
    """
    from hexaqual.adapters.publishers.devto import record_medium_url
    from hexaqual.infra.workspace import get_repo_root

    repo_root = root or get_repo_root()
    record_medium_url(slug, url, repo_root=repo_root, dry_run=dry_run)
    typer.secho(f"✓ Recorded Medium URL for {slug}: {url}", fg=typer.colors.GREEN)


docs_app.add_typer(blog_app)


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
    from hexaqual.infra.workspace import get_repo_root

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


@docs_app.command("links")
def docs_links(
    path: Path | None = typer.Option(
        None, "-p", "--path", help="Directory or markdown file to scan for broken links."
    ),
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, json, markdown, rich, auto).",
    ),
    root: Path | None = typer.Option(None, "--root", help="Workspace root directory."),
) -> None:
    """Validate relative links and local anchors across documentation trees.

    Args:
        path: Path to markdown document or directory.
        format_type: Output presentation format.
        root: Workspace root directory.

    Raises:
        typer.Exit: If broken links are detected.

    Notes/Architectural Intent:
        Driving adapter scanning markdown files for dead links and missing anchors.
    """
    from hexaqual.adapters.code_analysis.doc_links import scan_doc_links
    from hexaqual.adapters.presenters.generators import create_generator_presenter
    from hexaqual.infra.workspace import get_repo_root

    repo_root = root or get_repo_root()
    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    presenter = create_generator_presenter(resolved_fmt)
    report = scan_doc_links(target_path=path, repo_root=repo_root)
    exit_code = presenter.present_doc_links(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@docs_app.command("drift")
def docs_drift(
    path: Path | None = typer.Argument(
        None, help="Specific markdown document or directory to audit."
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Automatically repair detected prose data drift."
    ),
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, json, markdown, auto).",
    ),
    root: Path | None = typer.Option(None, "--root", help="Workspace root directory."),
) -> None:
    """Audit documentation prose for data drift against codebase schemas and constants.

    Args:
        path: Path to markdown document or directory.
        fix: Whether to write repairs back to disk in-place.
        format_type: Output presentation format.
        root: Workspace root directory.

    Raises:
        typer.Exit: If un-remediated prose drift is detected.

    Notes/Architectural Intent:
        Driving adapter scanning documentation for version badge mismatches and
        monorepo package count drift ('The Lying Prose Linter').
    """
    from hexaqual.adapters.code_analysis.docs_drift import scan_docs_drift
    from hexaqual.adapters.presenters.generators import create_generator_presenter
    from hexaqual.infra.workspace import get_repo_root

    repo_root = root or get_repo_root()
    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    presenter = create_generator_presenter(resolved_fmt)
    report = scan_docs_drift(target_path=path, repo_root=repo_root, fix=fix)
    exit_code = presenter.present_doc_drift(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@docs_app.command("publish")
def docs_publish(
    slug: str | None = typer.Argument(
        None, help="Article filename stem (e.g. 'ai-guardrails-manifesto') or path."
    ),
    manifest: Path | None = typer.Option(
        None, "-m", "--manifest", help="Path to articles manifest or directory."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Validate without making live HTTP requests."
    ),
    publish: bool = typer.Option(
        False, "--publish", help="Publish live articles (otherwise draft upload mode)."
    ),
    all_drafts: bool = typer.Option(
        False, "--all-drafts", help="Upload all local articles without devto_id as drafts."
    ),
    status: bool = typer.Option(
        False, "--status", help="Show a status table of all articles and their publish state."
    ),
    sync_links: bool = typer.Option(
        False,
        "--sync-links",
        help="Re-resolve and update cross-links on DEV.to across all published articles.",
    ),
    medium_url: str | None = typer.Option(
        None, "--medium-url", help="Record the Medium URL for a slug after manual import."
    ),
    api_key: str | None = typer.Option(
        None, "--api-key", help="DEV.to API key (overrides DEVTO_API_KEY env var)."
    ),
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, json, markdown, auto).",
    ),
    root: Path | None = typer.Option(None, "--root", help="Workspace root directory."),
) -> None:
    """Syndicate or publish documentation articles to DEV.to / Medium.

    Args:
        slug: Article slug or path to process.
        manifest: Optional path to article markdown files.
        dry_run: Validate without network writes.
        publish: Publish live articles.
        all_drafts: Upload all unposted articles as drafts.
        status: Show status table.
        sync_links: Re-resolve cross-links across published articles.
        medium_url: Record syndicated Medium URL.
        api_key: DEV.to integration API key.
        format_type: Output presentation format.
        root: Workspace root directory.

    Raises:
        typer.Exit: If publication fails.

    Notes/Architectural Intent:
        Driving adapter dispatching PublishMediumArticlesCommand across the governance bus.
    """
    from hexaqual.adapters.presenters.refactoring import create_refactoring_presenter
    from hexaqual.domain.refactoring import PublishMediumArticlesCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.infra.workspace import get_repo_root

    repo_root = root or get_repo_root()
    bus = create_governance_bus(repo_root=repo_root)
    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    presenter = create_refactoring_presenter(resolved_fmt)
    cmd = PublishMediumArticlesCommand(
        slug=slug,
        manifest_path=manifest,
        dry_run=dry_run,
        publish=publish,
        all_drafts=all_drafts,
        status=status,
        sync_links=sync_links,
        medium_url=medium_url,
        api_key=api_key,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_medium_publish(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
