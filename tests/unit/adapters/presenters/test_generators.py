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
