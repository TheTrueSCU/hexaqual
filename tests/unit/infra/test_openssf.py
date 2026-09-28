"""Unit tests for OpenSSF infrastructure inspection and audit correlation.

Notes/Architectural Intent:
    Verifies local filesystem heuristic evaluation, git remote URL normalization,
    and audit status correlation against mock projects.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.domain.openssf import (
    CriterionProposal,
    CriterionStatus,
    OpenSsfProject,
    OpenSsfTier,
)
from hexaqual.infra.openssf import (
    audit_project_posture,
    evaluate_local_heuristics,
    resolve_local_repo_url,
)


def test_resolve_local_repo_url_ssh() -> None:
    """Test converting SSH git remote URL to HTTPS."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "git@github.com:TheTrueSCU/hexaqual.git\n"
        mock_run.return_value = mock_proc

        url = resolve_local_repo_url(Path("/tmp"))
        assert url == "https://github.com/TheTrueSCU/hexaqual"


def test_resolve_local_repo_url_https() -> None:
    """Test stripping .git suffix from HTTPS git remote URL."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "https://github.com/TheTrueSCU/hexaqual.git\n"
        mock_run.return_value = mock_proc

        url = resolve_local_repo_url(Path("/tmp"))
        assert url == "https://github.com/TheTrueSCU/hexaqual"


def test_evaluate_local_heuristics_passing(tmp_path: Path) -> None:
    """Test heuristic evaluation on a mock repository layout."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test-pkg'\n[tool.ruff]\n", encoding="utf-8")

    proposals = evaluate_local_heuristics(OpenSsfTier.PASSING, root_dir=tmp_path)
    crit_ids = [p.criterion_id for p in proposals]

    assert "tests_documented_added" in crit_ids
    assert "dynamic_analysis_unsafe" in crit_ids
    assert "crypto_weaknesses" in crit_ids


def test_audit_project_posture_correlation() -> None:
    """Test correlating local proposals with remote criteria states."""
    project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="in_progress",
        tiered_percentage=50,
        criteria_statuses={"test": "Met", "tests_documented_added": "?"},
    )
    local_proposals = [
        CriterionProposal(
            criterion_id="tests_documented_added",
            status=CriterionStatus.MET,
            justification="Documented in CONTRIBUTING.md.",
            tier=OpenSsfTier.PASSING,
        ),
        CriterionProposal(
            criterion_id="test",
            status=CriterionStatus.MET,
            justification="pytest configured.",
            tier=OpenSsfTier.PASSING,
        ),
    ]

    audit = audit_project_posture(project, OpenSsfTier.PASSING, local_proposals)
    # Only tests_documented_added should be pending because 'test' is already 'Met'
    assert len(audit.proposals) == 1
    assert audit.proposals[0].criterion_id == "tests_documented_added"
