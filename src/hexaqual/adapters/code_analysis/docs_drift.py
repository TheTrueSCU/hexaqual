"""Documentation prose data drift scanner and auto-repair adapter.

Notes/Architectural Intent:
    Audits documentation markdown trees against authoritative project definitions
    (e.g. pyproject.toml canonical version, workspace subpackage counts, and ADR indices)
    to eliminate 'Lying Prose' drift where prose contradicts real code constants.
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from hexaqual.domain.docs_drift import (
    DocDriftFinding,
    DocDriftReport,
)

__all__ = [
    "extract_canonical_version",
    "get_package_count",
    "scan_docs_drift",
]

IGNORED_DIRS = {
    ".cache",
    ".complexipy_cache",
    ".git",
    ".hypothesis",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "dist",
    "graphify-out",
    "node_modules",
    "site",
}

IGNORED_FILES = {
    "CHANGELOG.md",
}

BADGE_VERSION_PATTERN = re.compile(
    r"(https://img\.shields\.io/badge/[a-zA-Z0-9_\-]+-v?)(\d+\.\d+\.\d+)(-[a-zA-Z0-9_\.]+\.svg)"
)
PACKAGE_COUNT_PATTERN = re.compile(
    r"\b((?:all|across|between|in)\s+)(\d+)(\s+(?:workspace\s+)?(?:sub)?packages)\b",
    re.IGNORECASE,
)


def extract_canonical_version(repo_root: Path) -> str:
    """Extract canonical project or workspace version from pyproject.toml.

    Args:
        repo_root: Repository root directory.

    Returns:
        Version string (e.g. '0.9.0') or empty string if not found.

    Notes/Architectural Intent:
        Inspects project.version or tool.poetry.version from root pyproject.toml.
    """
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.is_file():
        return ""

    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project", {})
        if "version" in project and isinstance(project["version"], str):
            return project["version"]
        tool = data.get("tool", {})
        poetry = tool.get("poetry", {})
        if "version" in poetry and isinstance(poetry["version"], str):
            return poetry["version"]
    except Exception:
        return ""
    return ""


def get_package_count(repo_root: Path) -> int:
    """Count active workspace subpackages located in packages/*/pyproject.toml.

    Args:
        repo_root: Repository root directory.

    Returns:
        Total number of subpackages, or 0 if not a monorepo.

    Notes/Architectural Intent:
        Calculates authoritative package count for workspace prose verification.
    """
    packages_dir = repo_root / "packages"
    if not packages_dir.is_dir():
        return 0
    subpkgs = [p for p in packages_dir.glob("*/pyproject.toml") if p.is_file()]
    return len(subpkgs)


def _collect_markdown_files(target_path: Path | None, repo_root: Path) -> list[Path]:
    """Collect candidate markdown files respecting ignore filters."""
    if target_path is not None:
        if target_path.is_file() and target_path.suffix.lower() == ".md":
            return [target_path]
        if target_path.is_dir():
            search_root = target_path
        else:
            return []
    else:
        search_root = repo_root

    files: list[Path] = []
    for p in search_root.rglob("*.md"):
        parts = set(p.parts)
        if parts.intersection(IGNORED_DIRS):
            continue
        if p.name in IGNORED_FILES:
            continue
        files.append(p)

    return sorted(files)


