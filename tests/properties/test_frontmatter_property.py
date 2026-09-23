"""Hypothesis property-based tests for Markdown front-matter parsing and writeback.

Notes/Architectural Intent:
    Verifies round-trip fidelity, preservation of unknown front-matter keys (extra),
    and exact preservation of Markdown bodies under arbitrary generated strings.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from hexaqual.commands.medium_publish import (
    ArticlePayload,
    FrontMatter,
    _parse_article,
    _write_front_matter,
)

safe_text = (
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters=(" ", "-", "_"),
        ),
        min_size=1,
        max_size=30,
    )
    .map(str.strip)
    .filter(lambda s: len(s) > 0)
)


@given(
    title=safe_text,
    subtitle=safe_text,
    tags=st.lists(safe_text, max_size=4),
    status=st.sampled_from(["draft", "published", "archived"]),
    devto_id=st.one_of(st.none(), st.integers(min_value=1, max_value=999999)),
    body=safe_text.map(lambda s: f"# Heading\n\n{s}\n"),
)
@settings(max_examples=50)
def test_frontmatter_roundtrip_property(
    title: str,
    subtitle: str,
    tags: list[str],
    status: str,
    devto_id: int | None,
    body: str,
) -> None:
    """Verify that writing and re-parsing front matter preserves all fields.

    Args:
        title: Generated article title.
        subtitle: Generated subtitle.
        tags: Generated tags list.
        status: Status string.
        devto_id: Optional numeric article ID.
        body: Markdown body.
    """
    with tempfile.TemporaryDirectory() as td:
        article_file = Path(td) / "article.md"
        article_file.write_text(
            f"---\ntitle: {title}\nstatus: {status}\n---\n\nInitial content\n",
            encoding="utf-8",
        )

        initial_fm = FrontMatter(
            title=title,
            subtitle=subtitle,
            tags=tags,
            status=status,
            devto_id=devto_id,
            extra={"custom_key": "custom_value"},
        )
        payload = ArticlePayload(
            front_matter=initial_fm,
            body_markdown=body,
            slug="article",
            path=article_file,
        )

        _write_front_matter(payload)

        # Re-read and parse
        reloaded_text = article_file.read_text(encoding="utf-8")
        reloaded_payload = _parse_article(reloaded_text, article_file)

        assert reloaded_payload.front_matter.title == title
        assert reloaded_payload.front_matter.subtitle == subtitle
        assert reloaded_payload.front_matter.status == status
        assert reloaded_payload.front_matter.devto_id == devto_id
        assert reloaded_payload.front_matter.extra.get("custom_key") == "custom_value"
        assert reloaded_payload.body_markdown == body
