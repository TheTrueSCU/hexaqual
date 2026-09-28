"""Port contracts for OpenSSF Best Practices and Scorecard interactions.

Notes/Architectural Intent:
    Defines abstract interfaces separating remote badge querying and proposal
    formatting from concrete network transports or local Git inspectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from hexaqual.domain.openssf import (
    CriterionProposal,
    OpenSsfProject,
    OpenSsfTier,
)

__all__ = [
    "OpenSsfBadgePort",
]


class OpenSsfBadgePort(ABC):
    """Abstract port for communicating with bestpractices.dev and building proposal URLs."""

    @abstractmethod
    def fetch_project(self, project_id: int) -> OpenSsfProject:
        """Retrieve project status and criteria evaluations from bestpractices.dev.

        Args:
            project_id: OpenSSF project numeric identifier.

        Returns:
            OpenSsfProject containing criteria states and justifications.

        Raises:
            RuntimeError: If remote request fails or returns an error.
        """

    @abstractmethod
    def search_project_by_repo(self, repo_url: str) -> int | None:
        """Search bestpractices.dev for an existing project matching a repository URL.

        Args:
            repo_url: Repository URL (e.g. 'https://github.com/owner/repo').

        Returns:
            Project ID if found, otherwise None.

        Raises:
            RuntimeError: If remote lookup fails.
        """

    @abstractmethod
    def build_proposal_urls(
        self,
        project_id: int,
        tier: OpenSsfTier | str,
        proposals: Sequence[CriterionProposal],
        max_per_chunk: int = 12,
    ) -> list[str]:
        """Build chunked 1-click automation proposal URLs.

        Args:
            project_id: OpenSSF project numeric identifier.
            tier: Certification tier (passing, silver, gold).
            proposals: Criteria proposals with statuses and justifications.
            max_per_chunk: Maximum number of criteria per URL chunk to prevent HTTP 414.

        Returns:
            List of URL strings ready to launch in a browser.
        """
