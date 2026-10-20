"""Unit tests for refactoring port interfaces."""

from __future__ import annotations

import inspect

from hexaqual.domain.refactoring import (
    AlphabetizeCodeReport,
    MediumPublishReport,
)
from hexaqual.ports.refactoring import RefactoringPresenterPort


class DummyRefactoringPresenter(RefactoringPresenterPort):
    """Concrete dummy presenter for testing abstract interface conformance."""

    def present_alphabetize(self, report: AlphabetizeCodeReport) -> int:
        return 0 if report.is_successful else 1

    def present_medium_publish(self, report: MediumPublishReport) -> int:
        return 0 if report.is_successful else 1


def test_refactoring_presenter_port_instantiation() -> None:
    """Verify RefactoringPresenterPort is an abstract interface."""
    assert inspect.isabstract(RefactoringPresenterPort)
    assert "present_alphabetize" in RefactoringPresenterPort.__abstractmethods__


def test_concrete_refactoring_presenter() -> None:
    """Verify concrete subclass implements all abstract methods."""
    presenter = DummyRefactoringPresenter()
    assert presenter.present_alphabetize(AlphabetizeCodeReport()) == 0
    assert presenter.present_medium_publish(MediumPublishReport()) == 0
