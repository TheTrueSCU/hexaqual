"""Documentation markdown link and anchor integrity scanner.

Notes/Architectural Intent:
    Scans markdown files across repository trees to validate relative file paths,
    local anchors, and cross-file references. Provides fast fail-early verification
    before publishing static documentation or pushing commits.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from hexaqual.domain.generators import (
    BrokenDocLink,
    CheckDocLinksCommand,
    DocLinksReport,
)

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

LINK_PATTERN = re.compile(r"\[(?:[^\]]*)\]\(([^)]+)\)")
REF_LINK_PATTERN = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
HTML_ANCHOR_PATTERN = re.compile(r'<a\s+(?:[^>]*\s+)?(?:id|name)=["\']([^"\']+)["\']')


def slugify_heading(heading: str) -> str:
    """Convert a markdown heading string to GitHub/Zensical slugified anchor format.

    Args:
        heading: Raw heading text from markdown.

    Returns:
        Slugified anchor identifier (e.g. 'architecture-overview').

    Notes/Architectural Intent:
        Matches GitHub and Python-Markdown slugification rules by stripping punctuation
        and replacing whitespace with hyphens.
    """
    text = heading.strip().lower()
    text = text.replace("`", "")
    text = re.sub(
        r"<(/?(a|span|div|b|i|strong|em|p|br|code|img|sub|sup|font))(\s+[^>]*)?>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def extract_anchors_from_file(file_path: Path) -> set[str]:
    """Extract all valid heading and HTML anchor identifiers from a markdown file.

    Args:
        file_path: Path to the markdown document.

    Returns:
        Set of valid anchor IDs.

    Notes/Architectural Intent:
        Parses headings and explicit HTML anchors to build a lookup set for link validation.
    """
    anchors: set[str] = set()
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return anchors

    for line in content.splitlines():
        match_heading = HEADING_PATTERN.match(line.strip())
        if match_heading:
            anchors.add(slugify_heading(match_heading.group(2)))
        for match_html in HTML_ANCHOR_PATTERN.finditer(line):
            anchors.add(match_html.group(1).lower())

    return anchors


def _discover_markdown_files(base_path: Path) -> list[Path]:
    """Discover candidate markdown files excluding ignored directories."""
    if base_path.is_file() and base_path.suffix.lower() == ".md":
        return [base_path]
    if base_path.is_dir():
        return [
            p
            for p in sorted(base_path.rglob("*.md"))
            if not any(part in IGNORED_DIRS for part in p.parts)
        ]
    return []


def _extract_raw_links(line: str) -> list[str]:
    """Extract inline and reference link targets from a single text line."""
    links: list[str] = []
    for match in LINK_PATTERN.finditer(line):
        links.append(match.group(1).strip())
    ref_match = REF_LINK_PATTERN.match(line)
    if ref_match:
        links.append(ref_match.group(1).strip())
    return links


def _is_external_link(target: str) -> bool:
    """Return True if link target points to an external URL or protocol."""
    protocols = ("http://", "https://", "mailto:", "ftp:", "data:", "javascript:")
    return any(target.startswith(proto) for proto in protocols)


def _validate_same_file_anchor(
    target: str,
    md_file: Path,
    line_num: int,
    source_rel: str,
    get_anchors: Callable[[Path], set[str]],
) -> BrokenDocLink | None:
    """Validate same-file anchor link e.g. #my-anchor."""
    anchor = target.lstrip("#").lower()
    if not anchor:
        return None
    file_anchors = get_anchors(md_file)
    if anchor not in file_anchors:
        return BrokenDocLink(
            source_file=source_rel,
            line=line_num,
            target=target,
            reason=f"Anchor '#{anchor}' not found in current file",
        )
    return None


