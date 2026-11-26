"""Port contracts for Infrastructure-as-Code discovery, auditing, and presentation.

Notes/Architectural Intent:
    Defines abstract interfaces decoupling IaC file discovery and external tool
    execution (OpenTofu/Terraform, TFLint, Trivy, Checkov, Hadolint, ShellCheck)
    from CQRS orchestration and multi-format presentation adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from hexaqual.domain.iac import (
    IacAssetInventory,
    IacAuditReport,
    IacInventoryReport,
    IacToolAvailability,
    IacToolResult,
)

__all__ = [
    "IacAuditorPort",
    "IacPresenterPort",
]


class IacAuditorPort(ABC):
    """Abstract port for IaC asset discovery, readiness inspection, and tool execution."""

    @abstractmethod
    def discover_assets(
        self,
        repo_root: Path,
        paths: tuple[Path, ...] = (),
    ) -> IacAssetInventory:
        """Discover IaC modules, containers, Kubernetes manifests, and shell scripts.

        Args:
            repo_root: Repository root directory.
            paths: Optional explicit paths narrowing discovery scope.

        Returns:
            Populated ``IacAssetInventory`` describing discovered IaC artifacts.
        """

    @abstractmethod
    def check_tool_availability(self) -> tuple[IacToolAvailability, ...]:
        """Inspect PATH and environment availability for supported IaC binaries.

        Returns:
            Tuple of ``IacToolAvailability`` records for each supported tool.
        """

    @abstractmethod
    def run_tofu_fmt(
        self,
        repo_root: Path,
        tofu_dirs: tuple[Path, ...],
        fix: bool = False,
        strict: bool = False,
    ) -> IacToolResult:
        """Check or apply formatting across OpenTofu / Terraform directories.

        Args:
            repo_root: Repository root directory.
            tofu_dirs: Discovered OpenTofu / Terraform module directories.
            fix: Whether to format files in-place prior to checking.
            strict: Whether missing tool binary counts as failure instead of skip.

        Returns:
            ``IacToolResult`` containing formatting status and findings.
        """

    @abstractmethod
    def run_tofu_validate(
        self,
        repo_root: Path,
        tofu_dirs: tuple[Path, ...],
        init_tofu: bool = False,
        strict: bool = False,
    ) -> IacToolResult:
        """Validate OpenTofu / Terraform configuration syntax and schema.

        Args:
            repo_root: Repository root directory.
            tofu_dirs: Discovered OpenTofu / Terraform module directories.
            init_tofu: Whether to initialize uninitialized modules with ``-backend=false``.
            strict: Whether missing tool binary or uninitialized modules fail instead of skip.

        Returns:
            ``IacToolResult`` containing validation diagnostics.
        """

    @abstractmethod
    def run_tflint(
        self,
        repo_root: Path,
        tofu_dirs: tuple[Path, ...],
        strict: bool = False,
    ) -> IacToolResult:
        """Execute TFLint static analysis across OpenTofu / Terraform directories.

        Args:
            repo_root: Repository root directory.
            tofu_dirs: Discovered OpenTofu / Terraform module directories.
            strict: Whether missing ``tflint`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing TFLint issues and errors.
        """

    @abstractmethod
    def run_trivy(
        self,
        repo_root: Path,
        scan_paths: tuple[Path, ...],
        severity: str = "HIGH,CRITICAL",
        strict: bool = False,
    ) -> IacToolResult:
        """Run Trivy IaC misconfiguration scanning across discovered IaC paths.

        Args:
            repo_root: Repository root directory.
            scan_paths: Deduplicated files and directories to scan.
            severity: Comma-separated Trivy severity filter.
            strict: Whether missing ``trivy`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing misconfiguration findings.
        """

    @abstractmethod
    def run_checkov(
        self,
        repo_root: Path,
        scan_paths: tuple[Path, ...],
        strict: bool = False,
    ) -> IacToolResult:
        """Run Checkov policy-as-code scanning across discovered IaC paths.

        Args:
            repo_root: Repository root directory.
            scan_paths: Deduplicated files and directories to scan.
            strict: Whether missing ``checkov`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing failed Checkov policy checks.
        """

    @abstractmethod
    def run_hadolint(
        self,
        repo_root: Path,
        dockerfiles: tuple[Path, ...],
        failure_threshold: str = "warning",
        strict: bool = False,
    ) -> IacToolResult:
        """Lint discovered Dockerfiles with Hadolint.

        Args:
            repo_root: Repository root directory.
            dockerfiles: Discovered Dockerfile paths.
            failure_threshold: Hadolint ``--failure-threshold`` severity floor.
            strict: Whether missing ``hadolint`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing Dockerfile lint findings.
        """

    @abstractmethod
    def run_shellcheck(
        self,
        repo_root: Path,
        shell_scripts: tuple[Path, ...],
        severity: str = "warning",
        strict: bool = False,
    ) -> IacToolResult:
        """Lint discovered shell scripts with ShellCheck.

        Args:
            repo_root: Repository root directory.
            shell_scripts: Discovered shell script paths.
            severity: Minimum ShellCheck severity to consider (``-S``).
            strict: Whether missing ``shellcheck`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing ShellCheck diagnostics.
        """


class IacPresenterPort(ABC):
    """Abstract port for rendering IaC audit and discovery reports across formats."""

    @abstractmethod
    def present_iac_audit(self, report: IacAuditReport) -> int:
        """Render IaC linting, formatting, and misconfiguration scan outcomes.

        Args:
            report: Aggregated ``IacAuditReport`` domain report.

        Returns:
            Process exit code (0 for pass/clean, 1 for failure).
        """

    @abstractmethod
    def present_iac_inventory(self, report: IacInventoryReport) -> int:
        """Render discovered IaC assets and external tool readiness report.

        Args:
            report: Aggregated ``IacInventoryReport`` domain report.

        Returns:
            Process exit code (0 on success).
        """
