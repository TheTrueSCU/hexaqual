"""Unit tests for Git hooks port interfaces.

Notes/Architectural Intent:
    Validates abstract method contracts for GitHooksPort and HooksPresenterPort.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hexaqual.domain.hooks import (
    CommitMsgReport,
    HookInstallMode,
    HooksInstallReport,
    HookStatusInfo,
    HooksUninstallReport,
)
from hexaqual.ports.hooks import GitHooksPort, HooksPresenterPort


class DummyGitHooksPort(GitHooksPort):
    """Concrete test stub for GitHooksPort."""

    def install_hooks(
        self,
        repo_root: Path,
        mode: HookInstallMode = HookInstallMode.AUTO,
    ) -> HooksInstallReport:
        return HooksInstallReport(mode=mode, installed_stages=(), details=(), success=True)

    def uninstall_hooks(self, repo_root: Path) -> HooksUninstallReport:
        return HooksUninstallReport(removed_stages=(), details=(), success=True)

    def check_hooks(self, repo_root: Path) -> tuple[HookStatusInfo, ...]:
        return ()

    def validate_commit_msg(
        self,
        msg: str,
        require_dco: bool = True,
        require_conventional: bool = True,
    ) -> CommitMsgReport:
        return CommitMsgReport(
            is_valid=True,
            title="dummy",
            errors=(),
            dco_found=True,
            conventional_match=True,
        )


class DummyHooksPresenterPort(HooksPresenterPort):
    """Concrete test stub for HooksPresenterPort."""

    def present_install(self, report: HooksInstallReport) -> int:
        return 0

    def present_uninstall(self, report: HooksUninstallReport) -> int:
        return 0

    def present_check(self, statuses: tuple[HookStatusInfo, ...]) -> int:
        return 0

    def present_commit_msg(self, report: CommitMsgReport) -> int:
        return 0


def test_git_hooks_port_abstract_instantiation() -> None:
    """Verify GitHooksPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        GitHooksPort()  # type: ignore[abstract]


def test_hooks_presenter_port_abstract_instantiation() -> None:
    """Verify HooksPresenterPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        HooksPresenterPort()  # type: ignore[abstract]


def test_dummy_ports_conformance() -> None:
    """Verify concrete stubs implement all abstract methods."""
    hooks_port = DummyGitHooksPort()
    presenter_port = DummyHooksPresenterPort()

    install_rep = hooks_port.install_hooks(Path("."))
    uninstall_rep = hooks_port.uninstall_hooks(Path("."))
    statuses = hooks_port.check_hooks(Path("."))
    commit_rep = hooks_port.validate_commit_msg("feat: test")

    p_install = presenter_port.present_install(install_rep)
    p_uninstall = presenter_port.present_uninstall(uninstall_rep)
    p_check = presenter_port.present_check(statuses)
    p_commit = presenter_port.present_commit_msg(commit_rep)

    assert install_rep.success is True
    assert uninstall_rep.success is True
    assert len(statuses) == 0
    assert commit_rep.is_valid is True
    assert p_install == 0
    assert p_uninstall == 0
    assert p_check == 0
    assert p_commit == 0
