"""Unit tests for multi-format generator presenters."""

from __future__ import annotations

from unittest.mock import MagicMock

from rich.console import Console

from hexaqual.adapters.presenters.generators import (
    JsonGeneratorPresenterAdapter,
    MarkdownGeneratorPresenterAdapter,
    RichGeneratorPresenterAdapter,
    create_generator_presenter,
)
from hexaqual.domain.docs_drift import (
    DocDriftFinding,
    DocDriftReport,
)
from hexaqual.domain.generators import (
    ArchonReport,
    BrokenDocLink,
    DocLinksReport,
    PydepsDiagramResult,
    PydepsReport,
    UsageDocsReport,
)


def test_create_generator_presenter_factory() -> None:
    """Verify create_generator_presenter instantiates correct adapter."""
    assert isinstance(create_generator_presenter("rich"), RichGeneratorPresenterAdapter)
    assert isinstance(create_generator_presenter("table"), RichGeneratorPresenterAdapter)
    assert isinstance(create_generator_presenter("json"), JsonGeneratorPresenterAdapter)
    assert isinstance(create_generator_presenter("markdown"), MarkdownGeneratorPresenterAdapter)
    assert isinstance(create_generator_presenter("md"), MarkdownGeneratorPresenterAdapter)


def test_rich_generator_presenter() -> None:
    """Verify RichGeneratorPresenterAdapter renders reports correctly."""
    mock_console = MagicMock(spec=Console)
    presenter = RichGeneratorPresenterAdapter(console=mock_console)

    pydeps_rep = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=True),),
        is_successful=True,
    )
    rc = presenter.present_pydeps(pydeps_rep)
    assert rc == 0
    mock_console.print.assert_called()

    # Failed pydeps
    pydeps_fail = PydepsReport(
        results=(PydepsDiagramResult(name="bad", path="", success=False),),
        is_successful=False,
    )
    assert presenter.present_pydeps(pydeps_fail) == 1

    # Check mode pydeps - up to date
    pydeps_check_ok = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=True, is_stale=False),),
        is_successful=True,
        is_check=True,
    )
    assert presenter.present_pydeps(pydeps_check_ok) == 0

    # Check mode pydeps - stale
    pydeps_check_stale = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=False, is_stale=True),),
        is_successful=False,
        is_check=True,
    )
    assert presenter.present_pydeps(pydeps_check_stale) == 1

    # Check mode pydeps - skipped dot
    pydeps_check_skip = PydepsReport(
        results=(
            PydepsDiagramResult(
                name="Architecture Diagrams",
                path="",
                success=True,
                is_stale=False,
                details="Graphviz 'dot' not installed (check skipped)",
            ),
        ),
        is_successful=True,
        is_check=True,
    )
    assert presenter.present_pydeps(pydeps_check_skip) == 0

    usage_rep = UsageDocsReport(
        up_to_date_files=("USAGE.md",),
        updated_files=(),
        stale_files=(),
        diffs=(),
        is_valid=True,
    )
    assert presenter.present_usage_docs(usage_rep) == 0

    archon_rep = ArchonReport(
        generated_files=("tests/architecture/test_boundaries.py",),
        skipped_files=("pkg_b",),
        is_successful=True,
    )
    res_archon = presenter.present_archon(archon_rep)
    assert res_archon == 0

    doc_links_ok = DocLinksReport(scanned_files_count=1, total_links_count=2, is_successful=True)
    res_dl_ok = presenter.present_doc_links(doc_links_ok)
    assert res_dl_ok == 0

    doc_links_fail = DocLinksReport(
        scanned_files_count=1,
        total_links_count=2,
        broken_links=(BrokenDocLink("a.md", 1, "bad.md", "does not exist"),),
        is_successful=False,
    )
    res_dl_fail = presenter.present_doc_links(doc_links_fail)
    assert res_dl_fail == 1


