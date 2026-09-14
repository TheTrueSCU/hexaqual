"""CLI subcommands for test execution, coverage audits, and impact analysis.

Notes/Architectural Intent:
    Driving adapter exposing test execution with coverage contexts, branch boundary
    assertion audits, git impact test subset selection, and redundancy analysis.
"""

from __future__ import annotations

import typer

__all__ = [
    "test_app",
    "test_archon",
    "test_boundary",
    "test_fuzz",
    "test_impact",
    "test_redundancy",
    "test_run",
    "test_snapshot",
]

test_app = typer.Typer(
    name="test",
    help="Test execution, coverage audits, and architecture verification.",
    no_args_is_help=True,
)


@test_app.command(
    "run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def test_run(
    ctx: typer.Context,
    package: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    example: list[str] | None = typer.Option(
        None, "-e", "--example", help="Target example project(s)."
    ),
    all_packages: bool = typer.Option(
        False, "-a", "--all", help="Run across all workspace packages."
    ),
    affected: bool = typer.Option(False, "-A", "--affected", help="Run only affected packages."),
    unit: bool = typer.Option(False, "-U", "--unit", help="Run only unit tests."),
    properties: bool = typer.Option(False, "-P", "--properties", help="Run only property tests."),
    with_context: bool = typer.Option(
        False, "--with-context", help="Capture test context in coverage."
    ),
) -> None:
    """Run pytest suite with dynamic worker allocation and coverage.

    Args:
        ctx: Command execution context capturing extra CLI options.
        package: Optional sequence of target package names.
        example: Optional sequence of target example project names.
        all_packages: Whether to run across all packages unconditionally.
        affected: Whether to run only packages affected by git diff.
        unit: Whether to restrict execution to unit tests.
        properties: Whether to restrict execution to property tests.
        with_context: Whether to capture test context in coverage.

    Raises:
        typer.Exit: If tests fail.

    Notes/Architectural Intent:
        Driving adapter delegating to pytest runner adapter and forwarding
        any additional unknown options or flags directly to pytest.
    """
    from hexaqual.commands.pytest_runner import run_main

    argv: list[str] = []
    if package:
        for p in package:
            argv.extend(["-p", p])
    if example:
        for e in example:
            argv.extend(["-e", e])
    if all_packages:
        argv.append("-a")
    if affected:
        argv.append("-A")
    if unit:
        argv.append("-U")
    if properties:
        argv.append("-P")
    if with_context:
        argv.append("--with-context")
    if ctx.args:
        argv.extend(ctx.args)
    exit_code = run_main(argv) or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@test_app.command("boundary")
def test_boundary(
    format_type: str = typer.Option("table", "-f", "--format", help="Output presentation format."),
) -> None:
    """Audit test suites for branch boundary and edge-case assertions.

    Args:
        format_type: Output format.

    Raises:
        typer.Exit: If boundary audit detects defects.

    Notes/Architectural Intent:
        Audits branch coverage assertions across test suites.
    """
    from hexaqual.commands.coverage import boundary_audit_main

    exit_code = boundary_audit_main() or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@test_app.command("impact")
def test_impact(
    format_type: str = typer.Option("table", "-f", "--format", help="Output presentation format."),
) -> None:
    """Selectively run tests impacted by current git diff changes.

    Args:
        format_type: Output format.

    Raises:
        typer.Exit: If impacted tests fail.

    Notes/Architectural Intent:
        Accelerates local feedback loops by running only affected test paths.
    """
    from hexaqual.commands.coverage import impact_main

    exit_code = impact_main() or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@test_app.command("redundancy")
def test_redundancy(
    format_type: str = typer.Option("table", "-f", "--format", help="Output presentation format."),
) -> None:
    """Analyze test execution overlap and flag duplicate test paths.

    Args:
        format_type: Output format.

    Raises:
        typer.Exit: If redundancy exceeds configured thresholds.

    Notes/Architectural Intent:
        Identifies duplicate test execution paths to optimize CI test efficiency.
    """
    from hexaqual.commands.coverage import redundancy_audit_main

    exit_code = redundancy_audit_main() or 0
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@test_app.command("fuzz")
def test_fuzz(
    target: str = typer.Option(
        "all", "-t", "--target", help="Target fuzz harness (all, sanitizer, proto, owasp)."
    ),
    runs: int = typer.Option(1000, "-n", "--runs", help="Number of fuzzed runs per harness."),
    engine: str = typer.Option(
        "auto", "-e", "--engine", help="Fuzzing engine (auto, atheris, standalone)."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
) -> None:
    """Run coverage-guided and adversarial security fuzz harnesses.

    Args:
        target: Target fuzz harness to execute.
        runs: Number of fuzzed runs per harness.
        engine: Fuzzing engine to use.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If any fuzz harness fails.

    Notes/Architectural Intent:
        Driving adapter dispatching FuzzRunCommand across the governance bus.
    """
    from hexaqual.adapters.presenters.analysis import create_analysis_presenter
    from hexaqual.domain.analysis import FuzzRunCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    bus = create_governance_bus()
    presenter = create_analysis_presenter(format_type)
    cmd = FuzzRunCommand(
        target=target,
        runs=runs,
        engine=engine,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_fuzz(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@test_app.command("snapshot")
def test_snapshot(
    mode: str = typer.Option(
        "fix", "-m", "--mode", help="inline-snapshot mode (create, fix, review)."
    ),
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
    files: list[str] | None = typer.Argument(None, help="Target file paths."),
) -> None:
    """Update or review inline snapshots across test suites.

    Args:
        mode: Snapshot update mode.
        packages: Target package(s).
        format_type: Output presentation format.
        files: Target file paths.

    Raises:
        typer.Exit: If snapshot update command fails.

    Notes/Architectural Intent:
        Driving adapter dispatching UpdateInlineSnapshotsCommand across packages.
    """
    from pathlib import Path

    from hexaqual.adapters.presenters.analysis import create_analysis_presenter
    from hexaqual.domain.analysis import UpdateInlineSnapshotsCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import (
        get_package_directories,
        get_package_directory,
        get_repo_root,
    )

    root = get_repo_root()
    targets: list[Path] = []
    if files:
        targets.extend(Path(f) for f in files)
    elif packages:
        targets.extend(get_package_directory(p, root) for p in packages)
    else:
        targets.extend(get_package_directories(root))

    bus = create_governance_bus(repo_root=root)
    presenter = create_analysis_presenter(format_type)
    cmd = UpdateInlineSnapshotsCommand(mode=mode, targets=tuple(targets))
    report = bus.dispatch(cmd)
    exit_code = presenter.present_inline_snapshots(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@test_app.command("archon")
def test_archon(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing boundary test files."),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
) -> None:
    """Generate pytest-archon boundary tests for packages.

    Args:
        packages: Target package(s) for test generation.
        force: Overwrite existing test files.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If generation fails.

    Notes/Architectural Intent:
        Driving adapter dispatching GenerateArchonTestsCommand across the governance bus.
    """
    from hexaqual.adapters.presenters.generators import create_generator_presenter
    from hexaqual.domain.generators import GenerateArchonTestsCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    root = get_repo_root()
    bus = create_governance_bus(repo_root=root)
    presenter = create_generator_presenter(format_type)
    cmd = GenerateArchonTestsCommand(
        packages=tuple(packages) if packages else (),
        force=force,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_archon(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
