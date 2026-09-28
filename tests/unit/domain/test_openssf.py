"""Unit tests for OpenSSF domain models.

Notes/Architectural Intent:
    Verifies immutability, enum variants, and value initialization
    of OpenSSF domain entities and audit data structures.
"""

from __future__ import annotations

import dataclasses

import pytest

from hexaqual.domain.openssf import (
    CriterionProposal,
    CriterionStatus,
    OpenSsfAuditResult,
    OpenSsfProject,
    OpenSsfTier,
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
