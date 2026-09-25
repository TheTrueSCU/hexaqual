"""CQRS Command Handlers for repository governance and sanity verification.

Notes/Architectural Intent:
    Decouples verification business logic from execution mechanisms. Each check
    is a discrete CommandHandler, and RunSanityCheckHandler composites sub-checks
    by dispatching sub-commands directly across the CommandBusPort.
"""

from __future__ import annotations

import shutil
import time
from typing import Any

from hexaflow import (
    ExecutionPool,
    InMemoryStateStore,
    StageExecutionMode,
    StepContext,
    StepStatus,
    TriggerRule,
    Workflow,
)

from hexaqual.adapters.code_analysis.pydeps import audit_single_target_diagram
from hexaqual.domain.governance import (
    UNSET,
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckDiagramsCommand,
    CheckResult,
    CheckStatus,
    CheckTestParityCommand,
    DiagramAuditTask,
    RunDeptryCommand,
    RunLinterCommand,
    RunPytestCommand,
    RunSanityCheckCommand,
    RunTypecheckCommand,
    SanityCheckReport,
    SanityTarget,
)
from hexaqual.infra.dispatcher import CommandDispatcher
from hexaqual.ports.governance import ToolRunnerPort

__all__ = [
    "AuditComplexityHandler",
    "CheckAllStatementsHandler",
    "CheckDiagramsHandler",
    "CheckTestParityHandler",
    "RunDeptryHandler",
    "RunLinterHandler",
    "RunPytestHandler",
    "RunSanityCheckHandler",
    "RunTypecheckHandler",
]


def _audit_diagram_worker(task: DiagramAuditTask) -> CheckResult:
    """Top-level worker function executed across ProcessPoolExecutor workers.

    Args:
        task: DiagramAuditTask specifying target, repo root, and fix flag.

    Returns:
        CheckResult containing outcome and timing diagnostics.

    Notes/Architectural Intent:
        Must be a top-level module function to support Python multiprocessing spawn.
    """
    return audit_single_target_diagram(task.target, task.repo_root, fix=task.fix)


class RunLinterHandler:
    """Handler executing lint and formatting checks via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: RunLinterCommand) -> CheckResult:
        """Execute linter check.

        Args:
            command: RunLinterCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_ruff(command.paths, command.target_name, fix=command.fix)


class RunTypecheckHandler:
    """Handler executing static typechecks via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: RunTypecheckCommand) -> CheckResult:
        """Execute typecheck.

        Args:
            command: RunTypecheckCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_ty(command.paths, command.target_name)


class AuditComplexityHandler:
    """Handler auditing cognitive complexity via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: AuditComplexityCommand) -> CheckResult:
        """Execute complexity audit.

        Args:
            command: AuditComplexityCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_complexipy(
            command.paths, command.target_name, max_complexity=command.max_complexity
        )


class CheckAllStatementsHandler:
    """Handler verifying __all__ integrity via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: CheckAllStatementsCommand) -> CheckResult:
        """Execute __all__ check.

        Args:
            command: CheckAllStatementsCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_all_statements(command.paths, command.target_name, fix=command.fix)


class CheckTestParityHandler:
    """Handler validating unit test symmetry via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: CheckTestParityCommand) -> CheckResult:
        """Execute parity audit.

        Args:
            command: CheckTestParityCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_test_parity(command.target, command.repo_root)


