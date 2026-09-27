"""Unit tests for Git hooks service layer functions.

Notes/Architectural Intent:
    Validates orchestration between CLI commands, GitHooksAdapter, and HooksPresenterPort.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from hexaqual.adapters.hooks.service import (
    check_hooks_command,
    install_hooks_command,
    uninstall_hooks_command,
    validate_commit_msg_command,
)
from hexaqual.domain.hooks import (
    CommitMsgReport,
    HookInstallMode,
    HooksInstallReport,
    HooksUninstallReport,
)


def test_install_hooks_command(tmp_path: Path) -> None:
    """Verify install_hooks_command invokes adapter and presenter."""
    mock_adapter = MagicMock()
    mock_presenter = MagicMock()
    report = HooksInstallReport(
        mode=HookInstallMode.AUTO,
        installed_stages=(),
        details=(),
        success=True,
    )
    mock_adapter.install_hooks.return_value = report
    mock_presenter.present_install.return_value = 0

    exit_code = install_hooks_command(
        target_dir=tmp_path,
        mode=HookInstallMode.AUTO,
        presenter=mock_presenter,
        adapter=mock_adapter,
    )

    assert exit_code == 0
    assert mock_adapter.install_hooks.called is True
    assert mock_presenter.present_install.called is True


def test_uninstall_hooks_command(tmp_path: Path) -> None:
    """Verify uninstall_hooks_command invokes adapter and presenter."""
    mock_adapter = MagicMock()
    mock_presenter = MagicMock()
    report = HooksUninstallReport(removed_stages=(), details=(), success=True)
    mock_adapter.uninstall_hooks.return_value = report
    mock_presenter.present_uninstall.return_value = 0

    exit_code = uninstall_hooks_command(
        target_dir=tmp_path,
        presenter=mock_presenter,
        adapter=mock_adapter,
    )

    assert exit_code == 0
    assert mock_adapter.uninstall_hooks.called is True
    assert mock_presenter.present_uninstall.called is True


def test_check_hooks_command(tmp_path: Path) -> None:
    """Verify check_hooks_command inspects statuses and presents them."""
    mock_adapter = MagicMock()
    mock_presenter = MagicMock()
    mock_adapter.check_hooks.return_value = ()
    mock_presenter.present_check.return_value = 0

    exit_code = check_hooks_command(
        target_dir=tmp_path,
        presenter=mock_presenter,
        adapter=mock_adapter,
    )

    assert exit_code == 0
    assert mock_adapter.check_hooks.called is True
    assert mock_presenter.present_check.called is True


def test_validate_commit_msg_command(tmp_path: Path) -> None:
    """Verify validate_commit_msg_command with explicit text and file inputs."""
    mock_adapter = MagicMock()
    mock_presenter = MagicMock()
    report = CommitMsgReport(
        is_valid=True,
        title="feat: test",
        errors=(),
        dco_found=True,
        conventional_match=True,
    )
    mock_adapter.validate_commit_msg.return_value = report
    mock_presenter.present_commit_msg.return_value = 0

    # 1. Explicit text
    exit_text = validate_commit_msg_command(
        msg_text="feat: hello\n\nSigned-off-by: Dev <d@d.com>",
        presenter=mock_presenter,
        adapter=mock_adapter,
    )
    assert exit_text == 0

    # 2. File input
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("feat: file commit\n\nSigned-off-by: Dev <d@d.com>", encoding="utf-8")
    exit_file = validate_commit_msg_command(
        msg_file=msg_file,
        presenter=mock_presenter,
        adapter=mock_adapter,
    )
    assert exit_file == 0
