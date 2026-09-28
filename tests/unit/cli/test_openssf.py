"""Unit tests for OpenSSF CLI commands.

Notes/Architectural Intent:
    Verifies Typer command invocation for 'hexaqual openssf audit' and
    'hexaqual openssf propose' using Typer's CliRunner.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.main import app
from hexaqual.domain.openssf import (
    OpenSsfProject,
)

runner = CliRunner()


@patch("hexaqual.cli.openssf.OpenSsfBadgeAdapter")
def test_openssf_audit_command(mock_adapter_cls: MagicMock) -> None:
    """Test 'hexaqual openssf audit' output rendering."""
    mock_adapter = MagicMock()
    mock_adapter_cls.return_value = mock_adapter

    mock_project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="passing",
        tiered_percentage=100,
        criteria_statuses={"tests_documented_added": "Met"},
    )
    mock_adapter.fetch_project.return_value = mock_project

    result = runner.invoke(app, ["openssf", "audit", "--tier", "passing", "--project-id", "14749"])
    assert result.exit_code == 0
    assert "OpenSSF Project" in result.output
    assert "hexaqual" in result.output

    res_json = runner.invoke(
        app, ["openssf", "audit", "--tier", "passing", "--project-id", "14749", "-f", "json"]
    )
    assert res_json.exit_code == 0
    assert '"score": 100' in res_json.output


@patch("hexaqual.cli.openssf.OpenSsfBadgeAdapter")
def test_openssf_propose_command(mock_adapter_cls: MagicMock) -> None:
    """Test 'hexaqual openssf propose' generating URLs."""
    mock_adapter = MagicMock()
    mock_adapter_cls.return_value = mock_adapter

    mock_project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="in_progress",
        tiered_percentage=80,
        criteria_statuses={"tests_documented_added": "?"},
    )
    mock_adapter.fetch_project.return_value = mock_project
    mock_adapter.build_proposal_urls.return_value = [
        "https://www.bestpractices.dev/en/projects/14749/passing/edit?tests_documented_added_status=Met"
    ]

    result = runner.invoke(
        app, ["openssf", "propose", "--tier", "passing", "--project-id", "14749"]
    )
    assert result.exit_code == 0
    assert "Generated 1 Proposal URL(s)" in result.output
    assert "bestpractices.dev" in result.output


@patch("hexaqual.cli.openssf.OpenSsfBadgeAdapter")
def test_openssf_checklist_command(mock_adapter_cls: MagicMock) -> None:
    """Test 'hexaqual openssf checklist' with json and markdown formats."""
    mock_adapter = MagicMock()
    mock_adapter_cls.return_value = mock_adapter

    mock_project = OpenSsfProject(
        project_id=14749,
        name="hexaqual",
        repo_url="https://github.com/TheTrueSCU/hexaqual",
        badge_level="passing",
        tiered_percentage=100,
        criteria_statuses={"description_good": "Met"},
    )
    mock_adapter.fetch_project.return_value = mock_project

    # Rich table format
    res_rich = runner.invoke(app, ["openssf", "checklist", "-t", "passing", "-i", "14749"])
    assert res_rich.exit_code == 0
    assert "OpenSSF Best Practices Checklist" in res_rich.output

    # JSON format
    res_json = runner.invoke(
        app, ["openssf", "checklist", "-t", "passing", "-i", "14749", "-f", "json"]
    )
    assert res_json.exit_code == 0
    assert '"criterion_id": "description_good"' in res_json.output

    # Markdown format
    res_md = runner.invoke(
        app, ["openssf", "checklist", "-t", "passing", "-i", "14749", "-f", "markdown"]
    )
    assert res_md.exit_code == 0
    assert "# OpenSSF Best Practices Checklist: hexaqual" in res_md.output


@patch("hexaqual.cli.openssf.OpenSsfScorecardAdapter")
def test_openssf_scorecard_command(mock_adapter_cls: MagicMock) -> None:
    """Test 'hexaqual openssf scorecard' with rich and json formats."""
    from hexaqual.domain.openssf import ScorecardCheck, ScorecardResult

    mock_adapter = MagicMock()
    mock_adapter_cls.return_value = mock_adapter

    mock_result = ScorecardResult(
        repo="github.com/TheTrueSCU/hexastack",
        score=7.5,
        date="2026-09-27",
        checks=[ScorecardCheck(name="SAST", score=10, reason="CodeQL found", details=["workflow"])],
    )
    mock_adapter.fetch_scorecard.return_value = mock_result

    # Rich format
    res_rich = runner.invoke(
        app, ["openssf", "scorecard", "--repo", "TheTrueSCU/hexastack", "--details"]
    )
    assert res_rich.exit_code == 0
    assert "OpenSSF Scorecard" in res_rich.output
    assert "7.5/10" in res_rich.output

    # JSON format
    res_json = runner.invoke(
        app, ["openssf", "scorecard", "--repo", "TheTrueSCU/hexastack", "-f", "json"]
    )
    assert res_json.exit_code == 0
    assert '"score": 7.5' in res_json.output


@patch("hexaqual.cli.openssf.scaffold_document")
def test_openssf_scaffold_command(mock_scaffold: MagicMock) -> None:
    """Test 'hexaqual openssf scaffold' command execution."""
    from pathlib import Path

    mock_scaffold.return_value = Path("SECURITY.md")

    result = runner.invoke(app, ["openssf", "scaffold", "security"])
    assert result.exit_code == 0
    assert "Successfully generated" in result.output