class CheckDiagramsHandler:
    """Handler validating or updating architecture diagrams via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: CheckDiagramsCommand) -> CheckResult:
        """Execute architecture diagram audit.

        Args:
            command: CheckDiagramsCommand specification.

        Returns:
            CheckResult outcome.
        """
        if command.skip:
            return CheckResult(
                "Architecture Diagrams",
                command.target.name,
                CheckStatus.SKIP,
                0.0,
                "Skipped via --skip-diagrams",
            )
        if command.precomputed_result is not UNSET:
            return command.precomputed_result
        return self._runner.run_diagrams(command.target, command.repo_root, fix=command.fix)


class RunDeptryHandler:
    """Handler executing deptry dependency audits via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: RunDeptryCommand) -> CheckResult:
        """Execute deptry audit.

        Args:
            command: RunDeptryCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_deptry(command.target, skip=command.skip)


class RunPytestHandler:
    """Handler executing test suites via ToolRunnerPort."""

    def __init__(self, runner: ToolRunnerPort) -> None:
        """Initialize with tool runner port.

        Args:
            runner: Concrete ToolRunnerPort implementation.
        """
        self._runner = runner

    def handle(self, command: RunPytestCommand) -> CheckResult:
        """Execute test runner.

        Args:
            command: RunPytestCommand specification.

        Returns:
            CheckResult outcome.
        """
        return self._runner.run_pytest(command.target, command.repo_root, skip=command.skip)


class RunSanityCheckHandler:
    """Composite handler orchestrating complete sanity check battery across targets.

    Notes/Architectural Intent:
        Dispatches individual domain commands across the CommandBusPort, compositing
        results and calculating total runtime and overall exit status.
    """

    def __init__(self, bus: CommandDispatcher) -> None:
        """Initialize composite handler with CommandBusPort.

        Args:
            bus: CommandDispatcher instance for sub-command dispatch.
        """
        self._bus = bus

    @staticmethod
    def _build_skip_set(command: RunSanityCheckCommand) -> set[str]:
        """Aggregate all step names to skip based on explicit flags and step list."""
        skip_set = set(command.skip_steps)
        if command.skip_tests:
            skip_set.add("pytest")
        if command.skip_deptry:
            skip_set.add("deptry")
        if command.skip_typecheck:
            skip_set.add("typecheck")
        if command.skip_complexity:
            skip_set.add("complexity")
        if command.skip_parity:
            skip_set.add("test_parity")
        if command.skip_all_statements:
            skip_set.add("all_statements")
        if command.skip_diagrams:
            skip_set.add("diagrams")
        return skip_set

    def _audit_all_diagrams_parallel(
        self,
        command: RunSanityCheckCommand,
    ) -> dict[str, CheckResult]:
        """Audit package diagrams in parallel using hexaflow ProcessPoolExecutor.

        Args:
            command: RunSanityCheckCommand specification.

        Returns:
            Dictionary mapping package names to precomputed CheckResults.

        Notes/Architectural Intent:
            Fans out diagram checking across all CPU cores concurrently via
            hexaflow.Workflow and ExecutionPool.PROCESS, reducing multi-package
            diagram checking from sequential multi-second runs to ~1.2s.
        """
        package_targets = [t for t in command.targets if t.kind == "package"]
        if not package_targets:
            return {}

        pydeps_dir = command.repo_root / "docs" / "assets" / "pydeps"
        if not pydeps_dir.is_dir():
            return {
                target.name: CheckResult(
                    "Architecture Diagrams",
                    target.name,
                    CheckStatus.SKIP,
                    0.0,
                    "No docs/assets/pydeps directory",
                )
                for target in package_targets
            }

        if shutil.which("dot") is None:
            return {
                target.name: CheckResult(
                    "Architecture Diagrams",
                    target.name,
                    CheckStatus.SKIP,
                    0.0,
                    "Graphviz 'dot' not installed",
                )
                for target in package_targets
            }

        if len(package_targets) == 1:
            target = package_targets[0]
            return {
                target.name: audit_single_target_diagram(target, command.repo_root, fix=command.fix)
            }

        tasks = [
            DiagramAuditTask(target=target, repo_root=command.repo_root, fix=command.fix)
            for target in package_targets
        ]

        with Workflow("diagrams-parallel-audit", state_store=InMemoryStateStore()) as wf:

            @wf.step("tasks")
            def _get_diagram_tasks(ctx: StepContext) -> list[DiagramAuditTask]:
                return tasks

            wf.map_step(
                name="diagrams",
                over="tasks",
                pool=ExecutionPool.PROCESS,
            )(_audit_diagram_worker)

            state = wf.run()
            chk = state.step_checkpoints.get("diagrams")
            if chk and isinstance(chk.output_payload, list):
                return {
                    res.target_name: res
                    for res in chk.output_payload
                    if isinstance(res, CheckResult)
                }
        return {}

    def _register_static_checks(
        self,
        wf: Workflow,
        target: SanityTarget,
        command: RunSanityCheckCommand,
        skip_set: set[str],
        diagram_results: dict[str, CheckResult] | None = None,
    ) -> None:
        """Register Stage 1 static checks on the workflow."""
        combined_paths = target.src_paths + target.test_paths
        stage_mode = (
            StageExecutionMode.SEQUENTIAL if command.fix else StageExecutionMode.CONCURRENT_ALL
        )
        step_pool = ExecutionPool.ASYNC if command.fix else ExecutionPool.THREAD
        wf.stage("static_checks", execution_mode=stage_mode)

        @wf.step(
            name="lint",
            stage="static_checks",
            pool=step_pool,
            trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
        )
        def _lint(ctx: StepContext) -> CheckResult:
            if "lint" in skip_set:
                return CheckResult(
                    "Ruff Lint/Format",
                    target.name,
                    CheckStatus.SKIP,
                    0.0,
                    "Skipped via --skip",
                )
            return self._bus.dispatch(
                RunLinterCommand(
                    paths=combined_paths,
                    target_name=target.name,
                    fix=command.fix,
                )
            )

        @wf.step(
            name="all_statements",
            stage="static_checks",
            pool=step_pool,
            trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
        )
        def _all_statements(ctx: StepContext) -> CheckResult:
            if "all_statements" in skip_set or command.skip_all_statements:
                return CheckResult(
                    "__all__ Integrity",
                    target.name,
                    CheckStatus.SKIP,
                    0.0,
                    "Skipped via --skip-statements",
                )
            return self._bus.dispatch(
                CheckAllStatementsCommand(
                    paths=target.src_paths,
                    target_name=target.name,
                    fix=command.fix,
                )
            )

        if target.kind == "package":

            @wf.step(
                name="test_parity",
                stage="static_checks",
                pool=step_pool,
                trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
            )
            def _test_parity(ctx: StepContext) -> CheckResult:
                if "test_parity" in skip_set or command.skip_parity:
                    return CheckResult(
                        "Test Parity",
                        target.name,
                        CheckStatus.SKIP,
                        0.0,
                        "Skipped via --skip-parity",
                    )
                return self._bus.dispatch(
                    CheckTestParityCommand(
                        target=target,
                        repo_root=command.repo_root,
                    )
                )

            @wf.step(
                name="diagrams",
                stage="static_checks",
                pool=step_pool,
                trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
            )
            def _diagrams(ctx: StepContext) -> CheckResult:
                is_skipped = "diagrams" in skip_set or command.skip_diagrams
                if diagram_results is not None and target.name in diagram_results:
                    precomputed = diagram_results[target.name]
                else:
                    precomputed = UNSET
                return self._bus.dispatch(
                    CheckDiagramsCommand(
                        target=target,
                        repo_root=command.repo_root,
                        fix=command.fix,
                        skip=is_skipped,
                        precomputed_result=precomputed,
                    )
                )

    def _register_analysis_checks(
        self,
        wf: Workflow,
        target: SanityTarget,
        command: RunSanityCheckCommand,
        skip_set: set[str],
    ) -> None:
        """Register Stage 2 deep analysis checks on the workflow."""
        combined_paths = target.src_paths + target.test_paths
        wf.stage("analysis", execution_mode=StageExecutionMode.CONCURRENT_ALL)

        @wf.step(
            name="typecheck",
            stage="analysis",
            depends_on=["lint"],
            pool=ExecutionPool.THREAD,
            trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
        )
        def _typecheck(ctx: StepContext) -> CheckResult:
            if "typecheck" in skip_set or command.skip_typecheck:
                return CheckResult(
                    "Ty Typecheck",
                    target.name,
                    CheckStatus.SKIP,
                    0.0,
                    "Skipped via --skip-typecheck",
                )
            return self._bus.dispatch(
                RunTypecheckCommand(
                    paths=combined_paths,
                    target_name=target.name,
                )
            )

        @wf.step(
            name="complexity",
            stage="analysis",
            depends_on=["lint"],
            pool=ExecutionPool.THREAD,
            trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
        )
        def _complexity(ctx: StepContext) -> CheckResult:
            if "complexity" in skip_set or command.skip_complexity:
                return CheckResult(
                    "Cognitive Complexity",
                    target.name,
                    CheckStatus.SKIP,
                    0.0,
                    "Skipped via --skip-complexity",
                )
            return self._bus.dispatch(
                AuditComplexityCommand(
                    paths=target.src_paths,
                    target_name=target.name,
                    max_complexity=command.max_complexity,
                )
            )

        if target.kind == "package":

            @wf.step(
                name="deptry",
                stage="analysis",
                depends_on=["lint"],
                pool=ExecutionPool.THREAD,
                trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
            )
            def _deptry(ctx: StepContext) -> CheckResult:
                is_skipped = "deptry" in skip_set or command.skip_deptry
                return self._bus.dispatch(
                    RunDeptryCommand(
                        target=target,
                        skip=is_skipped,
                    )
                )

    def _register_verification_checks(
        self,
        wf: Workflow,
        target: SanityTarget,
        command: RunSanityCheckCommand,
        skip_set: set[str],
    ) -> None:
        """Register Stage 3 pytest verification on the workflow."""

        @wf.step(
            name="pytest",
            stage="verification",
            depends_on=["typecheck", "complexity"],
            trigger_rule=TriggerRule.ALL_SUCCESS_OR_SKIPPED,
        )
        def _pytest(ctx: StepContext) -> CheckResult:
            is_skipped = "pytest" in skip_set or command.skip_tests
            return self._bus.dispatch(
                RunPytestCommand(
                    target=target,
                    repo_root=command.repo_root,
                    skip=is_skipped,
                )
            )

    @staticmethod
    def _collect_workflow_results(
        state: Any,
        target: SanityTarget,
    ) -> list[CheckResult]:
        """Collect and order CheckResult outcomes from workflow state."""
        expected_step_order = ["lint", "typecheck", "complexity", "all_statements"]
        if target.kind == "package":
            expected_step_order.extend(["test_parity", "diagrams", "deptry"])
        expected_step_order.append("pytest")

        step_display_names = {
            "lint": "Ruff Lint/Format",
            "typecheck": "Ty Typecheck",
            "complexity": "Cognitive Complexity",
            "all_statements": "__all__ Integrity",
            "test_parity": "Test Parity",
            "diagrams": "Architecture Diagrams",
            "deptry": "Deptry Audit",
            "pytest": "Pytest Suite",
        }

        results: list[CheckResult] = []
        for step_name in expected_step_order:
            cp = state.step_checkpoints.get(step_name)
            if cp and cp.status == StepStatus.SKIPPED:
                display_name = step_display_names.get(step_name, step_name)
                results.append(
                    CheckResult(
                        check_name=display_name,
                        target_name=target.name,
                        status=CheckStatus.SKIP,
                        duration=cp.duration_seconds or 0.0,
                        details="Skipped via skip filter",
                    )
                )
            elif cp and isinstance(cp.output_payload, CheckResult):
                results.append(cp.output_payload)
            elif cp and cp.error_traceback:
                results.append(
                    CheckResult(
                        check_name=step_name,
                        target_name=target.name,
                        status=CheckStatus.FAIL,
                        duration=0.0,
                        details="Step execution failed",
                        error_output=cp.error_traceback,
                    )
                )
        return results

    def _execute_target_checks(
        self,
        target: SanityTarget,
        command: RunSanityCheckCommand,
        diagram_results: dict[str, CheckResult] | None = None,
    ) -> list[CheckResult]:
        """Execute standard check battery for a single target via a hexaflow Workflow DAG.

        Notes/Architectural Intent:
            Dogfoods hexaflow to organize checks into a directed acyclic graph.
            Static leaf checks (lint, all_statements, test_parity) run first,
            followed by static analysis (typecheck, complexity, deptry) and dynamic test
            execution (pytest), collecting CheckResults through step checkpoints.
        """
        skip_set = self._build_skip_set(command)
        with Workflow(
            f"sanity-{target.name}",
            state_store=InMemoryStateStore(),
        ) as wf:
            self._register_static_checks(
                wf, target, command, skip_set, diagram_results=diagram_results
            )
            self._register_analysis_checks(wf, target, command, skip_set)
            self._register_verification_checks(wf, target, command, skip_set)
            state = wf.run()
            return self._collect_workflow_results(state, target)

    def handle(self, command: RunSanityCheckCommand) -> SanityCheckReport:
        """Execute composite sanity check battery.

        Args:
            command: RunSanityCheckCommand specification.

        Returns:
            SanityCheckReport aggregate.
        """
        start = time.perf_counter()
        skip_set = self._build_skip_set(command)

        diagram_results: dict[str, CheckResult] = {}
        if "diagrams" not in skip_set and not command.skip_diagrams:
            diagram_results = self._audit_all_diagrams_parallel(command)

        all_results: list[CheckResult] = []
        for target in command.targets:
            all_results.extend(
                self._execute_target_checks(target, command, diagram_results=diagram_results)
            )

        total_duration = time.perf_counter() - start
        has_failure = any(r.status == CheckStatus.FAIL for r in all_results)
        exit_code = 1 if has_failure else 0

        return SanityCheckReport(
            results=tuple(all_results),
            total_duration=total_duration,
            exit_code=exit_code,
        )
