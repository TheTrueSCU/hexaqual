"""Domain models and value objects for OpenSSF Best Practices and Scorecard governance.

Notes/Architectural Intent:
    Encapsulates OpenSSF certification tiers, criteria evaluation states,
    project badge metadata, and proposal payloads without external HTTP
    or presentation framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "CriterionProposal",
    "CriterionStatus",
    "OpenSsfAuditResult",
    "OpenSsfProject",
    "OpenSsfTier",
]


class OpenSsfTier(StrEnum):
    """OpenSSF Best Practices badge certification tiers."""

    PASSING = "passing"
    SILVER = "silver"
    GOLD = "gold"


class CriterionStatus(StrEnum):
    """Canonical criterion evaluation status values."""

    MET = "Met"
    UNMET = "Unmet"
    NA = "N/A"
    UNKNOWN = "?"


@dataclass(frozen=True)
class CriterionProposal:
    """A proposed status and justification for a discrete OpenSSF criterion."""

    criterion_id: str
    status: CriterionStatus | str
    justification: str
    tier: OpenSsfTier = OpenSsfTier.PASSING


@dataclass(frozen=True)
class OpenSsfProject:
    """Project metadata and criteria states retrieved from bestpractices.dev."""

    project_id: int
    name: str
    repo_url: str
    badge_level: str
    tiered_percentage: int
    criteria_statuses: dict[str, str] = field(default_factory=dict)
    criteria_justifications: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class OpenSsfAuditResult:
    """Audit result correlating remote badge criteria with local repository heuristics."""

    project: OpenSsfProject
    tier: OpenSsfTier
    met_count: int
    total_count: int
    percentage: int
    proposals: list[CriterionProposal] = field(default_factory=list)
