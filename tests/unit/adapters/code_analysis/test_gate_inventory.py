"""Unit tests for quality gate inventory audit adapter.

Notes/Architectural Intent:
    Verifies detection of canonical quality gates, reporting of active vs. missing
    controls, and exit code logic.
"""

from __future__ import annotations

import os
from pathlib import Path

from hexaqual.adapters.code_analysis.gate_inventory import audit_gate_inventory


def test_audit_gate_inventory_empty_repo(tmp_path: Path) -> None:
    """Verify missing status for canonical gates in an empty directory."""
    report = audit_gate_inventory(tmp_path)
    assert report.exit_code == 1
    missing_items = [i for i in report.items if i.status == "MISSING"]
    assert len(missing_items) > 0
    names = [i.name for i in missing_items]
    assert "Static Linter (Ruff)" in names
    assert "1:1 Unit Test Symmetry" in names


def test_audit_gate_inventory_configured_repo(tmp_path: Path) -> None:
    """Verify active status when canonical configuration files and hooks are present."""
    # Ruff
    (tmp_path / "ruff.toml").write_text("", encoding="utf-8")
    # Ty
    (tmp_path / "ty.toml").write_text("", encoding="utf-8")
    # Tests unit
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    # Architecture tests
    arch_dir = tmp_path / "tests" / "architecture"
    arch_dir.mkdir()
    (arch_dir / "test_hexagonal_boundaries.py").write_text("", encoding="utf-8")
    # Git hook
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    os.chmod(hook, 0o700)
    # AGENTS.md and rules
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    rules_dir = tmp_path / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "hexastack-reanchoring.md").write_text("# Rule\n", encoding="utf-8")
    # docs/decisions.md
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "decisions.md").write_text("# Decisions\n", encoding="utf-8")

    report = audit_gate_inventory(tmp_path)
    assert report.exit_code == 0
    missing = [i for i in report.items if i.status == "MISSING"]
    assert len(missing) == 0

    active_names = [i.name for i in report.items if i.status == "ACTIVE"]
    assert "Static Linter (Ruff)" in active_names
    assert "Type Checking (Ty)" in active_names
    assert "1:1 Unit Test Symmetry" in active_names
    assert "Hexagonal Boundary Isolation" in active_names
    assert "Git Lifecycle Hooks" in active_names
    assert "AI Agent Guardrails Index" in active_names
    assert "Architectural Decisions & Re-Anchoring" in active_names
