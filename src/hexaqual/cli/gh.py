"""CLI subcommands for GitHub PR examination, status checks, and security alerts.

Notes/Architectural Intent:
    Driving adapter exposing PR diagnostic dashboards, CI check runs inspection,
    repository governance settings, Dependabot alerts, and CodeQL alerts.
"""

from __future__ import annotations

import time
from pathlib import Path

import typer

__all__ = [
    "gh_app",
    "gh_checks",
    "gh_code_scanning",
    "gh_codeql",
    "gh_pr",
    "gh_repo",
    "gh_resolve",
    "gh_security",
]

gh_app = typer.Typer(
    name="gh",
    help="GitHub repository, PR, and security examination.",
    no_args_is_help=True,
)


@gh_app.command("pr")
def gh_pr(
    pr_number: str = typer.Argument(..., help="Pull request number to examine."),
    details: bool = typer.Option(
        False, "--details", "-d", help="Display full comment discussions."
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w", help="Continuously poll until checks finish."
    ),
    format_type: str = typer.Option(
        "auto", "-f", "--format", help="Output format (auto, rich, json, plain)."
    ),
) -> None:
    """Examine a Pull Request health dashboard.

    Args:
        pr_number: Pull request number.
        details: Display full comments and review threads.
        watch: Poll until checks finish.
        format_type: Output format.

    Raises:
        typer.Exit: If examination fails.

    Notes/Architectural Intent:
        Single-step PR dashboard inspecting CI check runs and reviews.
    """
    from hexaqual.adapters.github.client import GitHubHttpAdapter
    from hexaqual.adapters.presenters.github import create_github_presenter
    from hexaqual.adapters.workspace import get_repo_root
    from hexaqual.cli.options import is_interactive_terminal
    from hexaqual.domain.github import ExaminePrCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    if watch and not is_interactive_terminal():
        from rich.console import Console

        console = Console(stderr=True)
        console.print(
            f"[bold red]❌ Error:[/bold red] The '--watch' ('-w') flag requires an interactive terminal (TTY).\n"
            f"[dim]Running continuous polling in headless, CI, or automated background environments is unsupported.[/dim]\n\n"
            f"[yellow]💡 Suggested alternatives:[/yellow]\n"
            f"  • Run without '-w' for a one-shot snapshot: [cyan]uv run hexaqual gh pr {pr_number}[/cyan]\n"
            f"  • Inspect check runs directly: [cyan]uv run hexaqual gh checks {pr_number}[/cyan]\n"
            f"  • Query GitHub CLI natively: [cyan]gh pr checks {pr_number}[/cyan]"
        )
        raise typer.Exit(code=1)

    root = get_repo_root()
    presenter = create_github_presenter(output_format=format_type)
    while True:
        with GitHubHttpAdapter() as client:
            bus = create_governance_bus(github_client=client, repo_root=root)
            rep = bus.dispatch(
                ExaminePrCommand(
                    pr_number=int(pr_number),
                    show_details=details,
                )
            )
        exit_code = presenter.present_pr_summary(rep) or 0
        if not watch:
            break
        if rep.summary.state.lower() in ("closed", "merged"):
            break
        if rep.summary.check_runs and all(
            c.status.lower() == "completed" for c in rep.summary.check_runs
        ):
            break
        time.sleep(15)

    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@gh_app.command("checks")
def gh_checks(
    ref_or_pr: str = typer.Argument(..., help="Pull request number or commit ref/branch name."),
    format_type: str = typer.Option("auto", "-f", "--format", help="Output format."),
) -> None:
    """Inspect CI status checks for a given PR number or Git ref.

    Args:
        ref_or_pr: PR number or branch/ref.
        format_type: Output format.

    Raises:
        typer.Exit: If status checks failed or query errors.

    Notes/Architectural Intent:
        Lists detailed GitHub Actions status checks and run conclusions.
    """
    from hexaqual.adapters.github.client import GitHubHttpAdapter
    from hexaqual.adapters.presenters.github import create_github_presenter
    from hexaqual.adapters.workspace import get_repo_root
    from hexaqual.domain.github import InspectChecksCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    root = get_repo_root()
    with GitHubHttpAdapter() as client:
        bus = create_governance_bus(github_client=client, repo_root=root)
        rep = bus.dispatch(InspectChecksCommand(ref_or_pr=ref_or_pr))
    presenter = create_github_presenter(output_format=format_type)
    exit_code = presenter.present_checks(rep) or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@gh_app.command("repo")
def gh_repo(
    repo_name: str | None = typer.Argument(None, help="Repository name (owner/repo)."),
    format_type: str = typer.Option("auto", "-f", "--format", help="Output format."),
) -> None:
    """Inspect GitHub repository settings and permissions.

    Args:
        repo_name: Optional repo identifier.
        format_type: Output format.

    Raises:
        typer.Exit: If query fails.

    Notes/Architectural Intent:
        Inspects repository settings, Actions permissions, and environments.
    """
    from hexaqual.adapters.github.client import GitHubHttpAdapter
    from hexaqual.adapters.presenters.github import create_github_presenter
    from hexaqual.adapters.workspace import get_repo_root
    from hexaqual.domain.github import InspectRepoCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    root = get_repo_root()
    with GitHubHttpAdapter() as client:
        bus = create_governance_bus(github_client=client, repo_root=root)
        rep = bus.dispatch(InspectRepoCommand(repo_name=repo_name))
    presenter = create_github_presenter(output_format=format_type)
    exit_code = presenter.present_repo_status(rep) or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@gh_app.command("security")
