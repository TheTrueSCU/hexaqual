"""Unit tests for OpenSSF domain models.

Notes/Architectural Intent:
    Verifies immutability, enum variants, and value initialization
    of OpenSSF domain entities and audit data structures.
"""

from __future__ import annotations

import dataclasses
from types import MappingProxyType

import pytest

from hexaqual.domain.openssf import (
    CRITERIA_CATALOG,
    CriterionProposal,
    CriterionStatus,
    OpenSsfAuditResult,
    OpenSsfCriteriaCatalog,
    OpenSsfCriterionDefinition,
    OpenSsfProject,
    OpenSsfTier,
    ScorecardCheck,
    ScorecardResult,
)


def test_openssf_tiers_and_statuses() -> None:
    """Test OpenSSF tier and criterion status enum values."""
    assert OpenSsfTier.PASSING == "passing"
    assert OpenSsfTier.SILVER == "silver"
    assert OpenSsfTier.GOLD == "gold"

    assert CriterionStatus.MET == "Met"
    assert CriterionStatus.UNMET == "Unmet"
    assert CriterionStatus.NA == "N/A"
    assert CriterionStatus.UNKNOWN == "?"


def test_criterion_proposal_immutability() -> None:
    """Test CriterionProposal creation and immutability."""
    proposal = CriterionProposal(
        criterion_id="build_reproducible",
        status=CriterionStatus.MET,
        justification="Deterministic uv.lock packaging.",
        tier=OpenSsfTier.SILVER,
    )
    assert proposal.criterion_id == "build_reproducible"
    assert proposal.status == CriterionStatus.MET
    assert proposal.tier == OpenSsfTier.SILVER

    with pytest.raises(dataclasses.FrozenInstanceError):
        proposal.__setattr__("status", CriterionStatus.UNMET)


def test_openssf_project_and_audit_result() -> None:
    """Test OpenSsfProject and OpenSsfAuditResult models."""
    project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="passing",
        tiered_percentage=100,
        criteria_statuses={"test": "Met", "build_reproducible": "Met"},
        criteria_justifications={"test": "pytest configured."},
    )
    assert project.project_id == 14749
    assert project.name == "hexaqual"
    assert project.badge_level == "passing"

    audit = OpenSsfAuditResult(
        project=project,
        tier=OpenSsfTier.PASSING,
        met_count=2,
        total_count=2,
        percentage=100,
        proposals=[],
    )
    assert audit.met_count == 2
    assert audit.percentage == 100


def test_criteria_catalog_and_definition() -> None:
    """Test OpenSSF criteria catalog structure, methods, and immutability."""
    passing_catalog = OpenSsfCriteriaCatalog.for_tier(OpenSsfTier.PASSING)
    silver_catalog = OpenSsfCriteriaCatalog.for_tier(OpenSsfTier.SILVER)
    gold_catalog = OpenSsfCriteriaCatalog.for_tier(OpenSsfTier.GOLD)

    assert len(passing_catalog) == 67
    assert len(silver_catalog) == 55
    assert len(gold_catalog) == 23

    sample_defn = passing_catalog[0]
    assert isinstance(sample_defn, OpenSsfCriterionDefinition)
    assert sample_defn.criterion_id == "description_good"
    assert sample_defn.tier == OpenSsfTier.PASSING
    assert sample_defn.category == "MUST"
    assert sample_defn.met_url_required is False

    # Test lookup via OpenSsfCriteriaCatalog.get
    found_defn = OpenSsfCriteriaCatalog.get("dco")
    assert found_defn is not None
    assert found_defn.criterion_id == "dco"
    assert found_defn.tier == OpenSsfTier.SILVER
    assert found_defn.met_url_required is True

    # Test immutability of the catalog view
    assert isinstance(CRITERIA_CATALOG, MappingProxyType)
    assert hasattr(CRITERIA_CATALOG, "__setitem__") is False


def test_scorecard_models() -> None:
    """Test ScorecardCheck and ScorecardResult models."""
    check = ScorecardCheck(
        name="SAST",
        score=10,
        reason="CodeQL runs on all commits",
        details=["CodeQL workflow found in .github/workflows/codeql.yml"],
    )
    assert check.name == "SAST"
    assert check.score == 10

    result = ScorecardResult(
        repo="github.com/TheTrueSCU/hexastack",
        score=9.5,
        date="2026-09-27",
        checks=[check],
    )
    assert result.repo == "github.com/TheTrueSCU/hexastack"
    assert result.score == 9.5
    assert len(result.checks) == 1