def _validate_relative_path(
    target: str,
    md_file: Path,
    line_num: int,
    source_rel: str,
    get_anchors: Callable[[Path], set[str]],
) -> BrokenDocLink | None:
    """Validate relative filesystem path and optional anchor."""
    path_part, _, anchor_part = target.partition("#")
    target_file = (md_file.parent / path_part).resolve()

    if not target_file.exists():
        return BrokenDocLink(
            source_file=source_rel,
            line=line_num,
            target=target,
            reason=f"Referenced path '{path_part}' does not exist",
        )

    if anchor_part and target_file.is_file() and target_file.suffix.lower() == ".md":
        anchor = anchor_part.lower()
        target_anchors = get_anchors(target_file)
        if anchor not in target_anchors:
            return BrokenDocLink(
                source_file=source_rel,
                line=line_num,
                target=target,
                reason=f"Anchor '#{anchor}' not found in '{path_part}'",
            )

    return None


def _scan_single_file(
    md_file: Path,
    root: Path,
    get_anchors: Callable[[Path], set[str]],
) -> tuple[list[BrokenDocLink], int]:
    """Scan an individual markdown document for link violations."""
    source_rel = str(md_file.relative_to(root) if md_file.is_relative_to(root) else md_file)
    try:
        lines = md_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as err:
        return [BrokenDocLink(source_rel, 1, str(md_file), f"Failed to read file: {err}")], 0

    broken: list[BrokenDocLink] = []
    links_count = 0
    in_code_block = False

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        for raw in _extract_raw_links(line):
            target = raw.split()[0].strip("<>\"'") if raw.split() else raw.strip("<>\"'")
            if _is_external_link(target):
                continue

            links_count += 1
            if target.startswith("#"):
                err = _validate_same_file_anchor(target, md_file, line_num, source_rel, get_anchors)
            else:
                err = _validate_relative_path(target, md_file, line_num, source_rel, get_anchors)

            if err is not None:
                broken.append(err)

    return broken, links_count


def scan_doc_links(
    target_path: Path | None = None,
    repo_root: Path | None = None,
) -> DocLinksReport:
    """Scan markdown files for broken relative links and anchors.

    Args:
        target_path: Optional file or directory to scan. Defaults to repo_root.
        repo_root: Optional repository root. Defaults to current working directory.

    Returns:
        DocLinksReport summarizing scanned files, verified links, and errors.

    Notes/Architectural Intent:
        Core domain logic checking filesystem existence and anchor presence for all
        relative links within documentation.
    """
    root = repo_root or Path.cwd()
    base_path = target_path or root
    md_files = _discover_markdown_files(base_path)

    broken_links: list[BrokenDocLink] = []
    total_links_count = 0
    anchors_cache: dict[Path, set[str]] = {}

    def get_anchors(p: Path) -> set[str]:
        resolved = p.resolve()
        if resolved not in anchors_cache:
            anchors_cache[resolved] = extract_anchors_from_file(resolved)
        return anchors_cache[resolved]

    for md_file in md_files:
        file_broken, file_count = _scan_single_file(md_file, root, get_anchors)
        broken_links.extend(file_broken)
        total_links_count += file_count

    return DocLinksReport(
        scanned_files_count=len(md_files),
        total_links_count=total_links_count,
        broken_links=tuple(broken_links),
        is_successful=len(broken_links) == 0,
    )


class CheckDocLinksHandler:
    """CQRS Handler executing documentation link validation scans.

    Notes/Architectural Intent:
        Routes CheckDocLinksCommand to scan_doc_links.
    """

    def handle(self, command: CheckDocLinksCommand) -> DocLinksReport:
        """Handle CheckDocLinksCommand and produce a DocLinksReport.

        Args:
            command: Command containing path and repo_root specifications.

        Returns:
            DocLinksReport containing validation results.
        """
        target = Path(command.path) if command.path else None
        root = Path(command.repo_root) if command.repo_root else None
        return scan_doc_links(target_path=target, repo_root=root)


__all__ = [
    "CheckDocLinksHandler",
    "extract_anchors_from_file",
    "scan_doc_links",
    "slugify_heading",
]
