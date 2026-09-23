"""Unit tests for refactoring and publishing CQRS handlers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from hexaqual.domain.refactoring import (
    AlphabetizeCodeCommand,
    PublishMediumArticlesCommand,
)
from hexaqual.infra.handlers.refactoring import (
    AlphabetizeCodeHandler,
    PublishMediumArticlesHandler,
)


def test_alphabetize_code_handler(tmp_path: Path) -> None:
    """Verify AlphabetizeCodeHandler processes target Python files."""
    code_file = tmp_path / "sample.py"
    code_file.write_text("def b(): pass\ndef a(): pass\n", encoding="utf-8")

    handler = AlphabetizeCodeHandler(root=tmp_path)
    with patch(
        "hexaqual.infra.handlers.refactoring.sort_python_file",
        return_value=True,
    ):
        report = handler.handle(AlphabetizeCodeCommand(targets=(code_file,)))
        assert report.is_successful is True
        assert len(report.reordered_files) == 1


def test_publish_medium_articles_handler(tmp_path: Path) -> None:
    """Verify PublishMediumArticlesHandler scans articles and returns report."""
    medium_dir = tmp_path / "docs" / "medium"
    medium_dir.mkdir(parents=True)
    article_content = "---\ntitle: Article 1\n---\n# Article 1"
    (medium_dir / "article-1-intro.md").write_text(article_content, encoding="utf-8")

    handler = PublishMediumArticlesHandler(root=tmp_path)
    # Test status inspection
    report = handler.handle(PublishMediumArticlesCommand(status=True))
    assert report.is_successful is True
    assert report.total_count == 1
    assert len(report.status_table) == 1

    # Test single-article dry-run
    single_report = handler.handle(
        PublishMediumArticlesCommand(slug="article-1-intro", dry_run=True)
    )
    assert single_report.is_successful is True
    assert single_report.total_count == 1
    assert len(single_report.details) == 1
