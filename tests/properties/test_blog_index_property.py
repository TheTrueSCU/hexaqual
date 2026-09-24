"""Hypothesis property-based tests for blog index table generation.

Notes/Architectural Intent:
    Verifies that blog index table regeneration adheres to the strict 5-column schema,
    maintains topological order across arbitrary combinations of published articles,
    and guarantees idempotent document updates.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from hexaqual.adapters.publishers.devto import (
    _BLOG_PUBLICATION_ORDER,
    _regenerate_blog_index,
)

url_strategy = st.from_regex(r"https://dev\.to/[a-z0-9\-]+/[a-z0-9\-]+", fullmatch=True)


@given(
    published_flags=st.lists(
        st.booleans(), min_size=len(_BLOG_PUBLICATION_ORDER), max_size=len(_BLOG_PUBLICATION_ORDER)
    ),
    sample_urls=st.lists(
        url_strategy, min_size=len(_BLOG_PUBLICATION_ORDER), max_size=len(_BLOG_PUBLICATION_ORDER)
    ),
)
@settings(max_examples=30)
def test_blog_index_table_schema_and_idempotency_property(
    published_flags: list[bool], sample_urls: list[st.SearchStrategy[str]]
) -> None:
    """Verify 5-column schema and idempotent updates under arbitrary publication states.

    Args:
        published_flags: List of booleans indicating whether each article is published.
        sample_urls: List of URLs generated for published articles.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        docs_dir = root / "docs"
        blog_dir = docs_dir / "blog"
        medium_dir = docs_dir / "medium"
        blog_dir.mkdir(parents=True)
        medium_dir.mkdir(parents=True)

        initial_table = (
            "| # | Title | Topic | DEV.to | Medium |\n"
            "|---|-------|-------|--------|--------|\n"
            "| 0 | Stub | Architecture | — | — |\n"
        )
        blog_index = blog_dir / "index.md"
        blog_index.write_text(
            f"# Engineering Blog\n\n{initial_table}\n> URLs populate as articles go live.\n",
            encoding="utf-8",
        )

        # Create article drafts
        for i, (_num, slug, title, _topic) in enumerate(_BLOG_PUBLICATION_ORDER):
            is_pub = published_flags[i]
            dev_url = sample_urls[i] if is_pub else ""
            status = "published" if is_pub else "draft"
            art_file = medium_dir / f"{slug}.md"
            art_file.write_text(
                f"---\ntitle: {title}\nstatus: {status}\ndevto_url: '{dev_url}'\n---\n\nContent\n",
                encoding="utf-8",
            )

        # 1. Run regeneration
        _regenerate_blog_index(root, medium_dir)
        content_pass1 = blog_index.read_text(encoding="utf-8")

        # 2. Invariant: 5-column structure
        table_lines = [
            line
            for line in content_pass1.splitlines()
            if line.startswith("|") and not line.startswith("|---")
        ]
        # Header + 17 articles = 18 lines
        assert len(table_lines) == len(_BLOG_PUBLICATION_ORDER) + 1
        for line in table_lines:
            # Must split into 6 parts (5 columns surrounded by '|')
            parts = [p.strip() for p in line.split("|")[1:-1]]
            assert len(parts) == 5

        # 3. Invariant: Idempotence (running again produces identical text)
        _regenerate_blog_index(root, medium_dir)
        content_pass2 = blog_index.read_text(encoding="utf-8")
        assert content_pass1 == content_pass2
