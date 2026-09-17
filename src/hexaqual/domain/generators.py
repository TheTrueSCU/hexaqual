"""Domain models and CQRS commands for code and documentation generators.

Notes/Architectural Intent:
    Encapsulates command requests and output reports for pydeps dependency
    diagrams, USAGE.md catalog synchronization, and pytest-archon hexagonal
    boundary test scaffolding without subprocess or presentation dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexaqual.domain.base import Command


@dataclass(frozen=True)
class PydepsDiagramResult:
    """Represents a generated or audited pydeps dependency diagram result.

    Attributes:
        name: Name of the package or overview diagram.
        path: Path where the SVG diagram was written or inspected.
        success: Whether the diagram generation or verification succeeded.
        is_stale: Whether the diagram on disk was determined to be out of date.
        details: Diagnostic explanation or failure message.

    Notes/Architectural Intent:
        Encapsulates individual diagram output metadata for multi-format
        presentation and CI verification.
    """

    name: str
    path: str
    success: bool = True
    is_stale: bool = False
    details: str = ""


@dataclass(frozen=True)
class PydepsReport:
    """Summary report of pydeps architecture diagram generation or verification.

    Attributes:
        results: Tuple of generated or audited diagram results.
        is_successful: True if all requested diagrams generated or verified successfully.
        is_check: Whether this report represents a read-only freshness check.

    Notes/Architectural Intent:
        Represents the immutable aggregate output of pydeps diagram generation
        suitable for rich console tables or machine-readable JSON.
    """

    results: tuple[PydepsDiagramResult, ...] = ()
    is_successful: bool = True
    is_check: bool = False


class GeneratePydepsCommand(Command):
    """CQRS Command to generate or verify architecture dependency diagrams via pydeps.

    Attributes:
        packages: Optional tuple of specific package names to process diagrams for.
        check_only: Whether to perform read-only freshness validation without writing files.
        fix: Whether to regenerate diagrams explicitly.

    Notes/Architectural Intent:
        Dispatches diagram generation through the governance bus, decoupling
        the CLI entrypoint from concurrent multiprocessing workers.
    """

    packages: tuple[str, ...] = ()
    check_only: bool = False
    fix: bool = False


@dataclass(frozen=True)
class UsageDocsReport:
    """Summary report of USAGE.md documentation checks or updates.

    Attributes:
        up_to_date_files: Paths to USAGE.md files that are current.
        updated_files: Paths to USAGE.md files that were updated.
        stale_files: Paths to USAGE.md files that are out of date.
        diffs: Tuple of (file_path, diff_content) pairs for stale files.
        is_valid: True if all files are up-to-date (or were successfully fixed).

    Notes/Architectural Intent:
        Supports both read-only validation (pre-commit quality gate) and
        mutation fix mode, reporting unified status across workspace packages.
    """

    up_to_date_files: tuple[str, ...] = ()
    updated_files: tuple[str, ...] = ()
    stale_files: tuple[str, ...] = ()
    diffs: tuple[tuple[str, str], ...] = ()
    is_valid: bool = True


class GenerateUsageDocsCommand(Command):
    """CQRS Command to audit or generate USAGE.md files across the workspace.

    Attributes:
        check_only: Only verify documentation freshness without modifying files.
        fix: Automatically update stale USAGE.md files.
        affected_only: Restrict check/generation to packages affected by git diff.

    Notes/Architectural Intent:
        Decouples CLI argument parsing from parallel help-tree extraction
        and file diffing logic.
    """

    package: str | None = None
    check_only: bool = False
    fix: bool = False
    affected_only: bool = False


@dataclass(frozen=True)
class ArchonReport:
    """Summary report of pytest-archon boundary test scaffolding.

    Attributes:
        generated_files: Paths to created test files.
        skipped_files: Paths to packages skipped because layers were absent.
        is_successful: True if all eligible packages were scaffolded without error.

    Notes/Architectural Intent:
        Captures files created or skipped during archon test scaffolding.
    """

    generated_files: tuple[str, ...] = ()
    skipped_files: tuple[str, ...] = ()
    is_successful: bool = True


class GenerateArchonTestsCommand(Command):
    """CQRS Command to scaffold or regenerate pytest-archon boundary tests.

    Attributes:
        packages: Optional tuple of specific package names to generate tests for.
        force: Overwrite existing test files if True.

    Notes/Architectural Intent:
        Encapsulates pytest-archon boundary test generation parameters.
    """

    packages: tuple[str, ...] = ()
    force: bool = False


@dataclass(frozen=True)
class BrokenDocLink:
    """Represents a broken or invalid link detected within documentation.

    Attributes:
        source_file: Path to the markdown file containing the broken link.
        line: Line number where the broken link appears.
        target: Target URL or relative path referenced.
        reason: Explanation of why the link is considered invalid or broken.

    Notes/Architectural Intent:
        Encapsulates diagnostic data for broken relative paths, missing anchors,
        or dead local files across markdown document trees.
    """

    source_file: str
    line: int
    target: str
    reason: str


@dataclass(frozen=True)
class DocLinksReport:
    """Summary report of documentation link validation.

    Attributes:
        scanned_files_count: Total markdown files inspected.
        total_links_count: Total relative and anchor links validated.
        broken_links: Tuple of broken link diagnostics found.
        is_successful: True if no broken links were detected.

    Notes/Architectural Intent:
        Aggregates documentation link integrity scan results for multi-format
        presentation and automated CI quality gates.
    """

    scanned_files_count: int = 0
    total_links_count: int = 0
    broken_links: tuple[BrokenDocLink, ...] = ()
    is_successful: bool = True


class CheckDocLinksCommand(Command):
    """CQRS Command to validate relative links and anchors across documentation trees.

    Attributes:
        path: Optional path to specific file or directory to scan.
        repo_root: Optional workspace repository root path.

    Notes/Architectural Intent:
        Scans markdown documents for broken local references and anchor links,
        providing an early CI quality gate before documentation is published.
    """

    path: str | None = None
    repo_root: str | None = None


__all__ = [
    "ArchonReport",
    "BrokenDocLink",
    "CheckDocLinksCommand",
    "DocLinksReport",
    "GenerateArchonTestsCommand",
    "GeneratePydepsCommand",
    "GenerateUsageDocsCommand",
    "PydepsDiagramResult",
    "PydepsReport",
    "UsageDocsReport",
]
