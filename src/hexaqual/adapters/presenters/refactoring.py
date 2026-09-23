"""Multi-format presenters for AST refactoring and article publication tooling.

Notes/Architectural Intent:
    Provides Rich interactive, JSON machine-readable, and Markdown presentation
    adapters for LibCST code alphabetization and DEV.to/Medium article publishing.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexaqual.domain.refactoring import (
    AlphabetizeCodeReport,
    MediumPublishReport,
)
from hexaqual.ports.refactoring import RefactoringPresenterPort


class RichRefactoringPresenterAdapter(RefactoringPresenterPort):
    """Interactive Rich ANSI presenter for refactoring tools."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize RichRefactoringPresenterAdapter with optional console."""
        self.console = console or Console()

    def present_alphabetize(self, report: AlphabetizeCodeReport) -> int:
        """Render alphabetization summary table and panel."""
        if not report.is_successful:
            self.console.print(
                Panel.fit(
                    "[bold red]❌ Code alphabetization encountered errors.[/bold red]",
                    border_style="red",
                )
            )
            return 1

        for f in report.reordered_files:
            self.console.print(f"[bold green]✓[/bold green] Alphabetized: {f}")

        msg = (
            f"[bold green]✨ Alphabetized functions in {len(report.reordered_files)} file(s). "
            f"({len(report.unchanged_files)} files already sorted)[/bold green]"
        )
        self.console.print(Panel.fit(msg, border_style="green"))
        return 0

    def present_medium_publish(self, report: MediumPublishReport) -> int:
        """Render article publication outcomes."""
        if report.status_table:
            table = Table(
                title="[bold cyan]docs/medium — Article Status[/bold cyan]",
                show_header=True,
                header_style="bold magenta",
                box=None,
            )
            table.add_column("Slug", style="bold")
            table.add_column("State")
            table.add_column("DEV.to ID")
            table.add_column("DEV.to URL")
            table.add_column("Medium URL")

            for slug, state, devto_id, devto_url, medium_url in report.status_table:
                styled_state = {
                    "syndicated": "[green]syndicated[/green]",
                    "published": "[blue]published[/blue]",
                    "draft": "[yellow]draft[/yellow]",
                    "local": "[dim]local[/dim]",
                    "parse error": "[red]parse error[/red]",
                }.get(state, state)
                table.add_row(slug, styled_state, devto_id, devto_url, medium_url)

            self.console.print(table)
            return 0 if report.is_successful else 1

        table = Table(
            title="[bold cyan]Medium & DEV.to Article Publication[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Article Slug", style="bold")
        table.add_column("DEV.to URL / ID", style="blue")

        for slug, url in report.details:
            table.add_row(slug, url)

        self.console.print(table)
        status_msg = (
            f"[bold green]✨ Successfully processed {report.published_count}/{report.total_count} article(s).[/bold green]"
            if report.is_successful
            else "[bold red]❌ Article publication encountered errors.[/bold red]"
        )
        self.console.print(
            Panel.fit(status_msg, border_style="green" if report.is_successful else "red")
        )
        return 0 if report.is_successful else 1


class JsonRefactoringPresenterAdapter(RefactoringPresenterPort):
    """Machine-readable JSON presenter for refactoring tools."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize JsonRefactoringPresenterAdapter."""
        self.console = console or Console()

    def present_alphabetize(self, report: AlphabetizeCodeReport) -> int:
        """Format alphabetization report as JSON."""
        data = {
            "is_successful": report.is_successful,
            "reordered_files": list(report.reordered_files),
            "unchanged_files": list(report.unchanged_files),
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1

    def present_medium_publish(self, report: MediumPublishReport) -> int:
        """Format medium publish report as JSON."""
        data = {
            "is_successful": report.is_successful,
            "published_count": report.published_count,
            "total_count": report.total_count,
            "details": [{"slug": slug, "url": url} for slug, url in report.details],
            "status_table": [
                {
                    "slug": slug,
                    "state": state,
                    "devto_id": devto_id,
                    "devto_url": devto_url,
                    "medium_url": medium_url,
                }
                for slug, state, devto_id, devto_url, medium_url in report.status_table
            ],
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1


class MarkdownRefactoringPresenterAdapter(RefactoringPresenterPort):
    """GitHub Flavored Markdown presenter for refactoring tools."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize MarkdownRefactoringPresenterAdapter."""
        self.console = console or Console()

    def present_alphabetize(self, report: AlphabetizeCodeReport) -> int:
        """Render alphabetization report as Markdown."""
        lines = [
            "### 🔤 Code Symbol Alphabetization",
            "",
            f"- **Modified**: {len(report.reordered_files)} file(s)",
            f"- **Unchanged**: {len(report.unchanged_files)} file(s)",
            "",
        ]
        for f in report.reordered_files:
            lines.append(f"- `{f}`")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful else 1

    def present_medium_publish(self, report: MediumPublishReport) -> int:
        """Render article publication report as Markdown table."""
        if report.status_table:
            lines = [
                "### 📝 docs/medium — Article Status",
                "",
                "| Slug | State | DEV.to ID | DEV.to URL | Medium URL |",
                "|---|---|---|---|---|",
            ]
            for slug, state, devto_id, devto_url, medium_url in report.status_table:
                lines.append(f"| `{slug}` | {state} | {devto_id} | {devto_url} | {medium_url} |")
            lines.append("")
            self.console.print("\n".join(lines))
            return 0 if report.is_successful else 1

        lines = [
            "### 📝 Medium & DEV.to Publication Report",
            "",
            "| Article Slug | Status / Link |",
            "|---|---|",
        ]
        for slug, url in report.details:
            lines.append(f"| `{slug}` | {url} |")
        lines.append("")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful else 1


def create_refactoring_presenter(
    format_name: str = "rich",
    console: Console | None = None,
) -> RefactoringPresenterPort:
    """Factory creating appropriate refactoring presenter based on format string.

    Args:
        format_name: Output format name ('rich', 'table', 'json', 'markdown').
        console: Optional Rich Console instance.

    Returns:
        RefactoringPresenterPort instance.
    """
    fmt = format_name.lower().strip()
    if fmt == "json":
        return JsonRefactoringPresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownRefactoringPresenterAdapter(console=console)
    return RichRefactoringPresenterAdapter(console=console)


__all__ = [
    "create_refactoring_presenter",
    "JsonRefactoringPresenterAdapter",
    "MarkdownRefactoringPresenterAdapter",
    "RichRefactoringPresenterAdapter",
]
