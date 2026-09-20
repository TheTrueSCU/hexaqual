"""Agent asset presenters supporting terminal, JSON, and Markdown output formats.

Notes/Architectural Intent:
    Decouples AgentSyncReport, AgentCheckReport, and asset catalogs from output
    presentation formats, enabling consumption by developers, pre-commit hooks,
    and automated CI pipelines.
"""

from __future__ import annotations

import json

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexaqual.domain.agents import (
    AgentAsset,
    AgentCheckReport,
    AgentSyncReport,
)
from hexaqual.ports.agents import AgentPresenterPort

__all__ = [
    "create_agent_presenter",
    "JsonAgentPresenterAdapter",
    "MarkdownAgentPresenterAdapter",
    "RichAgentPresenterAdapter",
]


class RichAgentPresenterAdapter(AgentPresenterPort):
    """Rich console presenter implementing AgentPresenterPort."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.

        Notes/Architectural Intent:
            Enables dependency injection of Rich console for capturing or testing.
        """
        self._console = console or Console()

    def present_sync(self, report: AgentSyncReport) -> int:
        """Render agent assets synchronization results.

        Args:
            report: The AgentSyncReport data to present.

        Returns:
            Exit code 0.

        Notes/Architectural Intent:
            Displays summary metrics and detail log for synchronized files.
        """
        table = Table(
            title="Hexaqual Universal Agent Guardrails Synchronization",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Category", style="bold", ratio=2)
        table.add_column("Count", justify="right", ratio=1)
        table.add_column("Status", justify="center", ratio=1)

        status_created = (
            "[bold green]CREATED[/bold green]" if report.created_count > 0 else "[dim]NONE[/dim]"
        )
        table.add_row("Created Assets", str(report.created_count), status_created)

        status_updated = (
            "[bold yellow]UPDATED[/bold yellow]" if report.updated_count > 0 else "[dim]NONE[/dim]"
        )
        table.add_row("Updated Assets", str(report.updated_count), status_updated)

        table.add_row(
            "Unchanged Assets", str(report.unchanged_count), "[bold blue]PASS[/bold blue]"
        )
        table.add_row(
            "Preserved Local Assets",
            str(report.preserved_unmanaged_count),
            "[bold magenta]PRESERVED[/bold magenta]",
        )

        self._console.print(table)

        if report.details:
            details_text = "\n".join(f"[cyan]•[/cyan] {d}" for d in report.details)
            panel = Panel(
                details_text,
                title="Synchronized Asset Operations",
                border_style="green",
            )
            self._console.print(panel)

        self._console.print(
            Panel(
                f"[bold green]✨ Synchronized {report.total_synced} managed asset(s); "
                f"{report.unchanged_count} up to date; {report.preserved_unmanaged_count} local asset(s) preserved.[/bold green]",
                box=box.ROUNDED,
                border_style="green",
            )
        )
        return 0

    def present_check(self, report: AgentCheckReport) -> int:
        """Render agent drift check results.

        Args:
            report: The AgentCheckReport data to present.

        Returns:
            0 if clean, 1 if drift detected.

        Notes/Architectural Intent:
            Enforces failure exit code when guardrails are missing or modified.
        """
        if report.is_clean:
            self._console.print(
                Panel(
                    "[bold green]✅ All managed agent rules, workflows, and skills match the installed hexaqual version.[/bold green]",
                    box=box.ROUNDED,
                    border_style="green",
                )
            )
            return 0

        table = Table(
            title="Agent Guardrails Drift Detection",
            box=box.ROUNDED,
            header_style="bold red",
            expand=True,
        )
        table.add_column("Asset", style="bold red", ratio=2)
        table.add_column("Issue", style="yellow", ratio=2)

        for f in report.missing_files:
            table.add_row(f, "[bold red]Missing Asset[/bold red]")
        for f in report.drifted_files:
            table.add_row(f, "[bold yellow]Content Drifted[/bold yellow]")

        self._console.print(table)
        self._console.print(
            Panel(
                "[bold red]❌ Managed agent guardrails have drifted or are missing.\n"
                "Run '[bold cyan]uv run hexaqual agents sync[/bold cyan]' to refresh them.[/bold red]",
                box=box.ROUNDED,
                border_style="red",
            )
        )
        return 1

    def present_list(self, assets: tuple[AgentAsset, ...]) -> int:
        """Render catalog of bundled agent assets.

        Args:
            assets: Tuple of available bundled AgentAsset items.

        Returns:
            Exit code 0.

        Notes/Architectural Intent:
            Displays catalog grouped by kind (rules, workflows, skills).
        """
        table = Table(
            title="Hexaqual Universal Agent Guardrails Catalog",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Type", style="bold magenta", ratio=1)
        table.add_column("File Name", style="bold green", ratio=2)
        table.add_column("Path", style="dim", ratio=2)

        for a in sorted(assets, key=lambda x: (x.kind.value, x.name)):
            table.add_row(a.kind.value.capitalize(), a.name, a.relative_path)

        self._console.print(table)
        return 0


class JsonAgentPresenterAdapter(AgentPresenterPort):
    """JSON output presenter implementing AgentPresenterPort."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional console.

        Args:
            console: Optional Rich console.
        """
        self._console = console or Console()

    def present_sync(self, report: AgentSyncReport) -> int:
        """Render sync report as JSON."""
        data = {
            "created_count": report.created_count,
            "updated_count": report.updated_count,
            "unchanged_count": report.unchanged_count,
            "preserved_unmanaged_count": report.preserved_unmanaged_count,
            "total_synced": report.total_synced,
            "details": list(report.details),
        }
        self._console.print(json.dumps(data, indent=2))
        return 0

    def present_check(self, report: AgentCheckReport) -> int:
        """Render check report as JSON."""
        data = {
            "is_clean": report.is_clean,
            "missing_files": list(report.missing_files),
            "drifted_files": list(report.drifted_files),
            "details": list(report.details),
        }
        self._console.print(json.dumps(data, indent=2))
        return 0 if report.is_clean else 1

    def present_list(self, assets: tuple[AgentAsset, ...]) -> int:
        """Render asset list as JSON."""
        data = [{"name": a.name, "kind": a.kind.value, "path": a.relative_path} for a in assets]
        self._console.print(json.dumps(data, indent=2))
        return 0


class MarkdownAgentPresenterAdapter(AgentPresenterPort):
    """Markdown output presenter implementing AgentPresenterPort."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional console.

        Args:
            console: Optional Rich console.
        """
        self._console = console or Console()

    def present_sync(self, report: AgentSyncReport) -> int:
        """Render sync report as Markdown."""
        lines = [
            "# Hexaqual Universal Agent Guardrails Synchronization",
            "",
            "| Category | Count |",
            "|---|---|",
            f"| Created Assets | {report.created_count} |",
            f"| Updated Assets | {report.updated_count} |",
            f"| Unchanged Assets | {report.unchanged_count} |",
            f"| Preserved Local Assets | {report.preserved_unmanaged_count} |",
            "",
        ]
        if report.details:
            lines.append("### Details")
            for d in report.details:
                lines.append(f"- {d}")
        self._console.print("\n".join(lines))
        return 0

    def present_check(self, report: AgentCheckReport) -> int:
        """Render check report as Markdown."""
        if report.is_clean:
            self._console.print(
                "✅ All managed agent guardrails match the installed hexaqual version."
            )
            return 0
        lines = [
            "# Agent Guardrails Drift Report",
            "",
            "| Asset | Status |",
            "|---|---|",
        ]
        for f in report.missing_files:
            lines.append(f"| {f} | Missing |")
        for f in report.drifted_files:
            lines.append(f"| {f} | Content Drifted |")
        self._console.print("\n".join(lines))
        return 1

    def present_list(self, assets: tuple[AgentAsset, ...]) -> int:
        """Render asset list as Markdown."""
        lines = [
            "# Hexaqual Universal Agent Guardrails Catalog",
            "",
            "| Type | File Name | Path |",
            "|---|---|---|",
        ]
        for a in sorted(assets, key=lambda x: (x.kind.value, x.name)):
            lines.append(f"| {a.kind.value.capitalize()} | {a.name} | {a.relative_path} |")
        self._console.print("\n".join(lines))
        return 0


def create_agent_presenter(
    format_type: str = "table", console: Console | None = None
) -> AgentPresenterPort:
    """Factory creating an AgentPresenterPort based on format specifier.

    Args:
        format_type: Requested output presentation format ('table', 'json', 'markdown').
        console: Optional Rich Console instance.

    Returns:
        Instance implementing AgentPresenterPort.

    Notes/Architectural Intent:
        Standard factory pattern used across Hexaqual presenters.
    """
    if format_type == "json":
        return JsonAgentPresenterAdapter(console=console)
    if format_type == "markdown":
        return MarkdownAgentPresenterAdapter(console=console)
    return RichAgentPresenterAdapter(console=console)