def _format_rel_path(path: Path, root: Path) -> str:
    """Format path relative to root if possible, otherwise string path."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _audit_badge_version(
    line: str,
    line_idx: int,
    rel_path: str,
    canonical_version: str,
    fix: bool,
) -> tuple[list[DocDriftFinding], str, int]:
    """Inspect and optionally repair badge version discrepancies on a single line."""
    findings: list[DocDriftFinding] = []
    if not canonical_version:
        return findings, line, 0

    current_line = line
    fixed_count = 0
    for match in BADGE_VERSION_PATTERN.finditer(current_line):
        found_version = match.group(2)
        if found_version != canonical_version:
            findings.append(
                DocDriftFinding(
                    file_path=rel_path,
                    line_number=line_idx,
                    drift_type="version_mismatch",
                    matched_text=f"v{found_version}",
                    expected_text=f"v{canonical_version}",
                    snippet=line.strip(),
                    fixable=True,
                )
            )
            if fix:
                current_line = BADGE_VERSION_PATTERN.sub(
                    rf"\g<1>{canonical_version}\g<3>", current_line
                )
                fixed_count += 1
    return findings, current_line, fixed_count


def _audit_package_count(
    line: str,
    line_idx: int,
    rel_path: str,
    package_count: int,
    fix: bool,
) -> tuple[list[DocDriftFinding], str, int]:
    """Inspect and optionally repair package count discrepancies on a single line."""
    findings: list[DocDriftFinding] = []
    if package_count <= 0:
        return findings, line, 0

    current_line = line
    fixed_count = 0
    for match in PACKAGE_COUNT_PATTERN.finditer(current_line):
        found_count = int(match.group(2))
        if found_count != package_count:
            findings.append(
                DocDriftFinding(
                    file_path=rel_path,
                    line_number=line_idx,
                    drift_type="package_count_mismatch",
                    matched_text=f"{found_count} packages",
                    expected_text=f"{package_count} packages",
                    snippet=line.strip(),
                    fixable=True,
                )
            )
            if fix:
                current_line = PACKAGE_COUNT_PATTERN.sub(
                    rf"\g<1>{package_count}\g<3>", current_line
                )
                fixed_count += 1
    return findings, current_line, fixed_count


def _scan_single_file(
    file_path: Path,
    root: Path,
    canonical_version: str,
    package_count: int,
    fix: bool,
) -> tuple[list[DocDriftFinding], int]:
    """Audit and optionally repair a single markdown document."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return [], 0

    lines = content.splitlines(keepends=True)
    findings: list[DocDriftFinding] = []
    new_lines: list[str] = []
    fixed_count = 0
    rel_path = _format_rel_path(file_path, root)

    for line_idx, line in enumerate(lines, start=1):
        badge_findings, current_line, badge_fixes = _audit_badge_version(
            line, line_idx, rel_path, canonical_version, fix
        )
        pkg_findings, current_line, pkg_fixes = _audit_package_count(
            current_line, line_idx, rel_path, package_count, fix
        )
        findings.extend(badge_findings)
        findings.extend(pkg_findings)
        fixed_count += badge_fixes + pkg_fixes
        new_lines.append(current_line)

    if fix and fixed_count > 0:
        file_path.write_text("".join(new_lines), encoding="utf-8")

    return findings, fixed_count


def scan_docs_drift(
    target_path: Path | None = None,
    repo_root: Path | None = None,
    fix: bool = False,
) -> DocDriftReport:
    """Scan documentation files for prose data drift and optionally auto-repair them.

    Args:
        target_path: Optional explicit markdown file or directory to scan.
        repo_root: Workspace root directory (defaults to current working directory).
        fix: Whether to write repairs back to disk in-place.

    Returns:
        DocDriftReport containing detected drift violations and remediation counts.

    Notes/Architectural Intent:
        Acts as the primary driven adapter for 'The Lying Prose Linter', comparing
        version badges and monorepo package counts against canonical values.
    """
    if repo_root is not None:
        root = repo_root
    elif target_path is not None:
        root = target_path if target_path.is_dir() else target_path.parent
    else:
        root = Path.cwd()

    canonical_version = extract_canonical_version(root)
    package_count = get_package_count(root)

    md_files = _collect_markdown_files(target_path, root)
    findings: list[DocDriftFinding] = []
    total_fixed = 0

    for file_path in md_files:
        file_findings, fixed = _scan_single_file(
            file_path, root, canonical_version, package_count, fix
        )
        findings.extend(file_findings)
        total_fixed += fixed

    is_successful = len(findings) == 0 or (fix and total_fixed == len(findings))

    return DocDriftReport(
        scanned_files_count=len(md_files),
        findings=tuple(findings),
        fixed_count=total_fixed,
        is_successful=is_successful,
        canonical_version=canonical_version,
        package_count=package_count,
    )
