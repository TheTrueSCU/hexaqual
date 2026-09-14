"""CLI subcommands for mutation testing execution and triage analysis.

Notes/Architectural Intent:
    Driving adapter exposing mutation test execution via mutmut and interactive
    or summary mutant inspection correlated with test coverage contexts.
"""

from __future__ import annotations

import typer

__all__ = [
    "mutate_app",
    "mutate_inspect",
    "mutate_run",
]

mutate_app = typer.Typer(
    name="mutate",
    help="Mutation testing execution and triage inspection.",
    no_args_is_help=True,
)


@mutate_app.command("run")
def mutate_run(
    package: str | None = typer.Option(None, "-p", "--package", help="Target package name."),
    all_packages: bool = typer.Option(
        False, "-a", "--all", help="Run across all workspace packages."
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
        Executes mutmut mutation runner across targeted components.
    """
    from hexaqual.commands.mutmut import (
        clear_package_cache,
        ensure_tool_installed,
        run_mutmut_on_package,
    )
    from hexaqual.utils.workspace import (
        get_package_directories,
        get_package_directory,
        get_repo_root,
    )

    ensure_tool_installed("mutmut", cli_command="mutmut", extra_name="mutmut")
    root = get_repo_root()

    if reset:
        if package:
            clear_package_cache(package)
        else:
            for pkg_dir in get_package_directories(root):
                clear_package_cache(pkg_dir.name)

    if package:
        pkg_dir = get_package_directory(package, root)
        exit_code = run_mutmut_on_package(pkg_dir)
    else:
        exit_code = 0
        for pkg_dir in get_package_directories(root):
            exit_code = run_mutmut_on_package(pkg_dir)
            if exit_code != 0:
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
        Provides high-level triage and actionable surviving mutant analysis.
    """
    from hexaqual.adapters.presenters.testing import create_testing_presenter
    from hexaqual.commands.mutmut import (
        CACHE_FILE,
        ensure_tool_installed,
        get_db_connection,
        show_file_mutants,
        show_summary,
    )
    from hexaqual.domain.testing import InspectMutationCacheCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    ensure_tool_installed("mutmut", cli_command="mutmut", extra_name="mutmut")
    root = get_repo_root()

    if format_type in ("json", "markdown"):
        bus = create_governance_bus(repo_root=root)
        report = bus.dispatch(
            InspectMutationCacheCommand(
                cache_file=CACHE_FILE,
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
        return

    con = get_db_connection()
    if not con:
        raise typer.Exit(code=1)

    try:
        if summary or (not package and not all_mutants):
            show_summary(con)
        if package:
            show_file_mutants(
                con,
                package,
                limit=25,
                actionable_only=actionable,
                correlate_coverage=correlated,
            )
    finally:
        con.close()
