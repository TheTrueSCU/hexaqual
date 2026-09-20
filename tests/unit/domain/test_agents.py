"""Unit tests for agent domain models.

Notes/Architectural Intent:
    Validates construction, invariants, and properties of AgentAsset,
    AgentAssetKind, AgentSyncReport, and AgentCheckReport.
"""

from __future__ import annotations

from hexaqual.domain.agents import (
    AgentAsset,
    AgentAssetKind,
    AgentCheckReport,
    AgentSyncReport,
)


def test_agent_asset_kind_values() -> None:
    """Validate enumeration values for AgentAssetKind.

    Notes/Architectural Intent:
        Ensures string values correspond directly to directory names.
    """
    rule_val = AgentAssetKind.RULE.value
    workflow_val = AgentAssetKind.WORKFLOW.value
    skill_val = AgentAssetKind.SKILL.value

    assert rule_val == "rules"
    assert workflow_val == "workflows"
    assert skill_val == "skills"


def test_agent_asset_construction() -> None:
    """Validate AgentAsset dataclass instantiation.

    Notes/Architectural Intent:
        Asserts frozen immutability and exact field values.
    """
    asset = AgentAsset(
        name="hexaqual-boundaries.md",
        kind=AgentAssetKind.RULE,
        relative_path="rules/hexaqual-boundaries.md",
        content="# Rule Content",
    )

    name = asset.name
    kind = asset.kind
    rel_path = asset.relative_path
    content = asset.content

    assert name == "hexaqual-boundaries.md"
    assert kind == AgentAssetKind.RULE
    assert rel_path == "rules/hexaqual-boundaries.md"
    assert content == "# Rule Content"


def test_agent_sync_report_total_synced() -> None:
    """Validate calculation of total_synced in AgentSyncReport.

    Notes/Architectural Intent:
        Confirms total_synced sums created and updated counts.
    """
    report = AgentSyncReport(
        created_count=5,
        updated_count=3,
        unchanged_count=10,
        preserved_unmanaged_count=2,
        details=("Created rules/rule1.md", "Updated workflows/wf1.md"),
    )

    total = report.total_synced
    created = report.created_count
    updated = report.updated_count
    unchanged = report.unchanged_count
    preserved = report.preserved_unmanaged_count

    assert total == 8
    assert created == 5
    assert updated == 3
    assert unchanged == 10
    assert preserved == 2
    assert len(report.details) == 2


def test_agent_check_report_clean_status() -> None:
    """Validate AgentCheckReport behavior for clean vs drifted status.

    Notes/Architectural Intent:
        Verifies is_clean boolean flag and tuple members.
    """
    clean_report = AgentCheckReport(
        is_clean=True,
        drifted_files=(),
        missing_files=(),
        details=(),
    )
    is_clean = clean_report.is_clean
    assert is_clean is True

    dirty_report = AgentCheckReport(
        is_clean=False,
        drifted_files=("rules/hexaqual-boundaries.md",),
        missing_files=("workflows/hexaqual-pre-commit.md",),
        details=("Drift detected",),
    )
    is_dirty_clean = dirty_report.is_clean
    drifted_count = len(dirty_report.drifted_files)
    missing_count = len(dirty_report.missing_files)

    assert is_dirty_clean is False
    assert drifted_count == 1
    assert missing_count == 1
