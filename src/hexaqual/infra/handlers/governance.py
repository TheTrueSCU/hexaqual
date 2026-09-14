"""CQRS Command Handlers for repository governance and sanity verification.

Notes/Architectural Intent:
    Decouples verification business logic from execution mechanisms. Each check
    is a discrete CommandHandler, and RunSanityCheckHandler composites sub-checks
    by dispatching sub-commands directly across the CommandBusPort.
"""

from __future__ import annotations

import time
from typing import Any

from hexaflow import InMemoryStateStore, StepContext, Workflow

from hexaqual.domain.governance import (
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckResult,
    CheckStatus,
    CheckTestParityCommand,
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
    "CheckTestParityHandler",
    "RunDeptryHandler",
    "RunLinterHandler",
    "RunPytestHandler",
    "RunSanityCheckHandler",
    "RunTypecheckHandler",
]


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
        return skip_set

    def _register_static_checks(
        self,
        wf: Workflow,
        target: SanityTarget,
        command: RunSanityCheckCommand,
        skip_set: set[str],
    ) -> None:
        """Register Stage 1 static checks on the workflow."""
        combined_paths = target.src_paths + target.test_paths

        @wf.step(name="lint", stage="static_checks")
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

        @wf.step(name="all_statements", stage="static_checks")
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

            @wf.step(name="test_parity", stage="static_checks")
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

    def _register_analysis_checks(
        self,
        wf: Workflow,
        target: SanityTarget,
        command: RunSanityCheckCommand,
        skip_set: set[str],
    ) -> None:
        """Register Stage 2 deep analysis checks on the workflow."""
        combined_paths = target.src_paths + target.test_paths

        @wf.step(name="typecheck", stage="analysis", depends_on=["lint"])
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

        @wf.step(name="complexity", stage="analysis", depends_on=["lint"])
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

            @wf.step(name="deptry", stage="analysis", depends_on=["lint"])
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
            expected_step_order.extend(["test_parity", "deptry"])
        expected_step_order.append("pytest")

        results: list[CheckResult] = []
        for step_name in expected_step_order:
            cp = state.step_checkpoints.get(step_name)
            if cp and isinstance(cp.output_payload, CheckResult):
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
    ) -> list[CheckResult]:
        """Execute standard check battery for a single target via a hexaflow Workflow DAG.

        Notes/Architectural Intent:
            Dogfoods hexaflow to organize checks into a directed acyclic graph.
            Static leaf checks (lint, all_statements, test_parity) run first,
            followed by static analysis (typecheck, complexity, deptry) and dynamic test
            execution (pytest), collecting CheckResults through step checkpoints.
        """
        skip_set = self._build_skip_set(command)
        wf = Workflow(
            f"sanity-{target.name}",
            state_store=InMemoryStateStore(),
        )
        self._register_static_checks(wf, target, command, skip_set)
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
        all_results: list[CheckResult] = []

        for target in command.targets:
            all_results.extend(self._execute_target_checks(target, command))

        total_duration = time.perf_counter() - start
        has_failure = any(r.status == CheckStatus.FAIL for r in all_results)
        exit_code = 1 if has_failure else 0

        return SanityCheckReport(
            results=tuple(all_results),
            total_duration=total_duration,
            exit_code=exit_code,
        )
