"""Domain models and value objects for OpenSSF Best Practices and Scorecard governance.

Notes/Architectural Intent:
    Encapsulates OpenSSF certification tiers, criteria evaluation states,
    project badge metadata, and proposal payloads without external HTTP
    or presentation framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import ClassVar

__all__ = [
    "CRITERIA_CATALOG",
    "CriterionProposal",
    "CriterionStatus",
    "OpenSsfAuditResult",
    "OpenSsfCheckResult",
    "OpenSsfCriteriaCatalog",
    "OpenSsfCriterionDefinition",
    "OpenSsfProject",
    "OpenSsfTier",
    "ScorecardCheck",
    "ScorecardResult",
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
class OpenSsfCriterionDefinition:
    """Master definition and constraints for an OpenSSF criterion."""

    criterion_id: str
    tier: OpenSsfTier
    category: str
    met_url_required: bool = False


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


@dataclass(frozen=True)
class OpenSsfCheckResult:
    """Evaluation result verifying repository compliance with an OpenSSF badge tier."""

    passed: bool
    tier: OpenSsfTier
    badge_level: str
    score: int
    min_score: int
    unmet_must: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScorecardCheck:
    """Individual security check evaluation returned by OpenSSF Scorecard."""

    name: str
    score: int
    reason: str
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScorecardResult:
    """Aggregated Scorecard evaluation report for a GitHub repository."""

    repo: str
    score: float
    date: str
    checks: list[ScorecardCheck] = field(default_factory=list)


_PASSING_CRITERIA: tuple[tuple[str, str, bool], ...] = (
    ("description_good", "MUST", False),
    ("interact", "MUST", False),
    ("contribution", "MUST", True),
    ("contribution_requirements", "SHOULD", True),
    ("floss_license", "MUST", False),
    ("floss_license_osi", "SUGGESTED", False),
    ("license_location", "MUST", True),
    ("documentation_basics", "MUST", False),
    ("documentation_interface", "MUST", False),
    ("sites_https", "MUST", False),
    ("discussion", "MUST", False),
    ("english", "SHOULD", False),
    ("maintained", "MUST", False),
    ("repo_public", "MUST", False),
    ("repo_track", "MUST", False),
    ("repo_interim", "MUST", False),
    ("repo_distributed", "SUGGESTED", False),
    ("version_unique", "MUST", False),
    ("version_semver", "SUGGESTED", False),
    ("version_tags", "SUGGESTED", False),
    ("release_notes", "MUST", True),
    ("release_notes_vulns", "MUST", False),
    ("report_process", "MUST", True),
    ("report_tracker", "SHOULD", False),
    ("report_responses", "MUST", False),
    ("enhancement_responses", "SHOULD", False),
    ("report_archive", "MUST", True),
    ("vulnerability_report_process", "MUST", True),
    ("vulnerability_report_private", "MUST", True),
    ("vulnerability_report_response", "MUST", False),
    ("build", "MUST", False),
    ("build_common_tools", "SUGGESTED", False),
    ("build_floss_tools", "SHOULD", False),
    ("test", "MUST", False),
    ("test_invocation", "SHOULD", False),
    ("test_most", "SUGGESTED", False),
    ("test_continuous_integration", "SUGGESTED", False),
    ("test_policy", "MUST", False),
    ("tests_are_added", "MUST", False),
    ("tests_documented_added", "SUGGESTED", False),
    ("warnings", "MUST", False),
    ("warnings_fixed", "MUST", False),
    ("warnings_strict", "SUGGESTED", False),
    ("know_secure_design", "MUST", False),
    ("know_common_errors", "MUST", False),
    ("crypto_published", "MUST", False),
    ("crypto_call", "SHOULD", False),
    ("crypto_floss", "MUST", False),
    ("crypto_keylength", "MUST", False),
    ("crypto_working", "MUST", False),
    ("crypto_weaknesses", "SHOULD", False),
    ("crypto_pfs", "SHOULD", False),
    ("crypto_password_storage", "MUST", False),
    ("crypto_random", "MUST", False),
    ("delivery_mitm", "MUST", False),
    ("delivery_unsigned", "MUST", False),
    ("vulnerabilities_fixed_60_days", "MUST", False),
    ("vulnerabilities_critical_fixed", "SHOULD", False),
    ("no_leaked_credentials", "MUST", False),
    ("static_analysis", "MUST", False),
    ("static_analysis_common_vulnerabilities", "SUGGESTED", False),
    ("static_analysis_fixed", "MUST", False),
    ("static_analysis_often", "SUGGESTED", False),
    ("dynamic_analysis", "SUGGESTED", False),
    ("dynamic_analysis_unsafe", "SUGGESTED", False),
    ("dynamic_analysis_enable_assertions", "SUGGESTED", False),
    ("dynamic_analysis_fixed", "MUST", False),
)

_SILVER_CRITERIA: tuple[tuple[str, str, bool], ...] = (
    ("achieve_passing", "MUST", False),
    ("contribution_requirements", "MUST", True),
    ("dco", "SHOULD", True),
    ("governance", "MUST", True),
    ("code_of_conduct", "MUST", True),
    ("roles_responsibilities", "MUST", True),
    ("access_continuity", "MUST", True),
    ("bus_factor", "SHOULD", True),
    ("documentation_roadmap", "MUST", True),
    ("documentation_architecture", "MUST", True),
    ("documentation_security", "MUST", True),
    ("documentation_quick_start", "MUST", True),
    ("documentation_current", "MUST", False),
    ("documentation_achievements", "MUST", True),
    ("accessibility_best_practices", "SHOULD", False),
    ("internationalization", "SHOULD", False),
    ("sites_password_security", "MUST", False),
    ("maintenance_or_update", "MUST", False),
    ("report_tracker", "MUST", False),
    ("vulnerability_report_credit", "MUST", True),
    ("vulnerability_response_process", "MUST", True),
    ("coding_standards", "MUST", True),
    ("coding_standards_enforced", "MUST", False),
    ("build_standard_variables", "MUST", False),
    ("build_preserve_debug", "SHOULD", False),
    ("build_non_recursive", "MUST", False),
    ("build_repeatable", "MUST", False),
    ("installation_common", "MUST", False),
    ("installation_standard_variables", "MUST", False),
    ("installation_development_quick", "MUST", False),
    ("external_dependencies", "MUST", True),
    ("dependency_monitoring", "MUST", False),
    ("updateable_reused_components", "MUST", False),
    ("interfaces_current", "SHOULD", False),
    ("automated_integration_testing", "MUST", False),
    ("regression_tests_added50", "MUST", False),
    ("test_statement_coverage80", "MUST", False),
    ("test_policy_mandated", "MUST", False),
    ("tests_documented_added", "MUST", False),
    ("warnings_strict", "MUST", False),
    ("implement_secure_design", "MUST", False),
    ("crypto_weaknesses", "MUST", False),
    ("crypto_algorithm_agility", "SHOULD", False),
    ("crypto_credential_agility", "MUST", False),
    ("crypto_used_network", "SHOULD", False),
    ("crypto_tls12", "SHOULD", False),
    ("crypto_certificate_verification", "MUST", False),
    ("crypto_verification_private", "MUST", False),
    ("signed_releases", "MUST", False),
    ("version_tags_signed", "SUGGESTED", False),
    ("input_validation", "MUST", False),
    ("hardening", "SHOULD", False),
    ("assurance_case", "MUST", True),
    ("static_analysis_common_vulnerabilities", "MUST", False),
    ("dynamic_analysis_unsafe", "MUST", False),
)

_GOLD_CRITERIA: tuple[tuple[str, str, bool], ...] = (
    ("achieve_silver", "MUST", False),
    ("bus_factor", "MUST", True),
    ("contributors_unassociated", "MUST", True),
    ("copyright_per_file", "MUST", False),
    ("license_per_file", "MUST", False),
    ("repo_distributed", "MUST", False),
    ("small_tasks", "MUST", True),
    ("require_2FA", "MUST", False),
    ("secure_2FA", "SHOULD", False),
    ("code_review_standards", "MUST", True),
    ("two_person_review", "MUST", False),
    ("build_reproducible", "MUST", True),
    ("test_invocation", "MUST", True),
    ("test_continuous_integration", "MUST", True),
    ("test_statement_coverage90", "MUST", False),
    ("test_branch_coverage80", "MUST", False),
    ("crypto_used_network", "MUST", False),
    ("crypto_tls12", "MUST", False),
    ("hardened_site", "MUST", True),
    ("security_review", "MUST", False),
    ("hardening", "MUST", True),
    ("dynamic_analysis", "MUST", False),
    ("dynamic_analysis_enable_assertions", "SHOULD", False),
)


class OpenSsfCriteriaCatalog:
    """Master catalog and registry for OpenSSF Best Practices criteria.

    Notes/Architectural Intent:
        Encapsulates the canonical OpenSSF criterion specifications for Passing,
        Silver, and Gold tiers. Uses immutable tuples and read-only mappings to
        prevent accidental runtime mutation or global state drift.
    """

    _BY_TIER: ClassVar[dict[OpenSsfTier, tuple[OpenSsfCriterionDefinition, ...]]] = {
        OpenSsfTier.PASSING: tuple(
            OpenSsfCriterionDefinition(
                criterion_id=cid,
                tier=OpenSsfTier.PASSING,
                category=cat,
                met_url_required=req_url,
            )
            for cid, cat, req_url in _PASSING_CRITERIA
        ),
        OpenSsfTier.SILVER: tuple(
            OpenSsfCriterionDefinition(
                criterion_id=cid,
                tier=OpenSsfTier.SILVER,
                category=cat,
                met_url_required=req_url,
            )
            for cid, cat, req_url in _SILVER_CRITERIA
        ),
        OpenSsfTier.GOLD: tuple(
            OpenSsfCriterionDefinition(
                criterion_id=cid,
                tier=OpenSsfTier.GOLD,
                category=cat,
                met_url_required=req_url,
            )
            for cid, cat, req_url in _GOLD_CRITERIA
        ),
    }

    @classmethod
    def for_tier(cls, tier: OpenSsfTier) -> tuple[OpenSsfCriterionDefinition, ...]:
        """Retrieve criteria definitions belonging to a specific certification tier.

        Args:
            tier: OpenSSF certification tier (Passing, Silver, Gold).

        Returns:
            Immutable tuple of criterion definitions.
        """
        return cls._BY_TIER.get(tier, ())

    @classmethod
    def get(
        cls, criterion_id: str, tier: OpenSsfTier | None = None
    ) -> OpenSsfCriterionDefinition | None:
        """Lookup a discrete criterion by identifier, optionally scoped to a tier.

        Args:
            criterion_id: Snake-case OpenSSF criterion key.
            tier: Optional tier to restrict search scope.

        Returns:
            Matching OpenSsfCriterionDefinition, or None if not found.
        """
        tiers_to_search = (tier,) if tier is not None else tuple(OpenSsfTier)
        for t in tiers_to_search:
            for defn in cls.for_tier(t):
                if defn.criterion_id == criterion_id:
                    return defn
        return None

    @classmethod
    def as_mapping(cls) -> MappingProxyType[OpenSsfTier, tuple[OpenSsfCriterionDefinition, ...]]:
        """Return an immutable read-only view of the criteria catalog."""
        return MappingProxyType(cls._BY_TIER)


CRITERIA_CATALOG: MappingProxyType[OpenSsfTier, tuple[OpenSsfCriterionDefinition, ...]] = (
    OpenSsfCriteriaCatalog.as_mapping()
)
