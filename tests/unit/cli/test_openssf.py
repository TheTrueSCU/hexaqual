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
