"""Ports defining abstract contracts for mutation testing, boundary audits, and test execution.

Notes/Architectural Intent:
    Decouples mutation testing (mutmut), coverage inspection (.coverage SQLite),
    and test runners (pytest) from domain logic and output presentation formats.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from hexaqual.domain.testing import (
    BoundaryAuditReport,
    ImpactedTestsReport,
    MutationAuditReport,
    MutationEngine,
    RedundancyAuditReport,
)

__all__ = [
    "TestingPresenterPort",
    "TestingRunnerPort",
]


class TestingRunnerPort(ABC):
    """Abstract port for subprocess tool execution and coverage/mutmut database access."""

    @abstractmethod
    def run_mutation_testing(
        self,
        package_dir: Path,
        engine: MutationEngine = MutationEngine.GREMLINS,
        reset_cache: bool = False,
        workers: int | str | None = None,
        numprocesses: int | str | None = None,
        batch_size: int | None = None,
        report_file: Path | None = None,
    ) -> int:
        """Run mutation testing on a specific package directory.

        Args:
            package_dir: Directory path of package to mutate.
            engine: Mutation engine to use (e.g. GREMLINS or MUTMUT).
            reset_cache: Whether to clear incremental analysis cache.
            workers: Number of mutation workers (or 'auto') during mutation phase.
            numprocesses: Pytest-xdist worker count for baseline test execution.
            batch_size: Number of gremlins per worker batch.
            report_file: Path to write the JSON report.

        Returns:
            Exit code of mutation testing process.

        Notes/Architectural Intent:
            Engine-agnostic port interface for executing mutation testing. Decouples
            execution orchestration from specific tool CLI flags or subprocess invocations.
        """

    @abstractmethod
    def read_mutation_records(
        self,
        path: Path,
        engine: MutationEngine = MutationEngine.GREMLINS,
        package_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read surviving and timeout mutants from cache database or report.

        Args:
            path: Path to cache file or JSON report file.
            engine: Mutation engine corresponding to the cache or report format.
            package_filter: Optional package name filter.

        Returns:
            List of mutant records as raw dictionaries.

        Notes/Architectural Intent:
            Converts engine-specific mutant records into uniform raw mutant dictionaries
            compatible with downstream triage classification.
        """

    @abstractmethod
    def get_changed_lines(
        self, repo_root: Path, base_ref: str | None = None
    ) -> dict[Path, set[int]]:
        """Get added and modified lines per file from git diff.

        Args:
            repo_root: Root directory of git workspace.
            base_ref: Optional git commit/ref to compare against.

        Returns:
            Mapping of file Path to set of 1-based line numbers.
        """

    @abstractmethod
    def find_impacted_tests(
        self, changed_lines: dict[Path, set[int]], cov_path: Path | None = None
    ) -> set[str]:
        """Map changed lines to test contexts in .coverage.

        Args:
            changed_lines: Mapping of file Path to modified line numbers.
            cov_path: Optional path to .coverage database.

        Returns:
            Set of pytest test node IDs.
        """

    @abstractmethod
    def get_tests_covering_line(
        self, file_path: str | Path, line_number: int, cov_path: Path | None = None
    ) -> list[str]:
        """Find non-empty test contexts covering a specific file line.

        Args:
            file_path: Source file path.
            line_number: 1-based line number.
            cov_path: Optional path to .coverage database.

        Returns:
            List of covering test context strings.
        """

    @abstractmethod
    def audit_layer_boundary_leaks(self, cov_path: Path | None = None) -> list[tuple[str, str]]:
        """Query .coverage database for domain tests executing infra/adapter files.

        Args:
            cov_path: Optional path to .coverage database.

        Returns:
            List of (test_context, leaked_path) tuples.
        """

    @abstractmethod
    def audit_redundant_tests(self, cov_path: Path | None = None) -> list[str]:
        """Query .coverage branch arcs for tests with zero unique branch coverage.

        Args:
            cov_path: Optional path to .coverage database.

        Returns:
            List of redundant test context strings.
        """

    @abstractmethod
    def execute_pytest(
        self,
        test_nodes: list[str],
        extra_args: list[str] | None = None,
        cwd: Path | None = None,
    ) -> int:
        """Run pytest with specific test node IDs.

        Args:
            test_nodes: List of pytest test node ID targets.
            extra_args: Extra CLI arguments passed to pytest.
            cwd: Optional working directory for pytest execution.

        Returns:
            Exit code of pytest execution.
        """


class TestingPresenterPort(ABC):
    """Abstract port for rendering mutation and test rigor diagnostics."""

    @abstractmethod
    def present_mutation_summary(self, report: MutationAuditReport) -> int:
        """Render high-level mutation triage summary table across packages.

        Args:
            report: MutationAuditReport domain model.

        Returns:
            Exit code (0 if zero critical mutants, 1 otherwise).
        """

    @abstractmethod
    def present_actionable_mutants(self, report: MutationAuditReport) -> int:
        """Render detailed actionable/critical mutants table.

        Args:
            report: MutationAuditReport domain model.

        Returns:
            Exit code (0 if zero critical mutants, 1 otherwise).
        """

    @abstractmethod
    def present_boundary_audit(self, report: BoundaryAuditReport) -> int:
        """Render layer boundary leaks diagnostic table.

        Args:
            report: BoundaryAuditReport domain model.

        Returns:
            Exit code (0 if clean, 1 if boundary leaks exist).
        """

    @abstractmethod
    def present_redundancy_audit(self, report: RedundancyAuditReport) -> int:
        """Render redundant test suite table.

        Args:
            report: RedundancyAuditReport domain model.

        Returns:
            Exit code (0 for success).
        """

    @abstractmethod
    def present_impact_analysis(self, report: ImpactedTestsReport) -> int:
        """Render test impact analysis results or run status.

        Args:
            report: ImpactedTestsReport domain model.

        Returns:
            Exit code of test execution or impact analysis.
        """
