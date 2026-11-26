"""Domain models and CQRS commands for auto-detecting IaC quality and security gates.

Notes/Architectural Intent:
    Pure domain value objects, enumerations, aggregate reports, and commands
    for Infrastructure-as-Code linting, formatting, and misconfiguration scanning
    (OpenTofu/Terraform, Docker, Kubernetes/Helm, and Shell scripts).
    Maintains zero external framework dependencies and zero disk/subprocess I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from hexaqual.domain.base import Command

__all__ = [
    "DiscoverIacAssetsCommand",
    "IacAssetInventory",
    "IacAuditReport",
    "IacCategory",
    "IacCheckStatus",
    "IacFinding",
    "IacInventoryReport",
    "IacSeverity",
    "IacToolAvailability",
    "IacToolName",
    "IacToolResult",
    "normalize_severity",
    "RunIacAuditCommand",
]


class IacCategory(StrEnum):
    """Infrastructure-as-Code technology domain categories."""

    OPENTOFU = "opentofu"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    SHELL = "shell"


class IacToolName(StrEnum):
    """Canonical identifiers for supported IaC linters, validators, and scanners."""

    TOFU_FMT = "tofu-fmt"
    TOFU_VALIDATE = "tofu-validate"
    TFLINT = "tflint"
    TRIVY = "trivy"
    CHECKOV = "checkov"
    HADOLINT = "hadolint"
    SHELLCHECK = "shellcheck"


class IacCheckStatus(StrEnum):
    """Execution status of an individual IaC audit tool."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class IacSeverity(StrEnum):
    """Normalized severity levels across heterogeneous IaC analyzers."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    UNKNOWN = "UNKNOWN"


_SEVERITY_MAP: dict[str, IacSeverity] = {
    "critical": IacSeverity.CRITICAL,
    "crit": IacSeverity.CRITICAL,
    "high": IacSeverity.HIGH,
    "error": IacSeverity.HIGH,
    "err": IacSeverity.HIGH,
    "medium": IacSeverity.MEDIUM,
    "med": IacSeverity.MEDIUM,
    "warning": IacSeverity.MEDIUM,
    "warn": IacSeverity.MEDIUM,
    "low": IacSeverity.LOW,
    "info": IacSeverity.INFO,
    "informational": IacSeverity.INFO,
    "style": IacSeverity.INFO,
    "notice": IacSeverity.INFO,
}


def normalize_severity(raw: str | None) -> IacSeverity:
    """Normalize heterogeneous tool severity strings to canonical ``IacSeverity``.

    Args:
        raw: Optional raw severity or level token emitted by an analyzer.

    Returns:
        Normalized ``IacSeverity`` enum member.

    Raises:
        None.

    Notes/Architectural Intent:
        Maps tool-specific terms (such as ``error`` from ``tofu validate`` or
        ``style`` from ``shellcheck``/``hadolint``) into a unified severity scale.
    """
    if not raw:
        return IacSeverity.UNKNOWN
    return _SEVERITY_MAP.get(raw.strip().casefold(), IacSeverity.UNKNOWN)


@dataclass(frozen=True)
class IacFinding:
    """Single lint, validation, formatting, or misconfiguration finding."""

    tool: IacToolName
    category: IacCategory
    file_path: str
    line: int | None = None
    rule_id: str = ""
    severity: IacSeverity = IacSeverity.MEDIUM
    message: str = ""
    remediation: str = ""


@dataclass(frozen=True)
class IacToolResult:
    """Execution result for a single IaC analyzer invocation."""

    tool: IacToolName
    category: IacCategory
    status: IacCheckStatus
    duration: float = 0.0
    targets_checked: int = 0
    findings: tuple[IacFinding, ...] = ()
    details: str = ""
    error_output: str = ""


@dataclass(frozen=True)
class IacAssetInventory:
    """Auto-discovered IaC artifacts within a repository or scoped path set."""

    tofu_dirs: tuple[Path, ...] = ()
    tofu_files: tuple[Path, ...] = ()
    dockerfiles: tuple[Path, ...] = ()
    k8s_paths: tuple[Path, ...] = ()
    shell_scripts: tuple[Path, ...] = ()

    @property
    def has_any(self) -> bool:
        """Return True if at least one IaC artifact was discovered."""
        return bool(
            self.tofu_dirs
            or self.tofu_files
            or self.dockerfiles
            or self.k8s_paths
            or self.shell_scripts
        )

    @property
    def total_files(self) -> int:
        """Return total count of discovered IaC files and chart paths."""
        return (
            len(self.tofu_files)
            + len(self.dockerfiles)
            + len(self.k8s_paths)
            + len(self.shell_scripts)
        )


@dataclass(frozen=True)
class IacToolAvailability:
    """Installation availability metadata for an external IaC binary."""

    tool: IacToolName
    binary: str
    installed: bool
    resolved_path: str = ""


@dataclass(frozen=True)
class IacInventoryReport:
    """Report capturing discovered IaC assets and external tool readiness."""

    repo_root: Path
    inventory: IacAssetInventory
    tools: tuple[IacToolAvailability, ...] = ()


@dataclass(frozen=True)
class IacAuditReport:
    """Aggregated outcome across all executed IaC quality and security gates."""

    repo_root: Path
    inventory: IacAssetInventory
    results: tuple[IacToolResult, ...] = ()
    total_duration: float = 0.0
    exit_code: int = 0

    @property
    def findings(self) -> tuple[IacFinding, ...]:
        """Return flattened tuple of all findings across executed tools."""
        collected: list[IacFinding] = []
        for res in self.results:
            collected.extend(res.findings)
        return tuple(collected)

    @property
    def is_clean(self) -> bool:
        """Return True when the aggregated audit completed without failures."""
        return self.exit_code == 0


class DiscoverIacAssetsCommand(Command):
    """CQRS command requesting IaC artifact discovery and tool readiness audit."""

    repo_root: Path
    paths: tuple[Path, ...] = ()


class RunIacAuditCommand(Command):
    """CQRS command requesting auto-detecting IaC lint, validation, and security checks."""

    repo_root: Path
    paths: tuple[Path, ...] = ()
    tools: tuple[IacToolName, ...] = ()
    skip_tools: tuple[IacToolName, ...] = ()
    fix: bool = False
    init_tofu: bool = False
    strict: bool = False
    severity: str = "HIGH,CRITICAL"
    shellcheck_severity: str = "warning"
    hadolint_threshold: str = "warning"
