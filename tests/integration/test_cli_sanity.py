"""Integration tests for hexaqual check / sanity CLI commands.

Notes/Architectural Intent:
    Exercises the multi-stage quality sanity verification pipeline DAG
    in a synthetic workspace, validating all-pass outcomes and failure propagation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hexaqual.cli.main import app


@pytest.mark.integration
def test_sanity_help(runner: CliRunner) -> None:
    """Verify check and sanity commands render help and flags."""
    res_check = runner.invoke(app, ["check", "--help"])
    assert res_check.exit_code == 0
    assert "Execute the sanity check pipeline" in res_check.stdout

    res_sanity = runner.invoke(app, ["sanity", "--help"])
    assert res_sanity.exit_code == 0
    assert "Execute the sanity check pipeline" in res_sanity.stdout


@pytest.mark.integration
def test_sanity_clean_execution(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify check passes cleanly on a well-formed package.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    res = runner.invoke(
        app,
        [
            "check",
            "-p",
            "pkg_core",
            "--fix",
            "--skip-tests",
            "--skip-diagrams",
            "--skip-deptry",
            "--skip-typecheck",
        ],
    )
    assert res.exit_code == 0
    assert "PASS" in res.stdout or "passed" in res.stdout.lower()


@pytest.mark.integration
def test_sanity_detects_parity_violation(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify check fails when test symmetry is broken.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # Introduce an orphaned source file without matching test
    orphan = synthetic_workspace / "packages" / "pkg_core" / "src" / "pkg_core" / "untested.py"
    orphan.write_text('"""Untested module."""\n\n__all__: list[str] = []\n', encoding="utf-8")

    res = runner.invoke(
        app,
        [
            "check",
            "-p",
            "pkg_core",
            "--fix",
            "--skip-tests",
            "--skip-diagrams",
            "--skip-deptry",
            "--skip-typecheck",
        ],
    )
    assert res.exit_code != 0
    assert (
        "FAIL" in res.stdout or "untested" in res.stdout.lower() or "parity" in res.stdout.lower()
    )


@pytest.mark.integration
def test_sanity_detects_statement_violation(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify check fails when __all__ is unsorted.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # Break __all__ sorting in pkg_core/models.py
    models_file = synthetic_workspace / "packages" / "pkg_core" / "src" / "pkg_core" / "models.py"
    models_file.write_text('"""Models."""\n\n__all__ = ["Zebra", "Apple"]\n', encoding="utf-8")

    res = runner.invoke(
        app,
        [
            "check",
            "-p",
            "pkg_core",
            "--skip-tests",
            "--skip-diagrams",
            "--skip-deptry",
            "--skip-typecheck",
        ],
    )
    assert res.exit_code != 0
