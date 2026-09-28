"""HTTP adapter for bestpractices.dev REST API and proposal URL generation.

Notes/Architectural Intent:
    Implements OpenSsfBadgePort using Python's standard library urllib.request
    to guarantee zero external runtime dependencies. Correctly handles URL
    encoding, query string chunking (under 2,000 chars), and JSON response parsing.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from collections.abc import Sequence
from typing import Any

from hexaqual.domain.openssf import (
    CriterionProposal,
    OpenSsfProject,
    OpenSsfTier,
    ScorecardCheck,
    ScorecardResult,
)
from hexaqual.ports.openssf import OpenSsfBadgePort, OpenSsfScorecardPort

__all__ = [
    "OpenSsfBadgeAdapter",
    "OpenSsfScorecardAdapter",
]


class OpenSsfBadgeAdapter(OpenSsfBadgePort):
    """Adapter for bestpractices.dev API using standard library urllib."""

    def __init__(self, base_url: str = "https://www.bestpractices.dev") -> None:
        """Initialize the OpenSSF Badge API adapter.

        Args:
            base_url: Base URL for bestpractices.dev API.

        Notes/Architectural Intent:
            Allows injecting alternative mock or staging endpoints during integration tests.
        """
        self.base_url = base_url.rstrip("/")

    def fetch_project(self, project_id: int) -> OpenSsfProject:
        """Retrieve project status and criteria evaluations from bestpractices.dev.

        Args:
            project_id: OpenSSF project numeric identifier.

        Returns:
            OpenSsfProject containing criteria states and justifications.

        Raises:
            RuntimeError: If remote request fails or returns non-200 status.
        """
        url = f"{self.base_url}/projects/{project_id}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Hexaqual-OpenSSF/0.5.1"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            msg = f"Failed to fetch OpenSSF project {project_id} from {url}: {exc}"
            raise RuntimeError(msg) from exc

        statuses: dict[str, str] = {}
        justifications: dict[str, str] = {}
        for key, value in data.items():
            if key.endswith("_status") and value is not None:
                crit_id = key[:-7]
                statuses[crit_id] = str(value)
            elif key.endswith("_justification") and value is not None:
                crit_id = key[:-14]
                justifications[crit_id] = str(value)

        return OpenSsfProject(
            project_id=project_id,
            name=str(data.get("name", "")),
            repo_url=str(data.get("repo_url", "")),
            badge_level=str(data.get("badge_level", "in_progress")),
            tiered_percentage=int(data.get("tiered_percentage", 0)),
            criteria_statuses=statuses,
            criteria_justifications=justifications,
        )

    def search_project_by_repo(self, repo_url: str) -> int | None:
        """Search bestpractices.dev for an existing project matching a repository URL.

        Args:
            repo_url: Repository URL (e.g. 'https://github.com/owner/repo').

        Returns:
            Project ID if found, otherwise None.

        Raises:
            RuntimeError: If remote lookup fails.
        """
        encoded_query = urllib.parse.quote(repo_url)
        url = f"{self.base_url}/en/projects.json?pq={encoded_query}"
        req = urllib.request.Request(url, headers={"User-Agent": "Hexaqual-OpenSSF/0.5.1"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                results: list[dict[str, Any]] = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            msg = f"Failed to search OpenSSF projects for {repo_url}: {exc}"
            raise RuntimeError(msg) from exc

        if not results:
            return None

        # Return first matching project ID
        project_entry = results[0]
        return int(project_entry["id"])

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

        Notes/Architectural Intent:
            Chunks query strings to ensure URL lengths stay under 2,048 characters across
            browsers and reverse proxies.
        """
        tier_str = str(tier).lower()
        if hasattr(tier, "value"):
            tier_str = str(tier.value).lower()

        urls: list[str] = []
        chunk_size = max(1, max_per_chunk)

        for idx in range(0, len(proposals), chunk_size):
            chunk = proposals[idx : idx + chunk_size]
            params: list[str] = []
            for item in chunk:
                status_val = str(
                    item.status.value if hasattr(item.status, "value") else item.status
                )
                params.append(f"{item.criterion_id}_status={urllib.parse.quote(status_val)}")
                params.append(
                    f"{item.criterion_id}_justification={urllib.parse.quote_plus(item.justification)}"
                )

            query_string = "&".join(params)
            url = f"{self.base_url}/en/projects/{project_id}/{tier_str}/edit?{query_string}"
            urls.append(url)

        return urls


class OpenSsfScorecardAdapter(OpenSsfScorecardPort):
    """Adapter for api.securityscorecards.dev using standard library urllib."""

    def __init__(self, base_url: str = "https://api.securityscorecards.dev") -> None:
        """Initialize the OpenSSF Scorecard API adapter.

        Args:
            base_url: Base URL for api.securityscorecards.dev.

        Notes/Architectural Intent:
            Allows injecting alternative mock or staging endpoints during integration tests.
        """
        self.base_url = base_url.rstrip("/")

    def fetch_scorecard(self, repo: str) -> ScorecardResult:
        """Retrieve security scorecard analysis for a target repository.

        Args:
            repo: Repository identifier (e.g. 'owner/repo' or 'github.com/owner/repo').

        Returns:
            ScorecardResult containing overall score and individual check evaluations.

        Raises:
            RuntimeError: If remote lookup fails or repository is not indexed by Scorecard.

        Notes/Architectural Intent:
            Normalizes repository strings (stripping schemes and host prefixes)
            to GitHub target path 'github.com/{owner}/{repo}' expected by Scorecard API.
        """
        clean_repo = repo.strip()
        clean_repo = re.sub(r"^https?://", "", clean_repo)
        clean_repo = re.sub(r"^git@", "", clean_repo)
        clean_repo = re.sub(r"\.git$", "", clean_repo)
        if not clean_repo.startswith("github.com/"):
            clean_repo = f"github.com/{clean_repo.lstrip('/')}"

        url = f"{self.base_url}/projects/{clean_repo}"
        req = urllib.request.Request(url, headers={"User-Agent": "Hexaqual-OpenSSF/0.5.1"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            msg = f"Failed to fetch Scorecard for {clean_repo} from {url}: {exc}"
            raise RuntimeError(msg) from exc

        raw_score = data.get("score")
        score = float(raw_score) if raw_score is not None else 0.0
        date = str(data.get("date", ""))

        checks: list[ScorecardCheck] = []
        for raw_check in data.get("checks", []):
            chk_score = raw_check.get("score")
            chk_int_score = int(chk_score) if chk_score is not None and chk_score >= 0 else 0
            checks.append(
                ScorecardCheck(
                    name=str(raw_check.get("name", "")),
                    score=chk_int_score,
                    reason=str(raw_check.get("reason", "")),
                    details=list(raw_check.get("details", []) or []),
                )
            )

        return ScorecardResult(
            repo=clean_repo,
            score=score,
            date=date,
            checks=checks,
        )
