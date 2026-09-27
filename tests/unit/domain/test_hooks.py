"""Unit tests for Git hooks domain models and value objects.

Notes/Architectural Intent:
    Verifies construction, immutability, and field properties of HookStage,
    HookInstallMode, HookManager, HookStatusInfo, and validation reports.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.domain.hooks import (
    CommitMsgReport,
    HookInstallMode,
    HookManager,
    HooksInstallReport,
    HookStage,
    HookStatusInfo,
    HooksUninstallReport,
)


def test_hook_stage_values() -> None:
    """Validate enumeration values for HookStage.

    Notes/Architectural Intent:
        Ensures stages match standard Git hook file names.
    """
    pre_commit = HookStage.PRE_COMMIT.value
    commit_msg = HookStage.COMMIT_MSG.value
    pre_push = HookStage.PRE_PUSH.value
    post_merge = HookStage.POST_MERGE.value
    post_checkout = HookStage.POST_CHECKOUT.value

    assert pre_commit == "pre-commit"
    assert commit_msg == "commit-msg"
    assert pre_push == "pre-push"
    assert post_merge == "post-merge"
    assert post_checkout == "post-checkout"


def test_hook_install_mode_values() -> None:
    """Validate enumeration values for HookInstallMode."""
    auto_mode = HookInstallMode.AUTO.value
    native_mode = HookInstallMode.NATIVE.value
    pre_commit_mode = HookInstallMode.PRE_COMMIT.value

    assert auto_mode == "auto"
    assert native_mode == "native"
    assert pre_commit_mode == "pre-commit"


def test_hook_manager_values() -> None:
    """Validate enumeration values for HookManager."""
    native_mgr = HookManager.NATIVE.value
    pre_commit_mgr = HookManager.PRE_COMMIT.value
    none_mgr = HookManager.NONE.value
    unknown_mgr = HookManager.UNKNOWN.value

    assert native_mgr == "native"
    assert pre_commit_mgr == "pre-commit"
    assert none_mgr == "none"
    assert unknown_mgr == "unknown"


def test_hook_status_info_construction() -> None:
    """Validate HookStatusInfo dataclass properties."""
    path = Path("/repo/.git/hooks/pre-commit")
    info = HookStatusInfo(
        stage=HookStage.PRE_COMMIT,
        is_installed=True,
        manager=HookManager.PRE_COMMIT,
        script_path=path,
    )

    stage = info.stage
    is_installed = info.is_installed
    manager = info.manager
    script_path = info.script_path

    assert stage == HookStage.PRE_COMMIT
    assert is_installed is True
    assert manager == HookManager.PRE_COMMIT
    assert script_path == path


def test_hooks_install_report() -> None:
    """Validate HooksInstallReport dataclass properties."""
    report = HooksInstallReport(
        mode=HookInstallMode.NATIVE,
        installed_stages=(HookStage.PRE_COMMIT, HookStage.POST_MERGE),
        details=("Installed pre-commit", "Installed post-merge"),
        success=True,
    )

    mode = report.mode
    stages = report.installed_stages
    success = report.success

    assert mode == HookInstallMode.NATIVE
    assert stages == (HookStage.PRE_COMMIT, HookStage.POST_MERGE)
    assert success is True


def test_hooks_uninstall_report() -> None:
    """Validate HooksUninstallReport dataclass properties."""
    report = HooksUninstallReport(
        removed_stages=(HookStage.PRE_COMMIT,),
        details=("Removed pre-commit",),
        success=True,
    )

    stages = report.removed_stages
    success = report.success

    assert stages == (HookStage.PRE_COMMIT,)
    assert success is True


def test_commit_msg_report() -> None:
    """Validate CommitMsgReport dataclass properties."""
    report = CommitMsgReport(
        is_valid=True,
        title="feat(hooks): add git hooks support",
        errors=(),
        dco_found=True,
        conventional_match=True,
    )

    is_valid = report.is_valid
    title = report.title
    dco = report.dco_found
    conv = report.conventional_match

    assert is_valid is True
    assert title == "feat(hooks): add git hooks support"
    assert dco is True
    assert conv is True
