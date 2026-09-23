"""Integration tests for hexaqual parity CLI subcommands.

Notes/Architectural Intent:
    Exercises test symmetry (1:1 parity) and optional extras forwarding verification
    against a realistic multi-package workspace.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hexaqual.cli.parity import parity_app


@pytest.mark.integration
def test_parity_test_clean(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify parity test passes when all src modules have matching tests.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)
    res = runner.invoke(parity_app, ["test"])
    assert res.exit_code == 0


@pytest.mark.integration
def test_parity_test_detects_orphan(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify parity test detects and reports orphaned source files without matching tests.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # Add orphaned module without corresponding test
    orphan = synthetic_workspace / "packages" / "pkg_core" / "src" / "pkg_core" / "untested.py"
    orphan.write_text('"""Untested module."""\n', encoding="utf-8")

    res = runner.invoke(parity_app, ["test"])
    assert res.exit_code != 0
    assert "untested" in res.stdout


@pytest.mark.integration
def test_parity_extras_clean(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify parity extras passes when all subpackage extras are forwarded.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)
    res = runner.invoke(parity_app, ["extras"])
    assert res.exit_code == 0


@pytest.mark.integration
def test_parity_extras_detects_unforwarded(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify parity extras flags missing subpackage extras in the umbrella package.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # Add new unforwarded extra to pkg_events
    events_pyproject = synthetic_workspace / "packages" / "pkg_events" / "pyproject.toml"
    content = events_pyproject.read_text(encoding="utf-8")
    content = content.replace(
        'huey = ["huey>=3.3.4"]',
        'huey = ["huey>=3.3.4"]\nredis = ["redis>=5.0.0"]',
    )
    events_pyproject.write_text(content, encoding="utf-8")

    res = runner.invoke(parity_app, ["extras"])
    # When missing extras are found, exit code is non-zero (1)
    assert res.exit_code != 0
    assert "redis" in res.stdout
