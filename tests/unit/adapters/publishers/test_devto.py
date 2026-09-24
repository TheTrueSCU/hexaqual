"""Unit tests for the medium-publish DEV.to publishing command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hexaqual.adapters.publishers.devto import (
    ArticlePayload,
    FrontMatter,
    _all_unposted_articles,
    _build_slug_url_map,
    _devto_tags,
    _parse_article,
    _resolve_cross_links,
    _update_readme_registry,
    _write_front_matter,
    get_article_status_table,
    publish_or_upload_single,
    record_medium_url,
    sync_all_links,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_MD = """\
---
title: "Test Article Title"
subtitle: "A subtitle for testing"
date: 2026-09-09
status: draft
tags:
  - python
  - ai
  - architecture
cross_post:
  devto: true
---

# Test Article Title

Body content here.

[See also: feature flags](devto://feature-flags-openfeature)
"""

_SAMPLE_MD_WITH_IDS = """\
---
title: "Already Uploaded"
status: draft
tags: [python]
devto_id: 999
devto_url: "https://dev.to/user/already-uploaded-abc12"
---

Body.
"""

_SAMPLE_MD_NO_FRONTMATTER = """\
Just plain body text with no front matter.
"""


@pytest.fixture()
def article_file(tmp_path: Path) -> Path:
    f = tmp_path / "test-article.md"
    f.write_text(_SAMPLE_MD, encoding="utf-8")
    return f


@pytest.fixture()
def medium_dir(tmp_path: Path) -> Path:
    d = tmp_path / "medium"
    d.mkdir()
    (d / "README.md").write_text("# Readme\n\n---\n", encoding="utf-8")
    (d / "test-article.md").write_text(_SAMPLE_MD, encoding="utf-8")
    (d / "uploaded-article.md").write_text(_SAMPLE_MD_WITH_IDS, encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# Front matter parsing
# ---------------------------------------------------------------------------


def test_parse_article_block_tags(article_file: Path) -> None:
    """Block-style YAML tags are parsed into a list correctly."""
    text = article_file.read_text()
    payload = _parse_article(text, article_file)
    assert payload.front_matter.title == "Test Article Title"
    assert payload.front_matter.subtitle == "A subtitle for testing"
    assert "python" in payload.front_matter.tags
    assert "ai" in payload.front_matter.tags
    assert payload.front_matter.devto_id is None
    assert payload.front_matter.devto_url == ""
    assert "# Test Article Title" in payload.body_markdown


def test_parse_article_with_tracking_fields(tmp_path: Path) -> None:
    """devto_id and devto_url are parsed from existing front matter."""
    f = tmp_path / "uploaded.md"
    f.write_text(_SAMPLE_MD_WITH_IDS, encoding="utf-8")
    payload = _parse_article(f.read_text(), f)
    assert payload.front_matter.devto_id == 999
    assert payload.front_matter.devto_url == "https://dev.to/user/already-uploaded-abc12"


def test_parse_article_missing_frontmatter_exits(tmp_path: Path) -> None:
    """Missing front matter block causes SystemExit."""
    f = tmp_path / "bad.md"
    f.write_text(_SAMPLE_MD_NO_FRONTMATTER, encoding="utf-8")
    with pytest.raises(SystemExit):
        _parse_article(f.read_text(), f)


# ---------------------------------------------------------------------------
# Front matter writeback
# ---------------------------------------------------------------------------


def test_write_front_matter_roundtrip(article_file: Path) -> None:
    """Writing back front matter preserves title and adds tracking fields."""
    payload = _parse_article(article_file.read_text(), article_file)
    payload.front_matter.devto_id = 12345
    payload.front_matter.devto_url = "https://dev.to/user/test-article-abc12"
    _write_front_matter(payload)

    updated = _parse_article(article_file.read_text(), article_file)
    assert updated.front_matter.devto_id == 12345
    assert updated.front_matter.devto_url == "https://dev.to/user/test-article-abc12"
    # canonical_url should be set to devto_url automatically
    assert updated.front_matter.canonical_url == "https://dev.to/user/test-article-abc12"
    # Original body is preserved
    assert "# Test Article Title" in updated.body_markdown


# ---------------------------------------------------------------------------
# Cross-link resolution
# ---------------------------------------------------------------------------


def test_resolve_cross_links_substitutes_known_slugs() -> None:
    """Known devto:// slugs are replaced with their URLs."""
    body = "Check out [Feature Flags](devto://feature-flags-openfeature) for more."
    slug_map = {"feature-flags-openfeature": "https://dev.to/user/feature-flags-abc12"}
    result = _resolve_cross_links(body, slug_map)
    assert "https://dev.to/user/feature-flags-abc12" in result
    assert "devto://" not in result


def test_resolve_cross_links_leaves_unknown_slugs() -> None:
    """Unknown devto:// slugs are left intact for a later pass."""
    body = "See [article](devto://not-published-yet)."
    result = _resolve_cross_links(body, {})
    assert "devto://not-published-yet" in result


# ---------------------------------------------------------------------------
# DEV.to tag normalisation
# ---------------------------------------------------------------------------


def test_devto_tags_normalisation() -> None:
    """Tags are lowercased, non-alphanumeric removed, capped at 4."""
    result = _devto_tags(["Python", "open-source", "CNCF", "feature-flags", "fifth"])
    assert result == ["python", "opensource", "cncf", "featureflags"]


def test_devto_tags_empty() -> None:
    """Empty input returns empty list."""
    assert _devto_tags([]) == []


# ---------------------------------------------------------------------------
# Unposted articles discovery
# ---------------------------------------------------------------------------


def test_all_unposted_articles_excludes_uploaded(medium_dir: Path) -> None:
    """Articles with devto_id are excluded from unposted list."""
    unposted = _all_unposted_articles(medium_dir)
    slugs = [p.slug for p in unposted]
    assert "test-article" in slugs
    assert "uploaded-article" not in slugs


# ---------------------------------------------------------------------------
# Slug→URL map
# ---------------------------------------------------------------------------


def test_build_slug_url_map(medium_dir: Path) -> None:
    """Only articles with devto_url appear in the slug map."""
    slug_map = _build_slug_url_map(medium_dir)
    assert "uploaded-article" in slug_map
    assert slug_map["uploaded-article"] == "https://dev.to/user/already-uploaded-abc12"
    assert "test-article" not in slug_map


# ---------------------------------------------------------------------------
# README URL registry
# ---------------------------------------------------------------------------


def test_update_readme_registry_creates_section(medium_dir: Path) -> None:
    """URL Registry section is created if it doesn't exist."""
    _update_readme_registry(medium_dir)
    readme = (medium_dir / "README.md").read_text()
    assert "## URL Registry" in readme
    assert "uploaded-article" in readme
    assert "https://dev.to/user/already-uploaded-abc12" in readme


def test_update_readme_registry_updates_existing(medium_dir: Path) -> None:
    """Existing URL Registry section is replaced, not duplicated."""
    _update_readme_registry(medium_dir)
    _update_readme_registry(medium_dir)  # second call
    readme = (medium_dir / "README.md").read_text()
    assert readme.count("## URL Registry") == 1


# ---------------------------------------------------------------------------
# Dry-run and Handler Functions
# ---------------------------------------------------------------------------


def test_publish_or_upload_single_dry_run(article_file: Path) -> None:
    """Dry-run single upload produces action outcome without making HTTP call."""
    with patch("hexaqual.adapters.publishers.devto._devto_request") as mock_req:
        slug, msg = publish_or_upload_single(
            str(article_file),
            publish=False,
            api_key="test-key",
            repo_root=article_file.parent,
            dry_run=True,
            medium_dir=article_file.parent,
        )
        assert slug == "test-article"
        assert "[dry-run]" in msg
        mock_req.assert_not_called()


def test_get_article_status_table(medium_dir: Path) -> None:
    """Status table gathers status for articles in directory."""
    table = get_article_status_table(medium_dir)
    assert len(table) >= 2
    slugs = {row[0] for row in table}
    assert "test-article" in slugs
    assert "uploaded-article" in slugs


def test_record_medium_url(article_file: Path) -> None:
    """Record Medium URL updates front matter."""
    slug, msg = record_medium_url(
        str(article_file),
        "https://medium.com/@user/story",
        repo_root=article_file.parent,
        dry_run=False,
        medium_dir=article_file.parent,
    )
    assert slug == "test-article"
    assert "Recorded Medium URL" in msg
    assert "https://medium.com/@user/story" in article_file.read_text(encoding="utf-8")


def test_sync_all_links_dry_run(medium_dir: Path) -> None:
    """Sync links in dry run mode returns outcomes without HTTP calls."""
    with patch("hexaqual.adapters.publishers.devto._devto_request") as mock_req:
        results = sync_all_links(
            medium_dir,
            api_key="test-key",
            repo_root=medium_dir.parent,
            dry_run=True,
        )
        assert isinstance(results, list)
        mock_req.assert_not_called()


# ---------------------------------------------------------------------------
# Payload fields: series and ai_disclosure
# ---------------------------------------------------------------------------


def test_upload_draft_payload_includes_series_and_ai_disclosure(
    article_file: Path,
) -> None:
    """Verify that _upload_draft includes ai_disclosure and series in DEV.to payload."""
    from hexaqual.adapters.publishers.devto import _upload_draft

    payload = _parse_article(article_file.read_text(), article_file)
    payload.front_matter.extra["series"] = "Hexastack Deep Dives"

    with patch("hexaqual.adapters.publishers.devto._devto_request") as mock_devto:
        mock_devto.return_value = {"id": 12345}
        res = _upload_draft(payload, "fake-api-key", {})
        assert res["id"] == 12345
        call_args = mock_devto.call_args
        sent_body = call_args.kwargs["json"]["article"]
        assert sent_body["ai_disclosure"] == "ai_assisted"
        assert sent_body["series"] == "Hexastack Deep Dives"


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


def test_module_exports() -> None:
    """Public __all__ exports are importable."""
    assert callable(publish_or_upload_single)
    assert callable(get_article_status_table)
    assert callable(sync_all_links)
    assert FrontMatter is not None
    assert ArticlePayload is not None


def test_devto_publisher_adapter_methods() -> None:
    """Verify DevToPublisherAdapter list, get, create, and update via mock transport."""
    import httpx

    from hexaqual.adapters.publishers.devto import DevToPublisherAdapter

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/articles/me":
            return httpx.Response(200, json=[{"id": 101, "title": "My Article"}])
        if request.url.path == "/api/articles/101":
            if request.method == "GET":
                return httpx.Response(200, json={"id": 101, "title": "My Article"})
            if request.method == "PATCH":
                return httpx.Response(200, json={"id": 101, "updated": True})
        if request.url.path == "/api/articles" and request.method == "POST":
            return httpx.Response(201, json={"id": 202, "title": "New Article"})
        return httpx.Response(404, json={"error": "not found"})

    client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    adapter = DevToPublisherAdapter(api_key="mock_key", client=client)

    articles = adapter.list_articles()
    assert len(articles) == 1
    assert articles[0]["id"] == 101

    article = adapter.get_article(101)
    assert article["title"] == "My Article"

    missing = adapter.get_article(999)
    assert missing == {}

    created = adapter.create_article({"title": "New Article"})
    assert created["id"] == 202

    updated = adapter.update_article(101, {"title": "Updated"})
    assert updated["updated"] is True


def test_upload_all_drafts(medium_dir: Path) -> None:
    """Verify upload_all_drafts in dry-run and live modes."""
    from hexaqual.adapters.publishers.devto import upload_all_drafts

    # 1. Dry run mode
    dry_results = upload_all_drafts(medium_dir, api_key="dummy", dry_run=True)
    assert len(dry_results) >= 1
    assert "[dry-run]" in dry_results[0][1]

    # 2. Live mode with mock
    with patch(
        "hexaqual.adapters.publishers.devto._upload_draft",
        return_value={"id": 777},
    ):
        live_results = upload_all_drafts(medium_dir, api_key="dummy", dry_run=False)
        assert len(live_results) >= 1
        assert "Uploaded draft devto_id=777" in live_results[0][1]


def test_record_medium_url_with_directory(medium_dir: Path) -> None:
    """Verify record_medium_url updates markdown front matter in medium_dir."""
    from hexaqual.adapters.publishers.devto import record_medium_url

    repo_root = medium_dir.parent
    slug, msg = record_medium_url(
        slug="test-article",
        medium_url="https://medium.com/@user/test-article",
        repo_root=repo_root,
        dry_run=True,
        medium_dir=medium_dir,
    )
    assert slug == "test-article"
    assert "https://medium.com" in msg

    slug, msg = record_medium_url(
        slug="test-article",
        medium_url="https://medium.com/@user/test-article",
        repo_root=repo_root,
        dry_run=False,
        medium_dir=medium_dir,
    )
    assert "Recorded" in msg
    content = (medium_dir / "test-article.md").read_text()
    assert "medium_url" in content
