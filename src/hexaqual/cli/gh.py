"""CLI subcommands for GitHub PR examination, status checks, and security alerts.

Notes/Architectural Intent:
    Driving adapter exposing PR diagnostic dashboards, CI check runs inspection,
    repository governance settings, Dependabot alerts, and CodeQL alerts.
"""

from __future__ import annotations

import time

import typer

__all__ = [
    "gh_app",
    "gh_checks",
    "gh_code_scanning",
    "gh_pr",
    "gh_repo",
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
    from hexaqual.domain.github import ExaminePrCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

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
    from hexaqual.domain.github import InspectChecksCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

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
    from hexaqual.domain.github import InspectRepoCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

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
    format_type: str = typer.Option("auto", "-f", "--format", help="Output format."),
) -> None:
    """Summarize GitHub security advisories and Dependabot alerts.

    Args:
        format_type: Output format.

    Raises:
        typer.Exit: If security alerts found or query fails.

    Notes/Architectural Intent:
        Queries Dependabot security alerts and advisories.
    """
    from hexaqual.adapters.github.client import GitHubHttpAdapter
    from hexaqual.adapters.presenters.github import create_github_presenter
    from hexaqual.domain.github import InspectSecurityCommentsCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    root = get_repo_root()
    with GitHubHttpAdapter() as client:
        bus = create_governance_bus(github_client=client, repo_root=root)
        rep = bus.dispatch(InspectSecurityCommentsCommand(pr_number=0))
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
    from hexaqual.domain.github import InspectCodeScanningCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    root = get_repo_root()
    with GitHubHttpAdapter() as client:
        bus = create_governance_bus(github_client=client, repo_root=root)
        rep = bus.dispatch(InspectCodeScanningCommand())
    presenter = create_github_presenter(output_format=format_type)
    exit_code = presenter.present_code_scanning(rep) or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
