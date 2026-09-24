"""CLI subcommands for mutation testing and .mutmut-cache inspection.

Notes/Architectural Intent:
    Driving adapter exposing mutation test execution and cache inspection
    via the governance CommandDispatcher bus.
"""

from __future__ import annotations

import typer

from hexaqual.adapters.presenters.testing import create_testing_presenter
from hexaqual.adapters.workspace import (
    ensure_tool_installed,
    get_package_directories,
    get_package_directory,
    get_repo_root,
)
from hexaqual.domain.testing import (
    InspectMutationCacheCommand,
    RunMutationTestsCommand,
)
from hexaqual.infra.bootstrap import create_governance_bus

__all__ = [
    "mutate_app",
    "mutate_inspect",
    "mutate_run",
]

mutate_app = typer.Typer(
    name="mutate",
    help="Mutation testing execution and surviving mutant inspection.",
    no_args_is_help=True,
)


@mutate_app.command("run")
def mutate_run(
    package: str | None = typer.Option(
        None, "-p", "--package", help="Target package name (e.g. core)."
    ),
    all_packages: bool = typer.Option(
        False, "-a", "--all", help="Run across all workspace packages sequentially."
    ),
    reset: bool = typer.Option(False, "-r", "--reset", help="Clear cache and re-run."),
) -> None:
    """Run mutation testing scoped to package or workspace.

    Args:
        package: Target package name.
        all_packages: Whether to run across all workspace packages.
        reset: Clear mutmut cache and re-run.

    Raises:
        typer.Exit: If mutation testing fails.

    Notes/Architectural Intent:
        Executes mutmut mutation runner across targeted components via CQRS bus.
    """
    ensure_tool_installed("mutmut", cli_command="mutmut", extra_name="mutmut")
    root = get_repo_root()
    bus = create_governance_bus(repo_root=root)

    if package:
        pkg_dir = get_package_directory(package, root)
        targets = [pkg_dir]
    else:
        targets = get_package_directories(root)

    exit_code = 0
    for pkg_dir in targets:
        rc = bus.dispatch(RunMutationTestsCommand(package=pkg_dir.name, reset_cache=reset))
        if rc != 0:
            exit_code = rc
            break

    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@mutate_app.command("inspect")
def mutate_inspect(
    package: str | None = typer.Option(None, "-p", "--package", help="Filter by package."),
    all_mutants: bool = typer.Option(False, "-a", "--all", help="Inspect all mutants."),
    actionable: bool = typer.Option(
        False, "-act", "--actionable", help="Show actionable critical mutants."
    ),
    correlated: bool = typer.Option(False, "-c", "--correlated", help="Correlate with .coverage."),
    summary: bool = typer.Option(False, "-s", "--summary", help="Triage summary."),
    format_type: str = typer.Option("rich", "-f", "--format", help="Output format."),
) -> None:
    """Triage and inspect mutation testing results cache.

    Args:
        package: Filter by package.
        all_mutants: Display all surviving mutants.
        actionable: Display actionable critical mutants.
        correlated: Correlate with .coverage test context.
        summary: Display triage summary.
        format_type: Output format.

    Raises:
        typer.Exit: If inspect fails.

    Notes/Architectural Intent:
        Provides high-level triage and actionable surviving mutant analysis via CQRS bus.
    """
    ensure_tool_installed("mutmut", cli_command="mutmut", extra_name="mutmut")
    root = get_repo_root()
    cache_file = root / ".mutmut-cache"

    bus = create_governance_bus(repo_root=root)
    report = bus.dispatch(
        InspectMutationCacheCommand(
            cache_file=cache_file,
            package=package,
            actionable_only=actionable,
            correlate_coverage=correlated,
            coverage_file=root / ".coverage",
        )
    )
    presenter = create_testing_presenter(format_type)
    code = (
        presenter.present_actionable_mutants(report)
        if actionable
        else presenter.present_mutation_summary(report)
    )
    if code != 0:
        raise typer.Exit(code=code)
