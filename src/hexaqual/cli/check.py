"""Sanity and verification commands for the Hexaqual CLI.

Notes/Architectural Intent:
    Driving adapter exposing the multi-stage quality sanity check pipeline,
    supporting both 'check' and legacy 'sanity' command entrypoints.
"""

from __future__ import annotations

import typer
from hexaflow import StepContext, TriggerRule, Workflow

__all__ = [
    "check",
    "complexity",
    "register_check_commands",
    "sanity",
    "sanity_binder",
]


def _build_sanity_template_workflow() -> Workflow:
    """Construct canonical sanity check pipeline DAG template for CLI binding.

    Notes/Architectural Intent:
        Defines the canonical sanity check stages and steps to power dynamic
        CLI option binding via hexaflow.cli.binder.WorkflowCliBinder.
    """
    wf = Workflow("sanity_template")

    @wf.stage("static_checks")
    @wf.step("lint", trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED)
    def _lint(ctx: StepContext) -> None:
        pass

    @wf.step("all_statements", trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED)
    def _all_statements(ctx: StepContext) -> None:
        pass

    @wf.step("test_parity", trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED)
    def _test_parity(ctx: StepContext) -> None:
        pass

    @wf.step("diagrams", trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED)
    def _diagrams(ctx: StepContext) -> None:
        pass

    @wf.stage("analysis")
    @wf.step(
        "typecheck",
        depends_on=["lint"],
        trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
    )
    def _typecheck(ctx: StepContext) -> None:
        pass

    @wf.step(
        "complexity",
        depends_on=["lint"],
        trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
    )
    def _complexity(ctx: StepContext) -> None:
        pass

    @wf.step(
        "deptry",
        depends_on=["lint"],
        trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
    )
    def _deptry(ctx: StepContext) -> None:
        pass

    @wf.stage("verification")
    @wf.step(
        "pytest",
        depends_on=["typecheck", "complexity"],
        trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
    )
    def _pytest(ctx: StepContext) -> None:
        pass

    return wf


sanity_binder = _build_sanity_template_workflow().create_cli_binder(
    aliases={
        "lint": ["--skip-ruff"],
        "all_statements": ["--skip-statements"],
        "test_parity": ["--skip-parity"],
        "diagrams": ["--skip-diagrams"],
        "typecheck": ["--skip-ty"],
        "pytest": ["--skip-tests"],
    }
)


