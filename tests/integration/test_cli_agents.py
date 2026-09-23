"""Integration tests for hexaqual agents CLI subcommands.

Notes/Architectural Intent:
    Exercises end-to-end synchronization, listing, and drift detection of universal
    agent assets (.agents rules, workflows, skills) across synthetic workspaces.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hexaqual.cli.agents import agents_app


@pytest.mark.integration
def test_agents_list(runner: CliRunner) -> None:
    """Verify hexaqual agents list renders the catalog of packaged assets.

    Args:
        runner: CLI execution runner.
    """
    res = runner.invoke(agents_app, ["list"])
    assert res.exit_code == 0
    assert "hexaqual-test-pyramid" in res.stdout or "rules" in res.stdout


@pytest.mark.integration
def test_agents_sync_and_check_lifecycle(synthetic_workspace: Path, runner: CliRunner) -> None:
    """Verify sync installs all managed guardrails and check validates identity.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
    """
    # 1. Run sync
    res_sync = runner.invoke(agents_app, ["sync", "-t", str(synthetic_workspace)])
    assert res_sync.exit_code == 0

    agents_dir = synthetic_workspace / ".agents"
    rules_dir = agents_dir / "rules"
    assert rules_dir.is_dir()

    # Verify newly added rules are materialized
    test_pyramid_rule = rules_dir / "hexaqual-test-pyramid.md"
    assert test_pyramid_rule.is_file()
    assert "Four-Tier Testing Pyramid" in test_pyramid_rule.read_text(encoding="utf-8")

    modifications_rule = rules_dir / "hexaqual-modifications.md"
    assert modifications_rule.is_file()

    tooling_rule = rules_dir / "hexaqual-tooling.md"
    assert tooling_rule.is_file()

    # 2. Run check - should pass with zero drift
    res_check = runner.invoke(agents_app, ["check", "-t", str(synthetic_workspace)])
    assert res_check.exit_code == 0

    # 3. Modify a rule to simulate developer drift
    test_pyramid_rule.write_text("DRIFTED CONTENT", encoding="utf-8")

    # 4. Run check again - should fail and detect drift
    res_drift = runner.invoke(agents_app, ["check", "-t", str(synthetic_workspace)])
    assert res_drift.exit_code != 0
