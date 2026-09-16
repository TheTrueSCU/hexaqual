"""Unit tests for documentation link and anchor integrity scanner.

Notes/Architectural Intent:
    Verifies link extraction, heading slugification, and error reporting for
    broken paths and missing anchors across markdown documentation trees.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.commands.doc_links import (
    CheckDocLinksHandler,
    extract_anchors_from_file,
    scan_doc_links,
    slugify_heading,
)
from hexaqual.domain.generators import CheckDocLinksCommand


def test_slugify_heading() -> None:
    """Verify heading conversion to GitHub-compatible anchor slugs."""
    assert slugify_heading("Hello World") == "hello-world"
    assert slugify_heading("1. Overview & Setup!") == "1-overview-setup"
    assert slugify_heading("### Advanced Topic (v2)") == "advanced-topic-v2"
    assert slugify_heading("Code: `<MyClass>`") == "code-myclass"


def test_extract_anchors_from_file(tmp_path: Path) -> None:
    """Verify anchor extraction from headings and HTML anchors."""
    doc = tmp_path / "guide.md"
    doc.write_text(
        '# Introduction\n\n## Getting Started\n\n<a id="custom-anchor"></a>\n',
        encoding="utf-8",
    )
    anchors = extract_anchors_from_file(doc)
    assert "introduction" in anchors
    assert "getting-started" in anchors
    assert "custom-anchor" in anchors


def test_scan_doc_links_valid(tmp_path: Path) -> None:
    """Verify scan_doc_links passes when all links and anchors are valid."""
    doc_a = tmp_path / "index.md"
    doc_b = tmp_path / "details.md"

    doc_b.write_text(
        "# Details Page\n\n## Sub Section\nContent here.\n",
        encoding="utf-8",
    )
    doc_a.write_text(
        "# Main Index\n\n"
        "[Details](details.md)\n"
        "[Section](details.md#sub-section)\n"
        "[Self Anchor](#main-index)\n"
        "[External](https://github.com/TheTrueSCU/hexastack)\n",
        encoding="utf-8",
    )

    report = scan_doc_links(target_path=tmp_path)
    assert report.is_successful
    assert len(report.broken_links) == 0
    assert report.total_links_count == 3  # External link excluded from relative count


def test_scan_doc_links_broken(tmp_path: Path) -> None:
    """Verify scan_doc_links identifies missing files and dead anchors."""
    doc = tmp_path / "index.md"
    other = tmp_path / "exists.md"
    other.write_text("# Other\n", encoding="utf-8")

    doc.write_text(
        "# Main\n\n"
        "[Missing File](nonexistent.md)\n"
        "[Missing Anchor Same File](#dead-anchor)\n"
        "[Missing Anchor Other File](exists.md#dead-section)\n",
        encoding="utf-8",
    )

    report = scan_doc_links(target_path=tmp_path)
    assert not report.is_successful
    assert len(report.broken_links) == 3

    reasons = [b.reason for b in report.broken_links]
    assert any("does not exist" in r for r in reasons)
    assert any("not found in current file" in r for r in reasons)
    assert any("not found in 'exists.md'" in r for r in reasons)


def test_check_doc_links_handler(tmp_path: Path) -> None:
    """Verify CheckDocLinksHandler delegates correctly."""
    doc = tmp_path / "test.md"
    doc.write_text("# Valid\n[Self](#valid)\n", encoding="utf-8")

    handler = CheckDocLinksHandler()
    cmd = CheckDocLinksCommand(path=str(doc), repo_root=str(tmp_path))
    report = handler.handle(cmd)

    assert report.is_successful
    assert report.scanned_files_count == 1
