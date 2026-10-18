"""User Journey HQ-03: OpenSSF Best Practices Audit & Remediation demo test.

Notes/Architectural Intent:
    Demonstrates OpenSSF compliance auditing, criteria checklists, security scorecard
    evaluation, and compliance policy document scaffolding using Hexaqual.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from hexastack_cli.testing.narrator import CliNarrator

from hexaqual.cli.main import app
from hexaqual.domain.openssf import (
    OpenSsfProject,
    ScorecardCheck,
    ScorecardResult,
)


@pytest.mark.demo
def test_openssf_journey(tmp_path: Path) -> None:
    """Execute and record the OpenSSF Best Practices Audit & Remediation demo.

    Args:
        tmp_path: Temporary directory fixture provided by pytest.

    Notes/Architectural Intent:
        Hermetically mocks external OpenSSF REST APIs while rendering genuine
        Rich terminal tables, audit verdicts, and security documentation scaffolding.
    """
    mock_project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="passing",
        tiered_percentage=100,
        criteria_statuses={"tests_documented_added": "Met"},
    )
    mock_scorecard = ScorecardResult(
        repo="TheTrueSCU/hexaqual",
        score=9.8,
        date="2026-10-18",
        checks=[
            ScorecardCheck("Binary-Artifacts", 10, "No binary artifacts found"),
            ScorecardCheck("Branch-Protection", 10, "Branch protection enabled"),
            ScorecardCheck("Code-Review", 9, "All changes reviewed"),
            ScorecardCheck("Pinned-Dependencies", 10, "Dependencies pinned by hash"),
        ],
    )

    repo_root = Path(__file__).resolve().parent.parent.parent
    output_dir = repo_root / "docs" / "assets" / "demos"

    narrator = CliNarrator(
        app,
        output_name="hexaqual-openssf-audit",
        output_dir=output_dir,
    )

    with (
        patch("hexaqual.cli.openssf.OpenSsfBadgeAdapter") as mock_badge_cls,
        patch("hexaqual.cli.openssf.OpenSsfScorecardAdapter") as mock_scorecard_cls,
        patch("hexaqual.cli.openssf.scaffold_document", return_value=tmp_path / "SECURITY.md"),
    ):
        mock_badge_cls.return_value.fetch_project.return_value = mock_project
        mock_scorecard_cls.return_value.fetch_scorecard.return_value = mock_scorecard

        # Step 1: OpenSSF badge audit
        narrator.step("1. Auditing OpenSSF Best Practices badge criteria and compliance posture")
        res_audit = narrator.run_command(
            ["openssf", "audit", "--tier", "passing", "--project-id", "14749"]
        )
        code_audit = res_audit.exit_code
        assert code_audit == 0
        has_audit_dash = "OpenSSF Best Practices Audit" in res_audit.stdout
        assert has_audit_dash is True
        has_score = "100%" in res_audit.stdout
        assert has_score is True

        # Step 2: OpenSSF criteria checklist
        narrator.step("2. Inspecting OpenSSF Best Practices checklist and remediation status")
        res_checklist = narrator.run_command(
            ["openssf", "checklist", "--tier", "passing", "--project-id", "14749"]
        )
        code_checklist = res_checklist.exit_code
        assert code_checklist == 0
        has_checklist_title = "OpenSSF Best Practices Checklist" in res_checklist.stdout
        assert has_checklist_title is True

        # Step 3: OpenSSF Scorecard supply chain security metrics
        narrator.step("3. Auditing OpenSSF Scorecard supply chain security metrics")
        res_scorecard = narrator.run_command(
            ["openssf", "scorecard", "--repo", "TheTrueSCU/hexaqual", "-d"]
        )
        code_scorecard = res_scorecard.exit_code
        assert code_scorecard == 0
        has_scorecard_title = "Security Scorecard Checks" in res_scorecard.stdout
        assert has_scorecard_title is True
        has_checks = "Branch-Protection" in res_scorecard.stdout
        assert has_checks is True

        # Step 4: Scaffold compliance policy
        narrator.step("4. Scaffolding standardized OpenSSF security compliance policy")
        res_scaffold = narrator.run_command(["openssf", "scaffold", "security", "--force"])
        code_scaffold = res_scaffold.exit_code
        assert code_scaffold == 0
        has_scaffold_success = "Successfully generated" in res_scaffold.stdout
        assert has_scaffold_success is True

    artifacts = narrator.finish()
    if os.environ.get("RECORD_DEMO") == "1":
        vtt = artifacts.get("vtt")
        vtt_exists = vtt is not None and vtt.is_file()
        assert vtt_exists is True

        webm = artifacts.get("webm")
        webm_exists = webm is not None and webm.is_file()
        assert webm_exists is True
