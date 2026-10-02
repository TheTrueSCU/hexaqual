"""CLI subcommands for mutation testing and .mutmut-cache inspection.

Notes/Architectural Intent:
    Driving adapter exposing mutation test execution and cache inspection
    via the governance CommandDispatcher bus.
"""

from __future__ import annotations

from pathlib import Path

import typer

from hexaqual.adapters.presenters.testing import create_testing_presenter
from hexaqual.adapters.workspace import (
    ensure_tool_installed,
    get_repo_root,
)
from hexaqual.domain.testing import (
    InspectMutationCacheCommand,
    MutationEngine,
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
    affected: bool = typer.Option(
        False, "-A", "--affected", help="Run only on packages affected by git diff."
    ),
    reset: bool = typer.Option(False, "-r", "--reset", help="Clear cache and re-run."),
    engine: str = typer.Option(
        "gremlins",
        "-e",
        "--engine",
        help="Mutation engine to use ('gremlins' or 'mutmut').",
    ),
    workers: str | None = typer.Option(
        None,
        "-w",
        "--workers",
        help="Number of parallel mutation workers (defaults to 'auto' across available cores).",
    ),
    numprocesses: str | None = typer.Option(
        None,
        "-n",
        "--numprocesses",
        help="Pytest-xdist worker count for baseline test execution (defaults to 'auto' when xdist is installed).",
    ),
    batch_size: int | None = typer.Option(
        None,
        "--batch-size",
        help="Number of gremlins per worker batch (defaults to 10).",
    ),
    cluster: str = typer.Option(
        "local",
        "--cluster",
        help="Execution target cluster ('local' or 'hexaqueue').",
    ),
    cluster_url: str = typer.Option(
        "http://localhost:8000",
        "--cluster-url",
        envvar="HEXAQUEUE_URL",
        help="Hexaqueue cluster REST endpoint URL.",
    ),
    cluster_token: str | None = typer.Option(
        None,
        "--cluster-token",
        envvar="HEXAQUEUE_TOKEN",
        help="Authentication bearer token for Hexaqueue cluster.",
    ),
    cluster_user: str = typer.Option(
        "default",
        "--cluster-user",
        envvar="HEXAQUEUE_USER",
        help="Submitting user identity for Hexaqueue cluster.",
    ),
    cluster_elevate: bool = typer.Option(
        False,
        "--cluster-elevate",
        help="Assert administrative elevation on Hexaqueue cluster.",
    ),
) -> None:
    """Run mutation testing scoped to package or workspace.

    Args:
        package: Target package name.
        all_packages: Whether to run across all workspace packages.
        affected: Whether to run only packages affected by git diff.
        reset: Clear cache and re-run.
        engine: Runner engine ('gremlins' or 'mutmut').
        workers: Parallel workers during mutation phase.
        numprocesses: Pytest-xdist baseline process count.
        batch_size: Mutants per worker batch.
        cluster: Execution target cluster ('local' or 'hexaqueue').
        cluster_url: Hexaqueue cluster REST endpoint URL.
        cluster_token: Authentication bearer token for Hexaqueue cluster.
        cluster_user: Submitting user identity for Hexaqueue cluster.
        cluster_elevate: Assert administrative elevation on Hexaqueue cluster.

    Raises:
        typer.Exit: If mutation testing fails.

    Notes/Architectural Intent:
        Executes mutation runner across targeted components via CQRS bus.
        Decouples baseline suite parallelism (-n) from mutation worker crunching (-w).
        Supports distributing mutation workloads to a remote Hexaqueue cluster.
    """
    eng = (
        MutationEngine(engine.lower())
        if engine.lower() in ("gremlins", "mutmut")
        else MutationEngine.GREMLINS
    )
    cluster_norm = cluster.lower()
    if cluster_norm not in ("local", "hexaqueue"):
        raise typer.BadParameter(
            f"Invalid --cluster '{cluster}'. Supported values are 'local' or 'hexaqueue'."
        )
    if cluster_norm == "local":
        if eng == MutationEngine.GREMLINS:
            ensure_tool_installed("pytest_gremlins", extra_name="gremlins")
        else:
            ensure_tool_installed("mutmut", cli_command="mutmut", extra_name="mutmut")

    root = get_repo_root()
    testing_runner = None
    if cluster_norm == "hexaqueue":
        from hexaqual.adapters.runners.hexaqueue_cluster import HexaqueueClusterRunnerAdapter

        testing_runner = HexaqueueClusterRunnerAdapter(
            cluster_url=cluster_url,
            user_id=cluster_user,
            elevate=cluster_elevate,
            token=cluster_token,
        )

    bus = create_governance_bus(repo_root=root, testing_runner=testing_runner)

    exit_code = bus.dispatch(
        RunMutationTestsCommand(
            package=package,
            all_packages=all_packages or (not package and not affected),
            affected=affected,
            reset_cache=reset,
            engine=eng,
            workers=workers,
            numprocesses=numprocesses,
            batch_size=batch_size,
        )
    )

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
    engine: str = typer.Option(
        "gremlins",
        "-e",
        "--engine",
        help="Mutation engine to inspect ('gremlins' or 'mutmut').",
    ),
    report_file: str | None = typer.Option(
        None, "--report-file", help="Explicit path to gremlins JSON report file."
    ),
) -> None:
    """Triage and inspect mutation testing results cache or report.

    Args:
        package: Filter by package.
        all_mutants: Display all surviving mutants.
        actionable: Display actionable critical mutants.
        correlated: Correlate with .coverage test context.
        summary: Display triage summary.
        format_type: Output format.
        engine: Mutation engine inspected ('gremlins' or 'mutmut').
        report_file: Explicit report file path.

    Raises:
        typer.Exit: If inspect fails.

    Notes/Architectural Intent:
        Provides high-level triage and actionable surviving mutant analysis via CQRS bus.
    """
    eng = (
        MutationEngine(engine.lower())
        if engine.lower() in ("gremlins", "mutmut")
        else MutationEngine.GREMLINS
    )
    if eng == MutationEngine.MUTMUT:
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
            engine=eng,
            report_file=Path(report_file) if report_file else None,
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