def gh_security(
    pr_number: int = typer.Argument(
        ..., help="Pull request number to inspect security review comments for."
    ),
    format_type: str = typer.Option("auto", "-f", "--format", help="Output format."),
) -> None:
    """Summarize review discussions and security comments on a PR.

    Args:
        pr_number: Pull request number.
        format_type: Output format.

    Raises:
        typer.Exit: If security comments check fails or query fails.

    Notes/Architectural Intent:
        Queries PR review discussions and security comment threads.
    """
    from hexaqual.adapters.github.client import GitHubHttpAdapter
    from hexaqual.adapters.presenters.github import create_github_presenter
    from hexaqual.adapters.workspace import get_repo_root
    from hexaqual.domain.github import InspectSecurityCommentsCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    root = get_repo_root()
    with GitHubHttpAdapter() as client:
        bus = create_governance_bus(github_client=client, repo_root=root)
        rep = bus.dispatch(InspectSecurityCommentsCommand(pr_number=pr_number))
    presenter = create_github_presenter(output_format=format_type)
    exit_code = presenter.present_security_comments(rep) or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@gh_app.command("code-scanning")
def gh_code_scanning(
    format_type: str = typer.Option("auto", "-f", "--format", help="Output format."),
) -> None:
    """Query CodeQL alerts and scanning status.

    Args:
        format_type: Output format.

    Raises:
        typer.Exit: If scanning alerts found or query fails.

    Notes/Architectural Intent:
        Queries GitHub CodeQL code scanning alerts.
    """
    from hexaqual.adapters.github.client import GitHubHttpAdapter
    from hexaqual.adapters.presenters.github import create_github_presenter
    from hexaqual.adapters.workspace import get_repo_root
    from hexaqual.domain.github import InspectCodeScanningCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    root = get_repo_root()
    with GitHubHttpAdapter() as client:
        bus = create_governance_bus(github_client=client, repo_root=root)
        rep = bus.dispatch(InspectCodeScanningCommand())
    presenter = create_github_presenter(output_format=format_type)
    exit_code = presenter.present_code_scanning(rep) or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@gh_app.command("codeql")
def gh_codeql(
    suite: str = typer.Option(
        "codeql/python-queries", "-s", "--suite", help="CodeQL query suite or pack."
    ),
    output: Path | None = typer.Option(
        None, "-o", "--output", help="Optional destination path for generated SARIF report."
    ),
    threads: int = typer.Option(
        0, "-t", "--threads", help="Number of analysis threads (0 for auto)."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
) -> None:
    """Run local CodeQL security and quality analysis with auto-detection.

    Args:
        suite: CodeQL query suite or pack name.
        output: Optional destination path for SARIF report.
        threads: Number of analysis threads (0 for auto).
        format_type: Output presentation format.

    Raises:
        typer.Exit: If CodeQL analysis detects critical violations.

    Notes/Architectural Intent:
        Driving adapter dispatching ScanCodeQlCommand across the governance bus.
    """
    from hexaqual.adapters.presenters.analysis import create_analysis_presenter
    from hexaqual.domain.analysis import ScanCodeQlCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    bus = create_governance_bus()
    presenter = create_analysis_presenter(format_type)

    cmd = ScanCodeQlCommand(
        query_suite=suite,
        output_sarif=output,
        threads=threads,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_codeql(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@gh_app.command("resolve")
def gh_resolve(
    pr_number: str = typer.Argument(..., help="Pull request number to resolve threads on."),
    bot_only: bool = typer.Option(
        True,
        "--bot-only/--all",
        help="Resolve only automated bot review threads (e.g. CodeRabbit, Dependabot).",
    ),
) -> None:
    """Resolve open review discussion threads on a Pull Request via GitHub GraphQL.

    Args:
        pr_number: Pull request number.
        bot_only: If True, only auto-resolve comments authored by bot accounts.

    Raises:
        typer.Exit: If thread retrieval or resolution encounters critical errors.

    Notes/Architectural Intent:
        Unblocks branch protection policies enforcing 'required_conversation_resolution'
        by programmatically resolving open review threads.
    """
    from rich.console import Console

    from hexaqual.adapters.github.client import GitHubHttpAdapter

    console = Console()
    with GitHubHttpAdapter() as client:
        threads = client.get_review_threads(int(pr_number))
        if not threads:
            console.print(
                f"[green]✓ No review discussion threads found on PR #{pr_number}.[/green]"
            )
            return

        unresolved = [t for t in threads if not t.is_resolved]
        if not unresolved:
            console.print(
                f"[green]✓ All {len(threads)} review threads on PR #{pr_number} are already resolved.[/green]"
            )
            return

        target_threads = []
        for t in unresolved:
            if not bot_only:
                target_threads.append(t)
            else:
                is_bot = any(
                    c.author.lower().endswith(("[bot]", "coderabbitai"))
                    or c.author.lower() in ("coderabbitai", "github-actions", "dependabot")
                    for c in t.comments
                )
                if is_bot:
                    target_threads.append(t)

        if not target_threads:
            console.print(
                f"[dim]No unresolved matching review threads to resolve on PR #{pr_number}.[/dim]"
            )
            return

        resolved_count = 0
        for t in target_threads:
            author_snippet = t.comments[0].author if t.comments else "unknown"
            if client.resolve_review_thread(t.id):
                resolved_count += 1
                console.print(f"[green]✓ Resolved thread {t.id} (author: {author_snippet})[/green]")
            else:
                console.print(f"[yellow]⚠ Failed to resolve thread {t.id}[/yellow]")

        console.print(
            f"[bold green]✨ Resolved {resolved_count}/{len(target_threads)} review threads on PR #{pr_number}.[/bold green]"
        )
