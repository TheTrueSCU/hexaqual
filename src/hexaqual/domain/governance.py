"""Domain models and CQRS commands for repository governance and sanity verification.

Notes/Architectural Intent:
    Pure domain models defining verification commands, results, and targets.
    Maintains zero external framework dependencies beyond hexastack_core primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from hexaqual.domain.base import Command

__all__ = [
    "AuditComplexityCommand",
    "CheckAllStatementsCommand",
    "CheckDiagramsCommand",
    "CheckResult",
    "CheckStatus",
    "CheckTestParityCommand",
    "DiagramAuditTask",
    "RunDeptryCommand",
    "RunLinterCommand",
    "RunPytestCommand",
    "RunSanityCheckCommand",
    "RunTypecheckCommand",
    "SanityCheckReport",
    "SanityTarget",
    "UNSET",
]


class _UnsetType:
    """Sentinel type representing an unset argument or value."""

    def __repr__(self) -> str:
        return "<UNSET>"

    def __bool__(self) -> bool:
        return False


UNSET: Any = _UnsetType()


class CheckStatus(StrEnum):
    """Execution status of a single governance check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class SanityTarget:
    """Target component scoped for governance checks."""

    name: str
    kind: str  # "package", "example", "file"
    path: Path
    src_paths: tuple[Path, ...]
    test_paths: tuple[Path, ...]


@dataclass(frozen=True)
class DiagramAuditTask:
    """Specification for auditing or generating a package diagram."""

    target: SanityTarget
    repo_root: Path
    fix: bool = False


@dataclass(frozen=True)
class CheckResult:
    """Outcome and diagnostics for a single verification step."""

    check_name: str
    target_name: str
    status: CheckStatus
    duration: float
    details: str = ""
    error_output: str = ""


@dataclass(frozen=True)
class SanityCheckReport:
    """Aggregated report across all executed sanity checks."""

    results: tuple[CheckResult, ...]
    total_duration: float
    exit_code: int


class RunLinterCommand(Command):
    """Command requesting linting and code formatting check."""

    paths: tuple[Path, ...]
    target_name: str
    fix: bool = False


class RunTypecheckCommand(Command):
    """Command requesting static type checking."""

    paths: tuple[Path, ...]
    target_name: str


class AuditComplexityCommand(Command):
    """Command requesting cognitive complexity audit."""

    paths: tuple[Path, ...]
    target_name: str
    max_complexity: int = 25


class CheckAllStatementsCommand(Command):
    """Command requesting __all__ export integrity verification."""

    paths: tuple[Path, ...]
    target_name: str
    fix: bool = False


class CheckTestParityCommand(Command):
    """Command requesting 1:1 unit test symmetry check."""

    target: SanityTarget
    repo_root: Path


class RunDeptryCommand(Command):
    """Command requesting deptry dependency audit."""

    target: SanityTarget
    skip: bool = False


class RunPytestCommand(Command):
    """Command requesting test suite execution."""

    target: SanityTarget
    repo_root: Path
    skip: bool = False


class CheckDiagramsCommand(Command):
    """CQRS Command to verify or fix architecture dependency diagrams for a target.

    Attributes:
        target: Target component to audit.
        repo_root: Repository root path.
        fix: Whether to automatically regenerate stale diagrams.
        skip: Whether to skip running diagram checks.

    Notes/Architectural Intent:
        Dispatched during sanity check battery to verify or update SVG architecture diagrams.
    """

    target: SanityTarget
    repo_root: Path
    fix: bool = False
    skip: bool = False
    precomputed_result: Any = UNSET


class RunSanityCheckCommand(Command):
    """Composite command orchestrating full sanity check battery across targets."""

    targets: tuple[SanityTarget, ...]
    repo_root: Path
    fix: bool = False
    skip_tests: bool = False
    skip_deptry: bool = False
    skip_typecheck: bool = False
    skip_complexity: bool = False
    skip_parity: bool = False
    skip_all_statements: bool = False
    skip_diagrams: bool = False
    skip_steps: tuple[str, ...] = ()
    max_complexity: int = 25
