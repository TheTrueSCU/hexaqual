"""Multi-format presenters for architecture and documentation generators.

Notes/Architectural Intent:
    Provides Rich interactive, JSON machine-readable, and GitHub Flavored Markdown
    presentation adapters for pydeps diagram generation, USAGE.md catalog synchronization,
    and pytest-archon test scaffolding.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexaqual.domain.generators import (
    ArchonReport,
    DocLinksReport,
    PydepsReport,
    UsageDocsReport,
)
from hexaqual.ports.generators import GeneratorPresenterPort


class RichGeneratorPresenterAdapter(GeneratorPresenterPort):
    """Interactive ANSI terminal presenter for generators using Rich."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize RichGeneratorPresenterAdapter with optional console.

        Args:
            console: Rich Console instance or None to instantiate default.
        """
        self.console = console or Console()

    def present_pydeps(self, report: PydepsReport) -> int:
        """Render generated or verified pydeps diagrams in a formatted table.

        Args:
            report: PydepsReport to render.

        Returns:
            0 if generation or verification was successful, 1 otherwise.

        Notes/Architectural Intent:
            Displays a colorized summary table listing all generated or checked SVG diagram
            assets, freshness status, and actionable diagnostic guidance.
        """
        if report.is_check:
            table = Table(
                title="[bold cyan]Architecture Dependency Diagram Freshness Check (pydeps)[/bold cyan]",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Asset / Package", style="bold")
            table.add_column("Output File", style="blue")
            table.add_column("Status", justify="center")
            table.add_column("Details", style="dim")

            for res in report.results:
                if res.details and "Graphviz 'dot' not installed" in res.details:
                    status = "[bold yellow]SKIP[/bold yellow]"
                elif res.success and not res.is_stale:
                    status = "[bold green]PASS[/bold green]"
                elif res.is_stale:
                    status = "[bold red]STALE[/bold red]"
                else:
                    status = "[bold red]FAIL[/bold red]"
                table.add_row(res.name, res.path, status, res.details)

            self.console.print(table)
            if report.is_successful:
                has_skip = any(
                    "Graphviz 'dot' not installed" in (r.details or "") for r in report.results
                )
                if has_skip and all(
                    "Graphviz 'dot' not installed" in (r.details or "") for r in report.results
                ):
                    self.console.print(
                        Panel.fit(
                            "[bold yellow]⏭️ Architecture diagram check skipped (Graphviz 'dot' not installed).[/bold yellow]",
                            border_style="yellow",
                        )
                    )
                else:
                    self.console.print(
                        Panel.fit(
                            f"[bold green]✨ All {len(report.results)} architecture dependency diagram(s) are up to date.[/bold green]",
                            border_style="green",
                        )
                    )
                return 0

            self.console.print(
                Panel.fit(
                    "[bold red]❌ One or more architecture diagrams are stale or missing.\n"
                    "Run 'hexaqual deps pydeps' or 'hexaqual deps pydeps --fix' to regenerate.[/bold red]",
                    border_style="red",
                )
            )
            return 1

        table = Table(
            title="[bold cyan]Architecture Dependency Diagram Generator (pydeps)[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Asset / Package", style="bold")
        table.add_column("Output File", style="blue")

        for res in report.results:
            table.add_row(res.name, res.path)

        self.console.print(table)
        if report.is_successful:
            self.console.print(
                Panel.fit(
                    f"[bold green]✨ Generated {len(report.results)} architecture dependency diagram(s) in docs/assets/pydeps/.[/bold green]",
                    border_style="green",
                )
            )
            return 0

        self.console.print(
            Panel.fit(
                "[bold red]❌ One or more architecture diagrams failed to generate.[/bold red]",
                border_style="red",
            )
        )
        return 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        """Render USAGE.md validation or update results.

        Args:
            report: UsageDocsReport containing status and diffs.

        Returns:
            0 if documentation is valid/current, 1 if out of date.

        Notes/Architectural Intent:
            Emits clear feedback with diffs when USAGE.md files are out of sync.
        """
        for f in report.up_to_date_files:
            self.console.print(f"[bold green]✓[/bold green] {f} is up to date.")
        for f in report.updated_files:
            self.console.print(f"[bold green]✓[/bold green] Updated {f}")
        for f in report.stale_files:
            self.console.print(
                f"[bold red]❌ {f} is out of date. Run 'uv run generate-usage-docs --fix' to update.[/bold red]"
            )

        for _, diff_text in report.diffs:
            self.console.print(diff_text)

        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        """Render pytest-archon test scaffolding summary.

        Args:
            report: ArchonReport containing created files.

        Returns:
            0 if successful, 1 if failure.

        Notes/Architectural Intent:
            Informs the developer about created or skipped architecture boundary tests.
        """
        for f in report.generated_files:
            self.console.print(f"[bold green]✓[/bold green] Scaffolded boundary tests in {f}")
        for s in report.skipped_files:
            self.console.print(f"[dim]Skipped {s} (no standard hexagonal layers present)[/dim]")
        return 0 if report.is_successful else 1

    def present_doc_links(self, report: DocLinksReport) -> int:
        """Render documentation link check summary table."""
        if report.broken_links:
            table = Table(
                title="[bold red]Documentation Link Integrity Check - Violations[/bold red]",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Source File", style="blue")
            table.add_column("Line", justify="right", style="cyan")
            table.add_column("Target Link", style="yellow")
            table.add_column("Reason", style="red")

            for broken in report.broken_links:
                table.add_row(broken.source_file, str(broken.line), broken.target, broken.reason)

            self.console.print(table)
            self.console.print(
                f"[bold red]❌ Found {len(report.broken_links)} broken link(s) across "
                f"{report.scanned_files_count} file(s) ({report.total_links_count} links checked)[/bold red]"
            )
            return 1

        self.console.print(
            f"[bold green]✅ All {report.total_links_count} link(s) valid across "
            f"{report.scanned_files_count} markdown file(s)![/bold green]"
        )
        return 0


class JsonGeneratorPresenterAdapter(GeneratorPresenterPort):
    """Machine-readable JSON presenter for generator outputs."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize JsonGeneratorPresenterAdapter."""
        self.console = console or Console()

    def present_pydeps(self, report: PydepsReport) -> int:
        """Format pydeps report as structured JSON."""
        data = {
            "is_successful": report.is_successful,
            "is_check": report.is_check,
            "total_diagrams": len(report.results),
            "diagrams": [
                {
                    "name": r.name,
                    "path": r.path,
                    "success": r.success,
                    "is_stale": r.is_stale,
                    "details": r.details,
                }
                for r in report.results
            ],
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        """Format USAGE.md report as structured JSON."""
        data = {
            "is_valid": report.is_valid,
            "up_to_date_files": list(report.up_to_date_files),
            "updated_files": list(report.updated_files),
            "stale_files": list(report.stale_files),
            "diffs": dict(report.diffs),
        }
        self.console.print_json(data=data)
        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        """Format pytest-archon report as structured JSON."""
        data = {
            "is_successful": report.is_successful,
            "generated_files": list(report.generated_files),
            "skipped_files": list(report.skipped_files),
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1

    def present_doc_links(self, report: DocLinksReport) -> int:
        """Format documentation link report as structured JSON."""
        data = {
            "is_successful": report.is_successful,
            "scanned_files_count": report.scanned_files_count,
            "total_links_count": report.total_links_count,
            "broken_links": [
                {
                    "source_file": b.source_file,
                    "line": b.line,
                    "target": b.target,
                    "reason": b.reason,
                }
                for b in report.broken_links
            ],
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1


class MarkdownGeneratorPresenterAdapter(GeneratorPresenterPort):
    """GitHub Flavored Markdown presenter for CI step summaries."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize MarkdownGeneratorPresenterAdapter."""
        self.console = console or Console()

    def present_pydeps(self, report: PydepsReport) -> int:
        """Render pydeps diagrams as a Markdown table."""
        title = (
            "### 📐 Architecture Dependency Diagrams Freshness Check"
            if report.is_check
            else "### 📐 Architecture Dependency Diagrams"
        )
        lines = [
            title,
            "",
            "| Asset / Package | Output File | Status |",
            "|---|---|---|",
        ]
        for r in report.results:
            if report.is_check:
                if r.details and "Graphviz 'dot' not installed" in r.details:
                    status = "⚠️ Skipped (dot not installed)"
                else:
                    status = "✅ Up to date" if r.success and not r.is_stale else "❌ Stale"
            else:
                status = "✅ Generated" if r.success else "❌ Failed"
            lines.append(f"| `{r.name}` | `{r.path}` | {status} |")
        lines.append("")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful else 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        """Render USAGE.md status as Markdown."""
        status = "✅ Up to date" if report.is_valid else "❌ Out of date"
        lines = [
            f"### 📖 USAGE.md Verification: {status}",
            "",
            f"- **Up to date**: {len(report.up_to_date_files)} file(s)",
            f"- **Updated**: {len(report.updated_files)} file(s)",
            f"- **Stale**: {len(report.stale_files)} file(s)",
            "",
        ]
        if report.diffs:
            lines.append("<details><summary>View Diffs</summary>\n")
            for f, diff_text in report.diffs:
                lines.append(f"#### `{f}`")
                lines.append(f"```diff\n{diff_text}\n```")
            lines.append("</details>\n")

        self.console.print("\n".join(lines))
        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        """Render pytest-archon results as Markdown."""
        lines = [
            "### 🏛️ Hexagonal Boundary Test Scaffolding",
            "",
            f"- **Generated**: {len(report.generated_files)} file(s)",
            f"- **Skipped**: {len(report.skipped_files)} file(s)",
            "",
        ]
        for f in report.generated_files:
            lines.append(f"- Generated: `{f}`")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful else 1

    def present_doc_links(self, report: DocLinksReport) -> int:
        """Render documentation link check results as Markdown."""
        status = "✅ All links valid" if report.is_successful else "❌ Broken links detected"
        lines = [
            f"### 🔗 Documentation Link Validation: {status}",
            "",
            f"- **Scanned Files**: {report.scanned_files_count}",
            f"- **Links Validated**: {report.total_links_count}",
            f"- **Broken Links**: {len(report.broken_links)}",
            "",
        ]
        if report.broken_links:
            lines.extend(
                [
                    "| Source File | Line | Target | Reason |",
                    "|---|---|---|---|",
                ]
            )
            for b in report.broken_links:
                lines.append(f"| `{b.source_file}` | {b.line} | `{b.target}` | {b.reason} |")
            lines.append("")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful else 1


def create_generator_presenter(
    format_name: str = "rich",
    console: Console | None = None,
) -> GeneratorPresenterPort:
    """Factory creating appropriate generator presenter based on format string.

    Args:
        format_name: Output format name ('rich', 'table', 'json', 'markdown').
        console: Optional Rich Console instance.

    Returns:
        GeneratorPresenterPort instance conforming to requested format.

    Notes/Architectural Intent:
        Encapsulates presenter selection so CLI entrypoints remain agnostic of
        concrete output format adapters.
    """
    fmt = format_name.lower().strip()
    if fmt == "json":
        return JsonGeneratorPresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownGeneratorPresenterAdapter(console=console)
    return RichGeneratorPresenterAdapter(console=console)


__all__ = [
    "create_generator_presenter",
    "JsonGeneratorPresenterAdapter",
    "MarkdownGeneratorPresenterAdapter",
    "RichGeneratorPresenterAdapter",
]
