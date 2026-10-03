"""Unit tests for OpenSSF badge adapter.

Notes/Architectural Intent:
    Verifies URL proposal construction, query string chunking, and JSON
    response mapping using mock urllib responses without making live network calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from hexaqual.adapters.openssf import OpenSsfBadgeAdapter, OpenSsfScorecardAdapter
from hexaqual.domain.openssf import CriterionProposal, CriterionStatus, OpenSsfTier


def test_build_proposal_urls_chunking() -> None:
    """Test proposal URL construction with chunking."""
    adapter = OpenSsfBadgeAdapter(base_url="https://test.bestpractices.dev")
    proposals = [
        CriterionProposal(
            criterion_id=f"crit_{i}",
            status=CriterionStatus.MET,
            justification=f"Justification for {i}",
            tier=OpenSsfTier.PASSING,
        )
        for i in range(25)
    ]

    urls = adapter.build_proposal_urls(
        project_id=14749, tier=OpenSsfTier.PASSING, proposals=proposals, max_per_chunk=10
    )
    assert len(urls) == 3
    assert "https://test.bestpractices.dev/en/projects/14749/passing/edit?" in urls[0]
    assert "crit_0_status=Met" in urls[0]
    assert "crit_10_status=Met" in urls[1]
    assert "crit_20_status=Met" in urls[2]


@patch("urllib.request.urlopen")
def test_fetch_project_success(mock_urlopen: MagicMock) -> None:
    """Test fetch_project parsing JSON payload into OpenSsfProject."""
    payload = {
        "id": 14749,
        "name": "hexaqual",
        "repo_url": "https://github.com/TheTrueSCU/hexaqual",
        "badge_level": "passing",
        "tiered_percentage": 100,
        "test_status": "Met",
        "test_justification": "pytest configured.",
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = OpenSsfBadgeAdapter(base_url="https://test.bestpractices.dev")
    proj = adapter.fetch_project(14749)

    assert proj.project_id == 14749
    assert proj.name == "hexaqual"
    assert proj.badge_level == "passing"
    assert proj.criteria_statuses.get("test") == "Met"
    assert proj.criteria_justifications.get("test") == "pytest configured."


@patch("urllib.request.urlopen")
def test_search_project_by_repo(mock_urlopen: MagicMock) -> None:
    """Test search_project_by_repo finding matching project ID."""
    payload = [{"id": 14749, "name": "hexaqual"}]
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = OpenSsfBadgeAdapter(base_url="https://test.bestpractices.dev")
    pid = adapter.search_project_by_repo("https://github.com/TheTrueSCU/hexaqual")
    assert pid == 14749


@patch("urllib.request.urlopen")
def test_search_project_by_repo_not_found(mock_urlopen: MagicMock) -> None:
    """Test search_project_by_repo returning None when no project matches."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"[]"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = OpenSsfBadgeAdapter(base_url="https://test.bestpractices.dev")
    pid = adapter.search_project_by_repo("https://github.com/TheTrueSCU/nonexistent")
    assert pid is None


@patch("urllib.request.urlopen")
def test_fetch_scorecard_success(mock_urlopen: MagicMock) -> None:
    """Test fetch_scorecard parsing JSON payload into ScorecardResult."""
    payload = {
        "date": "2026-09-27",
        "repo": {"name": "github.com/TheTrueSCU/hexastack"},
        "score": 6.6,
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 10,
                "reason": "no dangerous workflow patterns detected",
                "details": [],
            },
            {
                "name": "Maintained",
                "score": 0,
                "reason": "project created recently",
                "details": ["recent repo"],
            },
        ],
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = OpenSsfScorecardAdapter(base_url="https://test.securityscorecards.dev")
    res = adapter.fetch_scorecard("TheTrueSCU/hexastack")

    assert res.repo == "github.com/TheTrueSCU/hexastack"
    assert res.score == 6.6
    assert len(res.checks) == 2
    assert res.checks[0].name == "Dangerous-Workflow"
    assert res.checks[0].score == 10


@patch("urllib.request.urlopen")
def test_fetch_scorecard_formats(mock_urlopen: MagicMock) -> None:
    """Test fetch_scorecard with git SSH and HTTPS URLs."""
    payload = {"date": "2026-09-27", "score": 8.0, "checks": []}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = OpenSsfScorecardAdapter(base_url="https://test.securityscorecards.dev")
    res1 = adapter.fetch_scorecard("git@github.com:TheTrueSCU/hexastack.git")
    assert res1.repo == "github.com/TheTrueSCU/hexastack"

    res2 = adapter.fetch_scorecard("https://github.com/TheTrueSCU/hexastack.git")
    assert res2.repo == "github.com/TheTrueSCU/hexastack"
