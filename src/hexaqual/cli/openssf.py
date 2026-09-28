"""CLI commands for OpenSSF Best Practices auditing and automation proposals.

Notes/Architectural Intent:
    Provides Typer subcommands under 'hexaqual openssf' for auditing badge criteria,
    evaluating local heuristics, generating chunked proposal URLs, and launching them
    in the default browser without persisting credentials.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from hexaqual.adapters.openssf import OpenSsfBadgeAdapter, OpenSsfScorecardAdapter
from hexaqual.cli.options import format_option, resolve_format
from hexaqual.domain.openssf import OpenSsfTier, ScorecardResult
from hexaqual.infra.openssf import (
    audit_project_posture,
    evaluate_local_heuristics,
    format_checklist_markdown,
    generate_checklist,
    resolve_local_repo_url,
    scaffold_document,
)

__all__ = [
    "openssf_app",
    "openssf_audit",
    "openssf_checklist",
    "openssf_propose",
    "openssf_scaffold",
    "openssf_scorecard",
]

openssf_app = typer.Typer(
    name="openssf",
    help="OpenSSF Best Practices badge auditing and proposal generation.",
    no_args_is_help=True,
)
console = Console()


def _resolve_project_id(adapter: OpenSsfBadgeAdapter, explicit_id: int | None) -> int:
    """Helper to resolve the numeric OpenSSF project ID."""
    if explicit_id is not None:
        return explicit_id

    repo_url = resolve_local_repo_url()
    if not repo_url:
        console.print(
            "[bold red]Error:[/bold red] Could not determine Git remote URL. Specify --project-id."
        )
        raise typer.Exit(code=1)

    project_id = adapter.search_project_by_repo(repo_url)
    if not project_id:
        console.print(
            f"[bold red]Error:[/bold red] No OpenSSF project found for repository {repo_url}.\n"
            f"Register your project at: https://www.bestpractices.dev/en/projects/new"
        )
        raise typer.Exit(code=1)

    return project_id


@openssf_app.command(name="audit")
def openssf_audit(
    tier: Annotated[
        str,
        typer.Option("--tier", "-t", help="Target badge tier: passing, silver, or gold."),
    ] = "passing",
    project_id: Annotated[
        int | None,
        typer.Option("--project-id", "-i", help="Explicit OpenSSF project numeric ID."),
    ] = None,
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, json, rich, auto).",
    ),
) -> None:
    """Audit OpenSSF Best Practices badge status and identify pending criteria."""
    adapter = OpenSsfBadgeAdapter()
    target_tier = OpenSsfTier(tier.lower())
    pid = _resolve_project_id(adapter, project_id)

    with console.status(f"[cyan]Auditing OpenSSF project {pid} ({target_tier.value})...[/cyan]"):
        project = adapter.fetch_project(pid)
        local_proposals = evaluate_local_heuristics(target_tier)
        result = audit_project_posture(project, target_tier, local_proposals)

    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    if resolved_fmt == "json":
        payload = {
            "project_id": pid,
            "name": result.project.name,
            "badge_level": result.project.badge_level,
            "score": result.project.tiered_percentage,
            "tier": target_tier.value,
            "proposals": [
                {
                    "criterion_id": p.criterion_id,
                    "status": p.status.value if hasattr(p.status, "value") else p.status,
                    "justification": p.justification,
                }
                for p in local_proposals
            ],
        }
        console.print_json(data=payload)
        return

    console.print(
        f"\n[bold]OpenSSF Project:[/bold] [cyan]{result.project.name}[/cyan] (ID: {pid}) | "
        f"[bold]Level:[/bold] {result.project.badge_level} | "
        f"[bold]Score:[/bold] {result.project.tiered_percentage}%\n"
    )

    table = Table(
        title=f"OpenSSF Best Practices Audit ({target_tier.value.title()})", title_justify="left"
    )
    table.add_column("Criterion", style="cyan", no_wrap=True)
    table.add_column("Current Status", style="magenta")
    table.add_column("Local Verdict", style="green")
    table.add_column("Evidence / Proposed Justification", style="dim")

    for prop in local_proposals:
        curr = project.criteria_statuses.get(prop.criterion_id, "?")
        verdict = f"[green]{prop.status}[/green]"
        table.add_row(prop.criterion_id, curr, verdict, prop.justification)

    console.print(table)

    if result.proposals:
        console.print(
            f"\n[bold yellow]Ready to Propose:[/bold yellow] {len(result.proposals)} criteria can be automatically set."
        )
        console.print(
            f"Run [bold cyan]hexaqual openssf propose --tier {target_tier.value}[/bold cyan] to generate 1-click URLs."
        )
    else:
        console.print(
            f"\n[bold green]✓ All evaluated {target_tier.value} criteria are satisfied![/bold green]"
        )


@openssf_app.command(name="propose")
def openssf_propose(
    tier: Annotated[
        str,
        typer.Option("--tier", "-t", help="Target badge tier: passing, silver, or gold."),
    ] = "passing",
    project_id: Annotated[
        int | None,
        typer.Option("--project-id", "-i", help="Explicit OpenSSF project numeric ID."),
    ] = None,
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open", "-o", help="Automatically launch pre-filled proposal URLs in default browser."
        ),
    ] = False,
    max_chunk: Annotated[
        int,
        typer.Option("--max-chunk", "-m", help="Maximum criteria per URL chunk."),
    ] = 12,
) -> None:
    """Generate 1-click automation proposal URLs for OpenSSF Best Practices."""
    adapter = OpenSsfBadgeAdapter()
    target_tier = OpenSsfTier(tier.lower())
    pid = _resolve_project_id(adapter, project_id)

    with console.status(f"[cyan]Evaluating proposals for project {pid}...[/cyan]"):
        project = adapter.fetch_project(pid)
        local_proposals = evaluate_local_heuristics(target_tier)
        result = audit_project_posture(project, target_tier, local_proposals)

    if not result.proposals:
        console.print(
            f"[bold green]✓ All evaluated {target_tier.value} criteria are already Met or N/A on the badge![/bold green]"
        )
        return

    urls = adapter.build_proposal_urls(pid, target_tier, result.proposals, max_per_chunk=max_chunk)

    console.print(
        f"\n[bold green]Generated {len(urls)} Proposal URL(s)[/bold green] for [cyan]{project.name}[/cyan] ({target_tier.value}):\n"
    )

    for idx, url in enumerate(urls, 1):
        console.print(f"[bold]Batch {idx}:[/bold] [link={url}]{url}[/link]\n")
        if open_browser:
            console.print(f"[dim]Opening Batch {idx} in default browser...[/dim]")
            typer.launch(url)

    console.print(
        "[dim]Review the pre-filled fields in yellow and click 'Save Changes' at the bottom of the page.[/dim]"
    )


def _render_checklist_table(items: Sequence[dict[str, Any]], title: str) -> None:
    """Render Rich terminal table for OpenSSF checklist items."""
    table = Table(title=title, title_justify="left")
    table.add_column("Criterion", style="cyan", no_wrap=True)
    table.add_column("Req", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Verdict", style="green")
    table.add_column("Justification", style="dim")

    for it in items:
        status = it.get("status", "?")
        verdict = it.get("local_verdict") or "-"
        table.add_row(
            it.get("criterion_id", ""),
            it.get("category", ""),
            status,
            verdict,
            it.get("justification") or "",
        )
    console.print(table)


@openssf_app.command(name="checklist")
def openssf_checklist(
    tier: Annotated[
        str,
        typer.Option("--tier", "-t", help="Target badge tier: passing, silver, or gold."),
    ] = "passing",
    project_id: Annotated[
        int | None,
        typer.Option("--project-id", "-i", help="Explicit OpenSSF project numeric ID."),
    ] = None,
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, json, markdown, rich, auto).",
    ),
    unmet_only: Annotated[
        bool,
        typer.Option("--unmet-only", "-u", help="Show only unmet or pending criteria."),
    ] = False,
) -> None:
    """Export or inspect the machine-readable OpenSSF Best Practices checklist."""
    adapter = OpenSsfBadgeAdapter()
    target_tier = OpenSsfTier(tier.lower())
    pid = _resolve_project_id(adapter, project_id)

    with console.status(f"[cyan]Retrieving checklist for project {pid}...[/cyan]"):
        project = adapter.fetch_project(pid)
        local_proposals = evaluate_local_heuristics(target_tier)
        items = generate_checklist(project, target_tier, local_proposals, unmet_only=unmet_only)

    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    if resolved_fmt == "json":
        console.print_json(data=items)
    elif resolved_fmt == "markdown":
        md = format_checklist_markdown(items, project.name, pid, target_tier)
        console.print(md)
    else:
        title = f"OpenSSF Best Practices Checklist ({project.name} - {target_tier.value.title()})"
        _render_checklist_table(items, title)


def _render_scorecard_table(result: ScorecardResult, show_details: bool) -> None:
    """Render Rich terminal table for OpenSSF Scorecard results."""
    console.print(
        f"\n[bold]OpenSSF Scorecard:[/bold] [cyan]{result.repo}[/cyan] | "
        f"[bold]Score:[/bold] [bold green]{result.score}/10[/bold green] | "
        f"[bold]Date:[/bold] {result.date}\n"
    )

    table = Table(title=f"Security Scorecard Checks ({result.repo})", title_justify="left")
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Score", style="magenta")
    table.add_column("Reason", style="dim")

    for chk in result.checks:
        score_style = "green" if chk.score >= 8 else ("yellow" if chk.score >= 5 else "red")
        score_str = f"[{score_style}]{chk.score}/10[/{score_style}]"
        table.add_row(chk.name, score_str, chk.reason)

    console.print(table)

    if show_details:
        console.print("\n[bold]Detailed Findings:[/bold]")
        for chk in result.checks:
            if chk.details:
                console.print(f"\n[bold cyan]{chk.name}[/bold cyan] ({chk.score}/10):")
                for d in chk.details:
                    console.print(f"  - {d}")


@openssf_app.command(name="scorecard")
def openssf_scorecard(
    repo: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Target GitHub repository (e.g. owner/repo)."),
    ] = None,
    details: Annotated[
        bool,
        typer.Option("--details", "-d", help="Display granular check reasons and details."),
    ] = False,
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, json, rich, auto).",
    ),
) -> None:
    """Audit OpenSSF Security Scorecard metrics and supply chain posture."""
    target_repo = repo
    if not target_repo:
        norm_url = resolve_local_repo_url()
        if not norm_url:
            console.print(
                "[bold red]Error:[/bold red] Could not determine repository URL. Specify --repo."
            )
            raise typer.Exit(code=1)
        target_repo = norm_url

    adapter = OpenSsfScorecardAdapter()
    with console.status(f"[cyan]Fetching OpenSSF Scorecard for {target_repo}...[/cyan]"):
        try:
            result = adapter.fetch_scorecard(target_repo)
        except Exception as exc:
            console.print(f"[bold red]Error fetching Scorecard:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    if resolved_fmt == "json":
        payload = {
            "repo": result.repo,
            "score": result.score,
            "date": result.date,
            "checks": [
                {"name": c.name, "score": c.score, "reason": c.reason, "details": c.details}
                for c in result.checks
            ],
        }
        console.print_json(data=payload)
    else:
        _render_scorecard_table(result, details)


@openssf_app.command(name="scaffold")
def openssf_scaffold(
    document: Annotated[
        str,
        typer.Argument(help="Document to scaffold: security, governance, contributing, or codeql."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files."),
    ] = False,
) -> None:
    """Scaffold standard OpenSSF governance and security compliance documents."""
    try:
        path = scaffold_document(document, force=force)
        console.print(f"[bold green]✓ Successfully generated:[/bold green] [cyan]{path}[/cyan]")
    except FileExistsError as exc:
        console.print(f"[bold yellow]Warning:[/bold yellow] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
