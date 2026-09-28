"""CLI commands for OpenSSF Best Practices auditing and automation proposals.

Notes/Architectural Intent:
    Provides Typer subcommands under 'hexaqual openssf' for auditing badge criteria,
    evaluating local heuristics, generating chunked proposal URLs, and launching them
    in the default browser without persisting credentials.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from hexaqual.adapters.openssf import OpenSsfBadgeAdapter
from hexaqual.domain.openssf import OpenSsfTier
from hexaqual.infra.openssf import (
    audit_project_posture,
    evaluate_local_heuristics,
    resolve_local_repo_url,
)

__all__ = [
    "openssf_app",
    "openssf_audit",
    "openssf_propose",
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
) -> None:
    """Audit OpenSSF Best Practices badge status and identify pending criteria."""
    adapter = OpenSsfBadgeAdapter()
    target_tier = OpenSsfTier(tier.lower())
    pid = _resolve_project_id(adapter, project_id)

    with console.status(f"[cyan]Auditing OpenSSF project {pid} ({target_tier.value})...[/cyan]"):
        project = adapter.fetch_project(pid)
        local_proposals = evaluate_local_heuristics(target_tier)
        result = audit_project_posture(project, target_tier, local_proposals)

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
