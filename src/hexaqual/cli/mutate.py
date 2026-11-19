"""CLI subcommands for mutation testing and .mutmut-cache inspection.

Notes/Architectural Intent:
    Driving adapter exposing mutation test execution and cache inspection
    via the governance CommandDispatcher bus.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import typer

from hexaqual.adapters.presenters.testing import (
    MarkdownTestingPresenterAdapter,
    create_testing_presenter,
)
from hexaqual.adapters.runners.hexaqueue_cluster import HexaqueueClusterRunnerAdapter
from hexaqual.adapters.workspace import (
    ensure_tool_installed,
    get_repo_root,
)
from hexaqual.cli.options import append_step_summary
from hexaqual.domain.testing import (
    InspectMutationCacheCommand,
    MutationEngine,
    RunMutationTestsCommand,
)
from hexaqual.infra.bootstrap import create_governance_bus
from hexaqual.utils.mutation_slicing import (
    DEFAULT_MAX_SLICE_WEIGHT,
    DEFAULT_NUM_SLICES,
    plan_mutation_matrix,
)

__all__ = [
    "mutate_app",
    "mutate_inspect",
    "mutate_plan",
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
    direct_only: bool = typer.Option(
        False,
        "--direct",
        "--direct-only",
        help="Restrict affected analysis to directly modified package directories, skipping transitive dependents and root infra changes.",
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
    targets: str | None = typer.Option(
        None,
        "-t",
        "--targets",
        help="Comma-separated relative source file paths to mutate.",
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
    cluster_timeout: float | None = typer.Option(
        None,
        "--cluster-timeout",
        envvar="HEXAQUEUE_TIMEOUT",
        help="Maximum execution timeout in seconds for remote Hexaqueue workload (defaults to 1800.0s).",
    ),
) -> None:
    """Run mutation testing scoped to package or workspace.

    Args:
        package: Target package name.
        all_packages: Whether to run across all workspace packages.
        affected: Whether to run only packages affected by git diff.
        direct_only: Whether to restrict affected analysis to directly modified package directories.
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
        cluster_timeout: Maximum execution timeout in seconds for remote Hexaqueue workload.

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
        testing_runner = HexaqueueClusterRunnerAdapter(
            cluster_url=cluster_url,
            user_id=cluster_user,
            elevate=cluster_elevate,
            token=cluster_token,
            timeout=cluster_timeout,
        )

    bus = create_governance_bus(repo_root=root, testing_runner=testing_runner)

    target_list = [item.strip() for item in targets.split(",") if item.strip()] if targets else None
    exit_code = bus.dispatch(
        RunMutationTestsCommand(
            package=package,
            all_packages=all_packages or (not package and not affected),
            affected=affected,
            direct_only=direct_only,
            reset_cache=reset,
            engine=eng,
            workers=workers,
            numprocesses=numprocesses,
            batch_size=batch_size,
            targets=target_list,
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
    step_summary: bool = typer.Option(
        False, "--step-summary", help="Append Markdown summary to $GITHUB_STEP_SUMMARY."
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
    if step_summary:
        md_presenter = MarkdownTestingPresenterAdapter()
        md_text = (
            md_presenter.render_actionable_mutants_markdown(report)
            if actionable
            else md_presenter.render_mutation_summary_markdown(report)
        )
        append_step_summary(md_text)

    if code != 0:
        raise typer.Exit(code=code)


@mutate_app.command("plan")
def mutate_plan(
    mode: str = typer.Option(
        "affected",
        "--mode",
        help="Planning mode ('affected', 'all', 'slices', or 'changed-slices').",
    ),
    base_ref: str = typer.Option(
        "main",
        "--base-ref",
        envvar="GITHUB_BASE_REF",
        help="Git base branch for 'affected' and 'changed-slices' modes.",
    ),
    packages_root: Path = typer.Option(
        Path("packages"),
        "--packages-root",
        help="Workspace packages directory for monorepo layouts.",
    ),
    root: Path = typer.Option(
        Path("src"),
        "--root",
        help="Source directory to partition for single-package slice modes.",
    ),
    slices: int = typer.Option(
        DEFAULT_NUM_SLICES,
        "--slices",
        help="Maximum number of parallel slices for slice-based modes.",
    ),
    max_weight: int = typer.Option(
        DEFAULT_MAX_SLICE_WEIGHT,
        "--max-weight",
        help="Per-slice AST mutation weight cap (0 disables dynamic capping).",
    ),
    github_output: bool = typer.Option(
        False,
        "--github-output",
        help="Write 'matrix' and 'has_affected' to $GITHUB_OUTPUT when set.",
    ),
) -> None:
    """Plan an AST-weighted, capacity-capped LPT mutation testing matrix.

    Args:
        mode: Planning mode ('affected', 'all', 'slices', or 'changed-slices').
        base_ref: Git base branch for diff-based modes.
        packages_root: Workspace packages root directory.
        root: Source directory for single-package slice modes.
        slices: Maximum number of parallel slices.
        max_weight: Per-slice AST weight cap (0 disables dynamic capping).
        github_output: Whether to append outputs to ``$GITHUB_OUTPUT``.

    Raises:
        typer.BadParameter: If ``mode`` is unsupported.

    Notes/Architectural Intent:
        Single CLI entrypoint consumed both locally for debugging and by the
        ``.github/actions/mutate-plan`` composite action so CI and cluster
        runners share the exact same AST-weighted LPT slicer.
    """
    try:
        matrix_obj, has_affected = plan_mutation_matrix(
            mode,
            base_ref=base_ref,
            packages_root=packages_root,
            root=root,
            num_slices=slices,
            max_slice_weight=max_weight if max_weight > 0 else None,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--mode") from exc

    matrix_json = json.dumps(matrix_obj)
    has_flag = "true" if has_affected else "false"
    output_lines = [f"matrix={matrix_json}", f"has_affected={has_flag}"]

    output_path = os.environ.get("GITHUB_OUTPUT", "").strip() if github_output else ""
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(output_lines) + "\n")
    else:
        sys.stdout.write("\n".join(output_lines) + "\n")
