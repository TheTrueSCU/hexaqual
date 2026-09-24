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


def test_publish_medium_articles_handler_branches(tmp_path: Path) -> None:
    """Verify PublishMediumArticlesHandler branches: medium_url, sync_links, all_drafts."""
    medium_dir = tmp_path / "docs" / "medium"
    medium_dir.mkdir(parents=True)
    (medium_dir / "article-1-intro.md").write_text("---\ntitle: A\n---\nBody", encoding="utf-8")

    handler = PublishMediumArticlesHandler(root=tmp_path)

    # 1. medium_url missing slug
    rep1 = handler.handle(PublishMediumArticlesCommand(medium_url="https://medium.com/@u/a"))
    assert rep1.is_successful is False

    # 2. medium_url with slug
    with patch(
        "hexaqual.adapters.publishers.devto.record_medium_url",
        return_value=("article-1-intro", "Recorded"),
    ):
        rep2 = handler.handle(
            PublishMediumArticlesCommand(
                slug="article-1-intro", medium_url="https://medium.com/@u/a"
            )
        )
        assert rep2.is_successful is True

    # 3. Missing API key
    rep3 = handler.handle(PublishMediumArticlesCommand(slug="article-1-intro", dry_run=False))
    assert rep3.is_successful is False
    assert "No DEV.to API key" in rep3.details[0][1]

    # 4. sync_links
    with patch(
        "hexaqual.adapters.publishers.devto.sync_all_links",
        return_value=[("article-1-intro", "Synced")],
    ):
        rep4 = handler.handle(
            PublishMediumArticlesCommand(sync_links=True, api_key="dummy", dry_run=True)
        )
        assert rep4.is_successful is True

    # 5. all_drafts
    with patch(
        "hexaqual.adapters.publishers.devto.upload_all_drafts",
        return_value=[("article-1-intro", "Uploaded")],
    ):
        rep5 = handler.handle(
            PublishMediumArticlesCommand(all_drafts=True, api_key="dummy", dry_run=True)
        )
        assert rep5.is_successful is True

    # 6. missing target
    rep6 = handler.handle(PublishMediumArticlesCommand(api_key="dummy", dry_run=True))
    assert rep6.is_successful is False

    # 7. single upload success
    with patch(
        "hexaqual.adapters.publishers.devto.publish_or_upload_single",
        return_value=("article-1-intro", "Uploaded successfully"),
    ):
        rep7 = handler.handle(
            PublishMediumArticlesCommand(slug="article-1-intro", api_key="dummy", dry_run=True)
        )
        assert rep7.is_successful is True
        assert rep7.details[0][1] == "Uploaded successfully"

    # 8. single upload exception
    with patch(
        "hexaqual.adapters.publishers.devto.publish_or_upload_single",
        side_effect=RuntimeError("Upload failure"),
    ):
        rep8 = handler.handle(
            PublishMediumArticlesCommand(slug="article-1-intro", api_key="dummy", dry_run=True)
        )
        assert rep8.is_successful is False
        assert "Failed: Upload failure" in rep8.details[0][1]
