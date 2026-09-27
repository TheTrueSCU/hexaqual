"""Rich terminal presenter for Git lifecycle hooks and commit message verification.

Notes/Architectural Intent:
    Implements HooksPresenterPort to provide developer-facing tables,
    diagnostic panels, and actionable remediation steps using Rich.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexaqual.domain.hooks import HookManager
from hexaqual.ports.hooks import HooksPresenterPort

if TYPE_CHECKING:
    from hexaqual.domain.hooks import (
        CommitMsgReport,
        HooksInstallReport,
        HookStatusInfo,
        HooksUninstallReport,
    )

__all__ = [
    "RichHooksPresenter",
]


class RichHooksPresenter(HooksPresenterPort):
    """Rich console presenter for Git hooks commands."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional console override.

        Args:
            console: Rich console instance (defaults to standard console).
        """
        self.console = console or Console()

    def present_install(self, report: HooksInstallReport) -> int:
        """Render installation outcome to the console.

        Args:
            report: Outcome of the hook installation process.

        Returns:
            Process exit code (0 for success, 1 for failure).

        Notes/Architectural Intent:
            Displays summary cards indicating the installation mode and active hooks.
        """
        if not report.success:
            self.console.print(
                Panel(
                    "\n".join(report.details) or "Hook installation failed.",
                    title="[bold red]Git Hooks Installation Failed[/bold red]",
                    border_style="red",
                )
            )
            return 1

        table = Table(
            title=f"Git Hooks Installation ({report.mode.value} mode)",
            header_style="bold cyan",
        )
        table.add_column("Stage", style="bold")
        table.add_column("Status", justify="center")

        for stage in report.installed_stages:
            table.add_row(stage.value, "[bold green]INSTALLED[/bold green]")

        self.console.print(table)
        for detail in report.details:
            self.console.print(f"[dim]• {detail}[/dim]")
        self.console.print(
            "\n[bold green]✨ Git lifecycle hooks configured successfully![/bold green]\n"
        )
        return 0

    def present_uninstall(self, report: HooksUninstallReport) -> int:
        """Render uninstallation outcome to the console.

        Args:
            report: Outcome of the hook removal process.

        Returns:
            Process exit code (0 for success).

        Notes/Architectural Intent:
            Lists cleaned hook stages and confirmation details.
        """
        table = Table(title="Git Hooks Uninstallation", header_style="bold cyan")
        table.add_column("Stage", style="bold")
        table.add_column("Status", justify="center")

        for stage in report.removed_stages:
            table.add_row(stage.value, "[bold yellow]REMOVED[/bold yellow]")

        self.console.print(table)
        for detail in report.details:
            self.console.print(f"[dim]• {detail}[/dim]")
        self.console.print("\n[bold green]✨ Managed Git hooks uninstalled cleanly.[/bold green]\n")
        return 0

    def present_check(self, statuses: tuple[HookStatusInfo, ...]) -> int:
        """Render hook status inspection dashboard to the console.

        Args:
            statuses: Inspection status records for each hook stage.

        Returns:
            Process exit code (0 if all hooks installed, 1 if any hook missing).

        Notes/Architectural Intent:
            Summarizes manager type (pre-commit, native) and script locations.
        """
        table = Table(title="Repository Git Hooks Status", header_style="bold cyan")
        table.add_column("Stage", style="bold")
        table.add_column("Installed", justify="center")
        table.add_column("Manager", style="magenta")
        table.add_column("Script Path", style="dim")

        all_installed = True
        for st in statuses:
            if st.is_installed:
                inst_str = "[bold green]YES[/bold green]"
            else:
                inst_str = "[bold red]NO[/bold red]"
                all_installed = False

            mgr_str = st.manager.value
            if st.manager == HookManager.PRE_COMMIT:
                mgr_str = "[cyan]pre-commit[/cyan]"
            elif st.manager == HookManager.NATIVE:
                mgr_str = "[green]native[/green]"
            elif st.manager == HookManager.NONE:
                mgr_str = "[dim]none[/dim]"

            table.add_row(
                st.stage.value,
                inst_str,
                mgr_str,
                str(st.script_path),
            )

        self.console.print(table)
        if not all_installed:
            self.console.print(
                "[bold yellow]Run 'uv run hexaqual hooks install' to install missing hooks.[/bold yellow]\n"
            )
            return 1
        return 0

    def present_commit_msg(self, report: CommitMsgReport) -> int:
        """Render commit message validation report to the console.

        Args:
            report: Validation report with status and diagnostic error messages.

        Returns:
            Process exit code (0 if valid, 1 if invalid).

        Notes/Architectural Intent:
            Provides actionable hints for Conventional Commits and DCO sign-offs.
        """
        if report.is_valid:
            self.console.print(
                f"[bold green]✓ Commit message validated successfully:[/bold green] {report.title}"
            )
            return 0

        self.console.print(
            Panel(
                "\n".join(f"• {err}" for err in report.errors),
                title="[bold red]Commit Message Validation Failed[/bold red]",
                subtitle="OpenSSF & Semantic Governance Gate",
                border_style="red",
            )
        )
        return 1
