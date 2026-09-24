"""Port interfaces for article and package publishing backends.

Notes/Architectural Intent:
    Decouples documentation publishing (DEV.to, Medium) and distribution packaging (PyPI)
    from driving CLI workflows and presentation adapters. Enforces pure interface boundaries
    enabling hermetic testing with mock transports and in-memory doubles.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hexaqual.ports.pypi import PyPiClientPort

__all__ = [
    "ArticlePublisherPort",
    "PackagePublisherPort",
]

PackagePublisherPort = PyPiClientPort


class ArticlePublisherPort(ABC):
    """Abstract port defining contracts for publishing technical articles to external platforms."""

    @abstractmethod
    def list_articles(self) -> list[dict[str, Any]]:
        """List published and draft articles from the remote platform.

        Returns:
            List of article metadata dictionaries from the platform.

        Notes/Architectural Intent:
            Used to query remote publication state without mutating documents.
        """
        raise NotImplementedError

    @abstractmethod
    def get_article(self, article_id: int) -> dict[str, Any]:
        """Retrieve a single article's remote representation by ID.

        Args:
            article_id: Unique identifier on the publishing platform.

        Returns:
            Dictionary containing article details and publication status.

        Notes/Architectural Intent:
            Fetches current canonical URLs and remote tags for reconciliation.
        """
        raise NotImplementedError

    @abstractmethod
    def create_article(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new article draft or publication on the remote platform.

        Args:
            payload: Formatted dictionary containing title, body_markdown, tags, and status.

        Returns:
            Dictionary representing the created article, including assigned remote ID.

        Notes/Architectural Intent:
            Executes platform creation HTTP requests. Must raise domain-level exceptions
            on authorization or rate-limiting failures.
        """
        raise NotImplementedError

    @abstractmethod
    def update_article(self, article_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Update an existing article on the remote platform.

        Args:
            article_id: Unique identifier of the target article.
            payload: Modified article contents and metadata.

        Returns:
            Dictionary representing the updated article state.

        Notes/Architectural Intent:
            Applies updates via PATCH/PUT requests to synchronize local content changes.
        """
        raise NotImplementedError