def _execute_sanity_pipeline(
    packages: list[str] | None,
    examples: list[str] | None,
    all_targets: bool,
    fix: bool,
    skip: list[str] | None,
    max_complexity: int,
    format_type: str,
    skip_steps: set[str] | None,
    files: list[str] | None,
    numprocesses: str = "auto",
    sequential: bool = False,
) -> None:
    """Execute shared sanity pipeline across targets.

    Args:
        packages: Optional sequence of package names to audit.
        examples: Optional sequence of example project names to audit.
        all_targets: Whether to audit all packages unconditionally.
        fix: Whether to auto-apply formatting and lint fixes.
        skip: Optional list of explicit step names to skip.
        max_complexity: Cognitive complexity ceiling.
        format_type: Output presentation format.
        skip_steps: Step names dynamically skipped via CLI flags.
        files: Optional explicit file or directory targets.
        numprocesses: Concurrency width ('auto' for cores - 2, or 1..num_cores).
        sequential: Whether to execute checks sequentially (sets parallelism to 1).

    Raises:
        typer.Exit: If any sanity checks fail.
    """
    from hexaqual.adapters.code_analysis.sanity import resolve_targets
    from hexaqual.adapters.presenters.governance import create_governance_presenter
    from hexaqual.adapters.workspace import get_repo_root
    from hexaqual.domain.governance import RunSanityCheckCommand, resolve_parallelism
    from hexaqual.infra.bootstrap import create_governance_bus

    repo_root = get_repo_root()
    targets = resolve_targets(
        packages=packages,
        examples=examples,
        files=files or [],
        all_targets=all_targets,
        repo_root=repo_root,
    )
    merged_skips = set(skip_steps or set())
    if skip:
        merged_skips.update(skip)

    if sequential:
        parallelism = 1
    else:
        try:
            parallelism = resolve_parallelism(numprocesses)
        except ValueError as err:
            typer.echo(f"Error: {err}", err=True)
            raise typer.Exit(code=2) from err

    bus = create_governance_bus()
    presenter = create_governance_presenter(format_type=format_type)
    cmd = RunSanityCheckCommand(
        targets=tuple(targets),
        repo_root=repo_root,
        fix=fix,
        skip_tests="pytest" in merged_skips,
        skip_deptry="deptry" in merged_skips,
        skip_typecheck="typecheck" in merged_skips,
        skip_complexity="complexity" in merged_skips,
        skip_parity="test_parity" in merged_skips,
        skip_all_statements="all_statements" in merged_skips,
        skip_diagrams="diagrams" in merged_skips,
        skip_steps=tuple(sorted(merged_skips)),
        max_complexity=max_complexity,
        parallelism=parallelism,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_sanity_dashboard(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@sanity_binder.apply
def check(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    examples: list[str] | None = typer.Option(None, "-e", "--example", help="Target example(s)."),
    all_targets: bool = typer.Option(False, "-a", "--all", help="Run across all packages."),
    fix: bool = typer.Option(False, "--fix", help="Automatically apply autofixes."),
    skip: list[str] | None = typer.Option(
        None, "--skip", help="Specific pipeline step(s) to skip (repeatable)."
    ),
    numprocesses: str = typer.Option(
        "auto",
        "-n",
        "--numprocesses",
        "--parallelism",
        help="Concurrency width ('auto' for cores - 2, or 1..num_cores).",
    ),
    sequential: bool = typer.Option(
        False,
        "--sequential",
        help="Execute checks sequentially (equivalent to -n 1).",
    ),
    max_complexity: int = typer.Option(
        25, "-mx", "--max-complexity", help="Cognitive complexity ceiling."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
    skip_steps: set[str] | None = None,
    files: list[str] | None = typer.Argument(None, help="Specific files or directories to verify."),
) -> None:
    """Execute the sanity check pipeline.

    Args:
        packages: Optional sequence of package names to audit.
        examples: Optional sequence of example project names to audit.
        all_targets: Whether to audit all packages unconditionally.
        fix: Whether to auto-apply formatting and lint fixes.
        skip: Optional list of explicit step names to skip.
        numprocesses: Concurrency width ('auto' for cores - 2, or 1..num_cores).
        sequential: Whether to execute checks sequentially (equivalent to -n 1).
        max_complexity: Cognitive complexity ceiling.
        format_type: Output presentation format.
        skip_steps: Step names dynamically skipped via CLI flags.
        files: Optional explicit file or directory targets.

    Raises:
        typer.Exit: If any sanity checks fail.

    Notes/Architectural Intent:
        Primary entrypoint for local pre-commit verification and CI pipelines.
    """
    _execute_sanity_pipeline(
        packages=packages,
        examples=examples,
        all_targets=all_targets,
        fix=fix,
        skip=skip,
        max_complexity=max_complexity,
        format_type=format_type,
        skip_steps=skip_steps,
        files=files,
        numprocesses=numprocesses,
        sequential=sequential,
    )


@sanity_binder.apply
def sanity(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    examples: list[str] | None = typer.Option(None, "-e", "--example", help="Target example(s)."),
    all_targets: bool = typer.Option(False, "-a", "--all", help="Run across all packages."),
    fix: bool = typer.Option(False, "--fix", help="Automatically apply autofixes."),
    skip: list[str] | None = typer.Option(
        None, "--skip", help="Specific pipeline step(s) to skip (repeatable)."
    ),
    numprocesses: str = typer.Option(
        "auto",
        "-n",
        "--numprocesses",
        "--parallelism",
        help="Concurrency width ('auto' for cores - 2, or 1..num_cores).",
    ),
    sequential: bool = typer.Option(
        False,
        "--sequential",
        help="Execute checks sequentially (equivalent to -n 1).",
    ),
    max_complexity: int = typer.Option(
        25, "-mx", "--max-complexity", help="Cognitive complexity ceiling."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
    skip_steps: set[str] | None = None,
    files: list[str] | None = typer.Argument(None, help="Specific files or directories to verify."),
) -> None:
    """Execute the sanity check pipeline (alias for 'check').

    Args:
        packages: Optional sequence of package names to audit.
        examples: Optional sequence of example project names to audit.
        all_targets: Whether to audit all packages unconditionally.
        fix: Whether to auto-apply formatting and lint fixes.
        skip: Optional list of explicit step names to skip.
        numprocesses: Concurrency width ('auto' for cores - 2, or 1..num_cores).
        sequential: Whether to execute checks sequentially (equivalent to -n 1).
        max_complexity: Cognitive complexity ceiling.
        format_type: Output presentation format.
        skip_steps: Step names dynamically skipped via CLI flags.
        files: Optional explicit file or directory targets.

    Raises:
        typer.Exit: If any sanity checks fail.

    Notes/Architectural Intent:
        Convenience alias matching legacy sanity-check naming.
    """
    _execute_sanity_pipeline(
        packages=packages,
        examples=examples,
        all_targets=all_targets,
        fix=fix,
        skip=skip,
        max_complexity=max_complexity,
        format_type=format_type,
        skip_steps=skip_steps,
        files=files,
        numprocesses=numprocesses,
        sequential=sequential,
    )


def complexity(
    max_complexity: int = typer.Option(
        25, "-mx", "--max-complexity", help="Maximum cognitive complexity ceiling."
    ),
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    files: list[str] | None = typer.Argument(None, help="Target file(s) or directories."),
) -> None:
    """Audit cognitive complexity using complexipy.

    Args:
        max_complexity: Maximum allowed cognitive complexity score.
        packages: Target packages to check.
        files: Target files or directories.

    Raises:
        typer.Exit: If complexity violations are detected.

    Notes/Architectural Intent:
        Driving adapter invoking ToolRunnerPort.run_complexipy across targets.
    """
    from pathlib import Path

    from hexaqual.adapters.runners.subprocess_runner import SubprocessToolRunnerAdapter
    from hexaqual.adapters.workspace import (
        get_package_directories,
        get_package_directory,
        get_repo_root,
    )
    from hexaqual.domain.governance import CheckStatus

    root = get_repo_root()
    runner = SubprocessToolRunnerAdapter()
    target_paths: list[Path] = []
    if files:
        target_paths.extend(Path(f) for f in files)
    elif packages:
        target_paths.extend(get_package_directory(p, root) for p in packages)
    else:
        target_paths.extend(get_package_directories(root))

    result = runner.run_complexipy(
        paths=tuple(target_paths),
        target_name="workspace",
        max_complexity=max_complexity,
    )
    if result.status == CheckStatus.FAIL:
        if result.error_output:
            typer.echo(result.error_output, err=True)
        raise typer.Exit(code=1)


def register_check_commands(app: typer.Typer) -> None:
    """Register check, sanity, and complexity commands on the root Typer application.

    Args:
        app: Target root Typer application.

    Notes/Architectural Intent:
        Attaches top-level root commands without introducing sub-app nesting.
    """
    app.command("check")(check)
    app.command("sanity")(sanity)
    app.command("complexity")(complexity)