def test_json_generator_presenter() -> None:
    """Verify JsonGeneratorPresenterAdapter formats output as JSON."""
    mock_console = MagicMock(spec=Console)
    presenter = JsonGeneratorPresenterAdapter(console=mock_console)

    pydeps_rep = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=True),),
        is_successful=True,
    )
    res_pydeps = presenter.present_pydeps(pydeps_rep)
    assert res_pydeps == 0
    mock_console.print_json.assert_called()

    # Check mode pydeps JSON
    pydeps_check = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=True, is_stale=False),),
        is_successful=True,
        is_check=True,
    )
    assert presenter.present_pydeps(pydeps_check) == 0

    usage_rep = UsageDocsReport(is_valid=True)
    res_usage = presenter.present_usage_docs(usage_rep)
    assert res_usage == 0

    archon_rep = ArchonReport(is_successful=True)
    res_archon = presenter.present_archon(archon_rep)
    assert res_archon == 0

    doc_links_rep = DocLinksReport(is_successful=True)
    res_dl = presenter.present_doc_links(doc_links_rep)
    assert res_dl == 0


def test_markdown_generator_presenter() -> None:
    """Verify MarkdownGeneratorPresenterAdapter formats output as Markdown."""
    mock_console = MagicMock(spec=Console)
    presenter = MarkdownGeneratorPresenterAdapter(console=mock_console)

    pydeps_rep = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=True),),
        is_successful=True,
    )
    res_pydeps = presenter.present_pydeps(pydeps_rep)
    assert res_pydeps == 0
    mock_console.print.assert_called()

    # Check mode pydeps Markdown
    pydeps_check_ok = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=True, is_stale=False),),
        is_successful=True,
        is_check=True,
    )
    assert presenter.present_pydeps(pydeps_check_ok) == 0

    pydeps_check_stale = PydepsReport(
        results=(PydepsDiagramResult(name="core", path="core.svg", success=False, is_stale=True),),
        is_successful=False,
        is_check=True,
    )
    assert presenter.present_pydeps(pydeps_check_stale) == 1

    # Check mode pydeps Markdown - skipped dot
    pydeps_check_skip = PydepsReport(
        results=(
            PydepsDiagramResult(
                name="Architecture Diagrams",
                path="",
                success=True,
                is_stale=False,
                details="Graphviz 'dot' not installed (check skipped)",
            ),
        ),
        is_successful=True,
        is_check=True,
    )
    assert presenter.present_pydeps(pydeps_check_skip) == 0

    usage_rep = UsageDocsReport(
        stale_files=("USAGE.md",),
        diffs=(("USAGE.md", "diff text"),),
        is_valid=False,
    )
    res_usage = presenter.present_usage_docs(usage_rep)
    assert res_usage == 1

    archon_rep = ArchonReport(
        generated_files=("test.py",),
        is_successful=True,
    )
    res_archon = presenter.present_archon(archon_rep)
    assert res_archon == 0

    doc_links_ok = DocLinksReport(is_successful=True)
    res_dl_ok = presenter.present_doc_links(doc_links_ok)
    assert res_dl_ok == 0

    doc_links_fail = DocLinksReport(
        broken_links=(BrokenDocLink("a.md", 1, "bad.md", "does not exist"),),
        is_successful=False,
    )
    res_dl_fail = presenter.present_doc_links(doc_links_fail)
    assert res_dl_fail == 1


def test_present_doc_drift_all_formats() -> None:
    """Verify present_doc_drift renders correctly in rich, json, and markdown formats."""
    finding = DocDriftFinding(
        file_path="docs/test.md",
        line_number=5,
        drift_type="version_mismatch",
        matched_text="v0.8.0",
        expected_text="v0.9.0",
        snippet="https://img.shields.io/badge/version-v0.8.0-blue.svg",
        fixable=True,
    )
    drift_dirty = DocDriftReport(findings=(finding,), is_successful=False)
    drift_clean = DocDriftReport(findings=(), is_successful=True)

    # Rich Presenter
    mock_console = MagicMock(spec=Console)
    rich_presenter = RichGeneratorPresenterAdapter(console=mock_console)
    assert rich_presenter.present_doc_drift(drift_dirty) == 1
    assert rich_presenter.present_doc_drift(drift_clean) == 0

    # JSON Presenter
    mock_json_console = MagicMock(spec=Console)
    json_presenter = JsonGeneratorPresenterAdapter(console=mock_json_console)
    assert json_presenter.present_doc_drift(drift_dirty) == 1
    assert json_presenter.present_doc_drift(drift_clean) == 0

    # Markdown Presenter
    mock_md_console = MagicMock(spec=Console)
    md_presenter = MarkdownGeneratorPresenterAdapter(console=mock_md_console)
    assert md_presenter.present_doc_drift(drift_dirty) == 1
    assert md_presenter.present_doc_drift(drift_clean) == 0
