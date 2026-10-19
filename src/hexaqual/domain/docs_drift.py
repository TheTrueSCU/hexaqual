"""Domain models for documentation prose data drift auditing and repair.

Notes/Architectural Intent:
    Encapsulates diagnostic findings and aggregate reports for documentation
    prose data drift (e.g. stale versions, out-of-sync monorepo package counts,
    and conflicting ADR indices) without presentation or filesystem coupling.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexaqual.domain.base import Command

__all__ = [
    "AuditDocsDriftCommand",
    "DocDriftFinding",
    "DocDriftReport",
]


@dataclass(frozen=True)
class DocDriftFinding:
    """Represents a single detected documentation prose drift violation.

    Attributes:
        file_path: Relative or absolute path to markdown file.
        line_number: Line number where drift was detected.
        drift_type: Classification (e.g. 'version_mismatch', 'package_count_mismatch').
        matched_text: The literal text found in documentation.
        expected_text: The expected authoritative value.
        snippet: The context line snippet.
        fixable: Whether this drift can be automatically repaired.

    Notes/Architectural Intent:
        Encapsulates individual drift occurrences for multi-format presentation.
    """

    file_path: str
    line_number: int
    drift_type: str
    matched_text: str
    expected_text: str
    snippet: str
    fixable: bool = True


@dataclass(frozen=True)
class DocDriftReport:
    """Aggregate summary report of documentation prose data drift audit.

    Attributes:
        scanned_files_count: Total markdown documents audited.
        findings: Tuple of detected drift violations.
        fixed_count: Number of drift violations automatically remediated.
        is_successful: True if no un-remediated drift violations remain.
        canonical_version: Authoritative version detected from pyproject.toml.
        package_count: Authoritative package count for monorepos.

    Notes/Architectural Intent:
        Represents the immutable aggregate output of docs drift auditing suitable
        for Rich console tables or automated CI gates.
    """

    scanned_files_count: int = 0
    findings: tuple[DocDriftFinding, ...] = ()
    fixed_count: int = 0
    is_successful: bool = True
    canonical_version: str = ""
    package_count: int = 0


class AuditDocsDriftCommand(Command):
    """CQRS Command to audit or repair prose data drift across documentation.

    Attributes:
        path: Optional specific file or directory path to audit.
        repo_root: Optional workspace repository root path.
        fix: Whether to automatically repair fixable drift in-place.

    Notes/Architectural Intent:
        Dispatches prose data drift analysis through the governance pipeline.
    """

    path: str | None = None
    repo_root: str | None = None
    fix: bool = False
