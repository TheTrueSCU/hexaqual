"""Unit tests for OpenSSF infrastructure inspection and audit correlation.

Notes/Architectural Intent:
    Verifies local filesystem heuristic evaluation, git remote URL normalization,
    and audit status correlation against mock projects.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hexaqual.domain.openssf import (
    CriterionProposal,
    CriterionStatus,
    OpenSsfCriteriaCatalog,
    OpenSsfProject,
    OpenSsfTier,
)
from hexaqual.infra.openssf import (
    audit_project_posture,
    evaluate_local_heuristics,
    format_checklist_markdown,
    generate_checklist,
    resolve_local_repo_url,
    scaffold_document,
    verify_openssf_compliance,
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


def test_generate_checklist_and_markdown() -> None:
    """Test generating structured checklist items and markdown formatting."""
    project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="in_progress",
        tiered_percentage=50,
        criteria_statuses={"description_good": "Met", "interact": "?"},
        criteria_justifications={"description_good": "Good description in README."},
    )
    items = generate_checklist(project, OpenSsfTier.PASSING, unmet_only=False)
    assert len(items) == 67
    met_item = next(it for it in items if it["criterion_id"] == "description_good")
    assert met_item["status"] == "Met"
    assert met_item["category"] == "MUST"

    unmet_items = generate_checklist(project, OpenSsfTier.PASSING, unmet_only=True)
    assert not any(it["status"] == "Met" for it in unmet_items)

    md = format_checklist_markdown(items[:2], "hexaqual", 14749, OpenSsfTier.PASSING)
    assert "# OpenSSF Best Practices Checklist: hexaqual" in md
    assert "[x] **description_good**" in md
    assert "[ ] **interact**" in md


def test_scaffold_document(tmp_path: Path) -> None:
    """Test scaffolding security, governance, contributing, and codeql documents."""
    sec_path = scaffold_document(
        "security", dest_dir=tmp_path, repo_url="https://github.com/org/repo"
    )
    assert sec_path.is_file()
    assert sec_path.name == "SECURITY.md"
    assert "https://github.com/org/repo/security/advisories/new" in sec_path.read_text("utf-8")

    gov_path = scaffold_document("governance", dest_dir=tmp_path)
    assert gov_path.is_file()
    assert gov_path.name == "GOVERNANCE.md"

    contrib_path = scaffold_document("contributing", dest_dir=tmp_path)
    assert contrib_path.is_file()
    assert contrib_path.name == "CONTRIBUTING.md"

    codeql_path = scaffold_document("codeql", dest_dir=tmp_path)
    assert codeql_path.is_file()
    assert codeql_path.name == "codeql.yml"

    # Verify duplicate error without force
    with pytest.raises(FileExistsError):
        scaffold_document("security", dest_dir=tmp_path, force=False)

    # Verify overwrite with force
    overwritten = scaffold_document("security", dest_dir=tmp_path, force=True)
    assert overwritten.exists()

    # Verify invalid document type
    with pytest.raises(ValueError, match="Unknown document type"):
        scaffold_document("unknown_type", dest_dir=tmp_path)


def test_verify_openssf_compliance_passing() -> None:
    """Test verification when project satisfies all tier requirements."""
    must_criteria = {
        crit.criterion_id: "Met"
        for crit in OpenSsfCriteriaCatalog.for_tier(OpenSsfTier.PASSING)
        if crit.category.upper() == "MUST"
    }

    project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="passing",
        tiered_percentage=100,
        criteria_statuses=must_criteria,
    )

    res = verify_openssf_compliance(project, OpenSsfTier.PASSING)
    assert res.passed is True
    assert len(res.errors) == 0
    assert len(res.unmet_must) == 0


def test_verify_openssf_compliance_failures() -> None:
    """Test verification when badge level, score, and criteria are deficient."""
    project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="in_progress",
        tiered_percentage=80,
        criteria_statuses={"description_good": "Unmet"},
    )

    res = verify_openssf_compliance(project, OpenSsfTier.PASSING, min_score=100)
    assert res.passed is False
    assert len(res.errors) > 0
    assert any("below required" in err for err in res.errors)
    assert any("below required minimum" in err for err in res.errors)
    assert len(res.unmet_must) > 0
