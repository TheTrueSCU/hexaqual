"""Unit tests for generator port interfaces."""

from __future__ import annotations

import pytest

from hexaqual.domain.generators import (
    ArchonReport,
    DocLinksReport,
    PydepsReport,
    UsageDocsReport,
)
from hexaqual.ports.generators import GeneratorPresenterPort


class DummyGeneratorPresenter(GeneratorPresenterPort):
    """Concrete dummy presenter for testing abstract interface conformance."""

    def present_pydeps(self, report: PydepsReport) -> int:
        return 0 if report.is_successful else 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        return 0 if report.is_successful else 1

    def present_doc_links(self, report: DocLinksReport) -> int:
        return 0 if report.is_successful else 1


def test_generator_presenter_port_instantiation() -> None:
    """Verify GeneratorPresenterPort cannot be instantiated directly without implementations."""
    with pytest.raises(TypeError):
        GeneratorPresenterPort()  # type: ignore[abstract]


def test_concrete_generator_presenter() -> None:
    """Verify concrete subclass implements all abstract methods."""
    presenter = DummyGeneratorPresenter()
    res_pydeps = presenter.present_pydeps(PydepsReport())
    assert res_pydeps == 0
    res_usage = presenter.present_usage_docs(UsageDocsReport())
    assert res_usage == 0
    res_archon = presenter.present_archon(ArchonReport())
    assert res_archon == 0
    res_doc_links = presenter.present_doc_links(DocLinksReport())
    assert res_doc_links == 0
