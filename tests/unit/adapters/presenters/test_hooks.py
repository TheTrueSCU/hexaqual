"""Unit tests for RichHooksPresenter.

Notes/Architectural Intent:
    Validates Rich console rendering for hook installation, uninstallation,
    inspection dashboard, and commit message validation reports.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from hexaqual.adapters.presenters.hooks import RichHooksPresenter
from hexaqual.domain.hooks import (
    CommitMsgReport,
    HookInstallMode,
    HookManager,
    HooksInstallReport,
    HookStage,
    HookStatusInfo,
    HooksUninstallReport,
)


def test_present_install() -> None:
    """Verify install rendering for successful and failing reports."""
    console = Console(record=True, width=120)
    presenter = RichHooksPresenter(console=console)

    # 1. Success
    success_report = HooksInstallReport(
        mode=HookInstallMode.NATIVE,
        installed_stages=(HookStage.PRE_COMMIT, HookStage.COMMIT_MSG),
        details=("Installed pre-commit", "Installed commit-msg"),
        success=True,
    )
    exit_success = presenter.present_install(success_report)
    assert exit_success == 0
    text = console.export_text()
    assert "pre-commit" in text
    assert "INSTALLED" in text

    # 2. Failure
    fail_report = HooksInstallReport(
        mode=HookInstallMode.PRE_COMMIT,
        installed_stages=(),
        details=("pre-commit executable not found",),
        success=False,
    )
    exit_fail = presenter.present_install(fail_report)
    assert exit_fail == 1


def test_present_uninstall() -> None:
    """Verify uninstallation rendering."""
    console = Console(record=True, width=120)
    presenter = RichHooksPresenter(console=console)

    report = HooksUninstallReport(
        removed_stages=(HookStage.PRE_COMMIT,),
        details=("Removed native hook: pre-commit",),
        success=True,
    )
    exit_code = presenter.present_uninstall(report)
    assert exit_code == 0
    text = console.export_text()
    assert "pre-commit" in text
    assert "REMOVED" in text


def test_present_check() -> None:
    """Verify status dashboard rendering."""
    console = Console(record=True, width=120)
    presenter = RichHooksPresenter(console=console)

    statuses = (
        HookStatusInfo(
            stage=HookStage.PRE_COMMIT,
            is_installed=True,
            manager=HookManager.PRE_COMMIT,
            script_path=Path("/repo/.git/hooks/pre-commit"),
        ),
        HookStatusInfo(
            stage=HookStage.COMMIT_MSG,
            is_installed=False,
            manager=HookManager.NONE,
            script_path=Path("/repo/.git/hooks/commit-msg"),
        ),
    )
    # One is missing, should return 1
    exit_code = presenter.present_check(statuses)
    assert exit_code == 1
    text = console.export_text()
    assert "pre-commit" in text
    assert "YES" in text
    assert "NO" in text


def test_present_commit_msg() -> None:
    """Verify commit message validation output."""
    console = Console(record=True, width=120)
    presenter = RichHooksPresenter(console=console)

    # 1. Valid
    valid_report = CommitMsgReport(
        is_valid=True,
        title="feat: valid commit",
        errors=(),
        dco_found=True,
        conventional_match=True,
    )
    exit_valid = presenter.present_commit_msg(valid_report)
    assert exit_valid == 0

    # 2. Invalid
    invalid_report = CommitMsgReport(
        is_valid=False,
        title="bad commit",
        errors=("Missing DCO sign-off.",),
        dco_found=False,
        conventional_match=False,
    )
    exit_invalid = presenter.present_commit_msg(invalid_report)
    assert exit_invalid == 1
    text = console.export_text()
    assert "Missing DCO sign-off" in text
