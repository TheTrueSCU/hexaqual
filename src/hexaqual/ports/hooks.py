"""Abstract ports defining Git hooks management and presentation interfaces.

Notes/Architectural Intent:
    Decoupled interfaces for inspecting, installing, uninstalling, and validating
    Git hooks. Implementations reside in adapters/ without bleeding into domain core.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from hexaqual.domain.hooks import (
    CommitMsgReport,
    HookInstallMode,
    HooksInstallReport,
    HookStatusInfo,
    HooksUninstallReport,
)

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "GitHooksPort",
    "HooksPresenterPort",
]


class GitHooksPort(ABC):
    """Abstract port for managing Git hooks and validating commit governance."""

    @abstractmethod
    def install_hooks(
        self,
        repo_root: Path,
        mode: HookInstallMode = HookInstallMode.AUTO,
    ) -> HooksInstallReport:
        """Install Git lifecycle hooks into the target repository.

        Args:
            repo_root: Path to the target repository root.
            mode: Installation strategy (auto, pre-commit, or native).

        Returns:
            HooksInstallReport detailing installed stages and execution mode.

        Raises:
            None.

        Notes/Architectural Intent:
            Configures either pre-commit multi-stage hooks or zero-dependency native
            bash scripts directly in .git/hooks/.
        """

    @abstractmethod
    def uninstall_hooks(
        self,
        repo_root: Path,
    ) -> HooksUninstallReport:
        """Uninstall Git lifecycle hooks from the target repository.

        Args:
            repo_root: Path to the target repository root.

        Returns:
            HooksUninstallReport detailing removed stages and outcomes.

        Raises:
            None.

        Notes/Architectural Intent:
            Removes managed hooks cleanly without disturbing unmanaged custom hooks.
        """

    @abstractmethod
    def check_hooks(
        self,
        repo_root: Path,
    ) -> tuple[HookStatusInfo, ...]:
        """Inspect the current installation status of all supported Git hooks.

        Args:
            repo_root: Path to the target repository root.

        Returns:
            Tuple of HookStatusInfo records for each lifecycle stage.

        Raises:
            None.

        Notes/Architectural Intent:
            Distinguishes between pre-commit managed, native hexaqual, unmanaged, and absent hooks.
        """

    @abstractmethod
    def validate_commit_msg(
        self,
        msg: str,
        require_dco: bool = True,
        require_conventional: bool = True,
    ) -> CommitMsgReport:
        """Validate a commit message against Conventional Commits and DCO sign-off rules.

        Args:
            msg: Raw commit message text to analyze.
            require_dco: Whether to enforce Developer Certificate of Origin (Signed-off-by:).
            require_conventional: Whether to enforce Conventional Commits title format.

        Returns:
            CommitMsgReport detailing validity and any diagnostic failure messages.

        Raises:
            None.

        Notes/Architectural Intent:
            Enforces OpenSSF Scorecard Gold DCO invariants and consistent semantic commit history.
        """


class HooksPresenterPort(ABC):
    """Abstract port for presenting Git hook results and diagnostics to developers."""

    @abstractmethod
    def present_install(self, report: HooksInstallReport) -> int:
        """Render installation outcome to the console or output stream.

        Args:
            report: Outcome of the hook installation process.

        Returns:
            Process exit code (0 for success).

        Raises:
            None.

        Notes/Architectural Intent:
            Formats success/failure cards and details in terminal tables.
        """

    @abstractmethod
    def present_uninstall(self, report: HooksUninstallReport) -> int:
        """Render uninstallation outcome to the console or output stream.

        Args:
            report: Outcome of the hook removal process.

        Returns:
            Process exit code (0 for success).

        Raises:
            None.

        Notes/Architectural Intent:
            Formats removal confirmations in terminal tables.
        """

    @abstractmethod
    def present_check(self, statuses: tuple[HookStatusInfo, ...]) -> int:
        """Render hook status inspection dashboard to the console or output stream.

        Args:
            statuses: Inspection status records for each hook stage.

        Returns:
            Process exit code (0 if all required hooks installed, 1 otherwise).

        Raises:
            None.

        Notes/Architectural Intent:
            Presents Rich status tables showing active managers and script paths.
        """

    @abstractmethod
    def present_commit_msg(self, report: CommitMsgReport) -> int:
        """Render commit message validation report to the console or output stream.

        Args:
            report: Validation report with status and diagnostic error messages.

        Returns:
            Process exit code (0 if valid, 1 if invalid).

        Raises:
            None.

        Notes/Architectural Intent:
            Provides actionable hints (e.g. `git commit -s --amend`) on validation failure.
        """
