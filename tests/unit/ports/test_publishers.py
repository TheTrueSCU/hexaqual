"""Unit tests for publisher port interfaces."""

from __future__ import annotations

from typing import Any

import pytest

from hexaqual.ports.publishers import ArticlePublisherPort, PackagePublisherPort
from hexaqual.ports.pypi import PyPiClientPort


class DummyArticlePublisher(ArticlePublisherPort):
    """Concrete dummy publisher for testing interface conformance."""

    def list_articles(self) -> list[dict[str, Any]]:
        return [{"id": 1, "title": "Test"}]

    def get_article(self, article_id: int) -> dict[str, Any]:
        return {"id": article_id, "title": "Test"}

    def create_article(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": 100, **payload}

    def update_article(self, article_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": article_id, **payload}


def test_article_publisher_port_instantiation() -> None:
    """Verify ArticlePublisherPort cannot be instantiated directly without implementations."""
    with pytest.raises(TypeError):
        ArticlePublisherPort()  # type: ignore[abstract]


def test_concrete_article_publisher() -> None:
    """Verify concrete subclass implements all abstract methods."""
    publisher = DummyArticlePublisher()
    articles = publisher.list_articles()
    assert len(articles) == 1

    article = publisher.get_article(1)
    assert article["id"] == 1

    created = publisher.create_article({"title": "New"})
    assert created["id"] == 100

    updated = publisher.update_article(1, {"title": "Updated"})
    assert updated["title"] == "Updated"


def test_package_publisher_port_alias() -> None:
    """Verify PackagePublisherPort aliases PyPiClientPort."""
    assert PackagePublisherPort is PyPiClientPort
