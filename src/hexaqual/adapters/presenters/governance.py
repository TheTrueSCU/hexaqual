"""Governance presenters supporting terminal, JSON, and Markdown output formats.

Notes/Architectural Intent:
    Decouples domain verification outcomes (SanityCheckReport, __all__ checks, test parity)
    from presentation formats, enabling unified consumption by humans (Rich table),
    automated machines / IDEs (JSON), and CI step summaries (Markdown).
"""

from __future__ import annotations

import json

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexaqual.domain.governance import (
    CheckStatus,
    GateInventoryReport,
    SanityCheckReport,
)
from hexaqual.ports.governance import GovernancePresenterPort

__all__ = [
    "create_governance_presenter",
    "JsonGovernancePresenterAdapter",
    "MarkdownGovernancePresenterAdapter",
    "RichGovernancePresenterAdapter",
]


class RichGovernancePresenterAdapter(GovernancePresenterPort):
    """Rich console presenter implementing GovernancePresenterPort with tables and panels."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_sanity_dashboard(self, report: SanityCheckReport) -> int:
        """Render sanity check results table and diagnostics to console.

        Args:
            report: Aggregated SanityCheckReport object.

        Returns:
            Process exit code (0 for pass, 1 for failure).
        """
        table = Table(
            title="Hexastack Scoped Sanity Check Dashboard",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Check", style="bold", ratio=2)
        table.add_column("Target", style="magenta", ratio=2)
        table.add_column("Status", justify="center", ratio=1)
        table.add_column("Duration", justify="right", ratio=1)
        table.add_column("Details", style="dim", ratio=4)

        for res in report.results:
            status_style = {
                CheckStatus.PASS: "[bold green]✅ PASS[/bold green]",
                CheckStatus.FAIL: "[bold red]❌ FAIL[/bold red]",
                CheckStatus.SKIP: "[yellow]⏭️ SKIP[/yellow]",
            }.get(res.status, str(res.status.value))

            table.add_row(
                res.check_name,
                res.target_name,
                status_style,
                f"{res.duration:.2f}s",
                res.details,
            )

        self._console.print()
        self._console.print(table)

        failures = [r for r in report.results if r.status == CheckStatus.FAIL]
        for f in failures:
            if f.error_output:
                self._console.print(
                    Panel(
                        f.error_output,
                        title=f"[bold red]❌ {f.check_name} Failure ({f.target_name})[/bold red]",
                        border_style="red",
                    )
                )

        if failures:
            self._console.print(
                Panel(
                    f"[bold red]❌ {len(failures)} check(s) failed in {report.total_duration:.2f}s.[/bold red]\n"
                    "Fix reported errors or run with [bold cyan]--fix[/bold cyan] where supported.",
                    border_style="red",
                )
            )
        else:
            self._console.print(
                Panel(
                    f"[bold green]✨ All {len(report.results)} sanity checks passed in {report.total_duration:.2f}s![/bold green]",
                    border_style="green",
                )
            )

        return report.exit_code

    def present_all_statements(
        self,
        errors: list[str],
        modified_count: int | None = None,
    ) -> int:
        """Render __all__ statement results using Rich tables and panels.

        Args:
            errors: List of detected __all__ error strings.
            modified_count: Optional count of modified files during autofix.

        Returns:
            0 if clean/success, 1 if violations found.
        """
        if modified_count is not None:
            self._console.print(
                Panel.fit(
                    f"[bold green]✨ Formatted and alphabetized __all__ statements in {modified_count} file(s).[/bold green]",
                    border_style="green",
                )
            )
            return 0

        if errors:
            table = Table(
                title="[bold red]API Surface & __all__ Integrity Violations[/bold red]",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Location & Violation")
            for err in errors:
                table.add_row(err)
            self._console.print(table)
            return 1

        return 0

    def present_test_parity(
        self,
        init_errors: list[str],
        symmetry_errors: list[str],
    ) -> int:
        """Render test parity results using Rich tables and panels.

        Args:
            init_errors: Errors regarding missing __init__.py in test directories.
            symmetry_errors: Errors regarding missing or orphaned unit test files.

        Returns:
            0 if clean, 1 if parity violations found.
        """
        all_errors = init_errors + symmetry_errors
        if all_errors:
            table = Table(
                title="[bold red]❌ Test Parity & Directory Integrity Violations[/bold red]",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Violation Type", width=24, style="bold red")
            table.add_column("Details")

            for err in init_errors:
                table.add_row("Missing __init__.py", err)
            for err in symmetry_errors:
                table.add_row("Asymmetry / Missing Test", err)

            self._console.print(table)
            return 1

        self._console.print(
            Panel(
                "[bold green]✅ All source modules mirror unit tests 1:1 and all test directories contain __init__.py.[/bold green]",
                border_style="green",
            )
        )
        return 0

    def present_architecture_parity(
        self,
        errors: list[str],
    ) -> int:
        """Render architecture test parity outcomes in Rich tables.

        Args:
            errors: List of detected architecture parity violation errors.

        Returns:
            0 if clean, 1 if errors detected.
        """
        if errors:
            table = Table(
                title="[bold red]Architecture Test Parity Violations[/bold red]",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Error", style="red")
            for err in errors:
                table.add_row(err)
            self._console.print(table)
            return 1

        self._console.print(
            Panel(
                "[bold green]✅ All packages satisfy architecture test parity.[/bold green]",
                border_style="green",
            )
        )
        return 0

    def present_gate_inventory(
        self,
        report: GateInventoryReport,
    ) -> int:
        """Render repository quality gate inventory matrix and status in Rich table.

        Args:
            report: Aggregated GateInventoryReport object.

        Returns:
            0 if all required gates active, 1 if any missing.
        """
        table = Table(
            title="Repository Quality Gate Inventory Matrix",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Category", style="bold magenta", ratio=2)
        table.add_column("Quality Gate", style="bold", ratio=3)
        table.add_column("Status", justify="center", ratio=1)
        table.add_column("Details", style="dim", ratio=4)
        table.add_column("Remediation", style="yellow", ratio=3)

        for item in report.items:
            status_style = {
                "ACTIVE": "[bold green]✅ ACTIVE[/bold green]",
                "WARNING": "[bold yellow]⚠️ WARNING[/bold yellow]",
                "MISSING": "[bold red]❌ MISSING[/bold red]",
            }.get(item.status, item.status)
            table.add_row(
                item.category,
                item.name,
                status_style,
                item.details,
                item.remediation,
            )

        self._console.print()
        self._console.print(table)

        missing = [i for i in report.items if i.status == "MISSING"]
        warnings = [i for i in report.items if i.status == "WARNING"]

        if missing:
            self._console.print(
                Panel(
                    f"[bold red]❌ {len(missing)} required quality gate(s) are missing or deactivated![/bold red]\n"
                    "Address the missing gates or configuration items listed above.",
                    border_style="red",
                )
            )
        elif warnings:
            self._console.print(
                Panel(
                    f"[bold yellow]⚠️ All required quality gates active with {len(warnings)} warning(s).[/bold yellow]",
                    border_style="yellow",
                )
            )
        else:
            self._console.print(
                Panel(
                    f"[bold green]✨ All {len(report.items)} canonical quality gates are fully configured and enforced![/bold green]",
                    border_style="green",
                )
            )
        return report.exit_code


class JsonGovernancePresenterAdapter(GovernancePresenterPort):
    """Machine-readable JSON presenter for governance outputs."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional console sink.

        Args:
            console: Optional Console instance for output writing.
        """
        self._console = console or Console()

    def present_sanity_dashboard(self, report: SanityCheckReport) -> int:
        """Serialize sanity check report to structured JSON.

        Args:
            report: Aggregated SanityCheckReport object.

        Returns:
            Process exit code.
        """
        payload = {
            "status": "PASS" if report.exit_code == 0 else "FAIL",
            "exit_code": report.exit_code,
            "total_duration": round(report.total_duration, 4),
            "results": [
                {
                    "check": r.check_name,
                    "target": r.target_name,
                    "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "duration": round(r.duration, 4),
                    "details": r.details,
                    "error_output": r.error_output or None,
                }
                for r in report.results
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return report.exit_code

    def present_all_statements(
        self,
        errors: list[str],
        modified_count: int | None = None,
    ) -> int:
        """Serialize __all__ outcomes to JSON.

        Args:
            errors: List of detected errors.
            modified_count: Optional count of modified files.

        Returns:
            0 if clean/success, 1 if errors detected.
        """
        payload = {
            "status": "FAIL" if errors else "PASS",
            "errors": errors,
            "modified_count": modified_count,
        }
        self._console.print(json.dumps(payload, indent=2))
        return 1 if errors else 0

    def present_test_parity(
        self,
        init_errors: list[str],
        symmetry_errors: list[str],
    ) -> int:
        """Serialize test parity results to JSON.

        Args:
            init_errors: Errors regarding missing __init__.py files.
            symmetry_errors: Errors regarding missing/orphaned test files.

        Returns:
            0 if clean, 1 if errors detected.
        """
        has_errors = bool(init_errors or symmetry_errors)
        payload = {
            "status": "FAIL" if has_errors else "PASS",
            "init_errors": init_errors,
            "symmetry_errors": symmetry_errors,
        }
        self._console.print(json.dumps(payload, indent=2))
        return 1 if has_errors else 0

    def present_architecture_parity(
        self,
        errors: list[str],
    ) -> int:
        """Serialize architecture test parity results to JSON.

        Args:
            errors: List of detected architecture parity errors.

        Returns:
            0 if clean, 1 if errors detected.
        """
        payload = {
            "status": "FAIL" if errors else "PASS",
            "errors": errors,
        }
        self._console.print(json.dumps(payload, indent=2))
        return 1 if errors else 0

    def present_gate_inventory(
        self,
        report: GateInventoryReport,
    ) -> int:
        """Serialize quality gate inventory report to structured JSON.

        Args:
            report: Aggregated GateInventoryReport object.

        Returns:
            Process exit code.
        """
        payload = {
            "status": "PASS" if report.exit_code == 0 else "FAIL",
            "exit_code": report.exit_code,
            "total_gates": len(report.items),
            "missing_count": sum(1 for i in report.items if i.status == "MISSING"),
            "warning_count": sum(1 for i in report.items if i.status == "WARNING"),
            "active_count": sum(1 for i in report.items if i.status == "ACTIVE"),
            "items": [
                {
                    "name": item.name,
                    "category": item.category,
                    "status": item.status,
                    "details": item.details,
                    "remediation": item.remediation,
                }
                for item in report.items
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return report.exit_code


class MarkdownGovernancePresenterAdapter(GovernancePresenterPort):
    """GitHub-flavored Markdown presenter for CI summaries and documentation."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional console sink.

        Args:
            console: Optional Console instance for output writing.
        """
        self._console = console or Console()

    def present_sanity_dashboard(self, report: SanityCheckReport) -> int:
        """Render sanity check results as a GitHub Markdown table with error details.

        Args:
            report: Aggregated SanityCheckReport object.

        Returns:
            Process exit code.
        """
        lines: list[str] = [
            "# Hexastack Scoped Sanity Check Dashboard",
            "",
            "| Check | Target | Status | Duration | Details |",
            "| :--- | :--- | :---: | :---: | :--- |",
        ]

        for res in report.results:
            icon = {
                CheckStatus.PASS: "✅ PASS",
                CheckStatus.FAIL: "❌ FAIL",
                CheckStatus.SKIP: "⏭️ SKIP",
            }.get(res.status, str(res.status))
            lines.append(
                f"| {res.check_name} | {res.target_name} | {icon} | {res.duration:.2f}s | {res.details} |"
            )

        lines.append("")
        if report.exit_code == 0:
            lines.append(
                f"> ✨ **All {len(report.results)} sanity checks passed in {report.total_duration:.2f}s!**"
            )
        else:
            failures = [r for r in report.results if r.status == CheckStatus.FAIL]
            lines.append(
                f"> ❌ **{len(failures)} check(s) failed in {report.total_duration:.2f}s.**"
            )
            lines.append("")
            lines.append("### Diagnostic Failures")
            for f in failures:
                if f.error_output:
                    lines.append(
                        f"<details><summary>❌ <b>{f.check_name} Failure ({f.target_name})</b></summary>\n"
                    )
                    lines.append("```")
                    lines.append(f.error_output.strip())
                    lines.append("```")
                    lines.append("</details>\n")

        self._console.print("\n".join(lines))
        return report.exit_code

    def present_all_statements(
        self,
        errors: list[str],
        modified_count: int | None = None,
    ) -> int:
        """Render __all__ outcomes as Markdown.

        Args:
            errors: List of detected errors.
            modified_count: Optional count of modified files.

        Returns:
            0 if clean/success, 1 if errors detected.
        """
        lines: list[str] = []
        if modified_count is not None:
            lines.append(
                f"> ✨ **Formatted and alphabetized `__all__` statements in {modified_count} file(s).**"
            )
            self._console.print("\n".join(lines))
            return 0

        if errors:
            lines.append("### ❌ `__all__` Integrity Violations")
            lines.append("")
            for err in errors:
                lines.append(f"- {err}")
            self._console.print("\n".join(lines))
            return 1

        lines.append("> ✅ **All `__all__` statements deduplicated and sorted.**")
        self._console.print("\n".join(lines))
        return 0

    def present_test_parity(
        self,
        init_errors: list[str],
        symmetry_errors: list[str],
    ) -> int:
        """Render test parity results as Markdown.

        Args:
            init_errors: Errors regarding missing __init__.py files.
            symmetry_errors: Errors regarding missing/orphaned test files.

        Returns:
            0 if clean, 1 if errors detected.
        """
        all_errors = init_errors + symmetry_errors
        if not all_errors:
            self._console.print(
                "> ✅ **All source modules mirror unit tests 1:1 and all test directories contain `__init__.py`.**"
            )
            return 0

        lines: list[str] = [
            "### ❌ Test Parity & Directory Integrity Violations",
            "",
            "| Violation Type | Details |",
            "| :--- | :--- |",
        ]
        for err in init_errors:
            lines.append(f"| Missing `__init__.py` | `{err}` |")
        for err in symmetry_errors:
            lines.append(f"| Asymmetry / Missing Test | `{err}` |")

        self._console.print("\n".join(lines))
        return 1

    def present_architecture_parity(
        self,
        errors: list[str],
    ) -> int:
        """Render architecture test parity outcomes as Markdown.

        Args:
            errors: List of detected architecture parity errors.

        Returns:
            0 if clean/success, 1 if errors detected.
        """
        lines: list[str] = []
        if errors:
            lines.append("### ❌ Architecture Test Parity Violations")
            lines.append("")
            for err in errors:
                lines.append(f"- {err}")
        else:
            lines.append("> ✅ **All packages satisfy architecture test parity.**")

        self._console.print("\n".join(lines))
        return 1 if errors else 0

    def present_gate_inventory(
        self,
        report: GateInventoryReport,
    ) -> int:
        """Render quality gate inventory report as Markdown table.

        Args:
            report: Aggregated GateInventoryReport object.

        Returns:
            Process exit code.
        """
        lines: list[str] = [
            "# Repository Quality Gate Inventory Matrix",
            "",
            "| Category | Quality Gate | Status | Details | Remediation |",
            "| :--- | :--- | :---: | :--- | :--- |",
        ]
        for item in report.items:
            icon = {
                "ACTIVE": "✅ ACTIVE",
                "WARNING": "⚠️ WARNING",
                "MISSING": "❌ MISSING",
            }.get(item.status, item.status)
            remediation = item.remediation or "-"
            lines.append(
                f"| {item.category} | {item.name} | {icon} | {item.details} | {remediation} |"
            )

        lines.append("")
        missing = [i for i in report.items if i.status == "MISSING"]
        if missing:
            lines.append(
                f"> ❌ **{len(missing)} required quality gate(s) missing or deactivated.**"
            )
        else:
            lines.append(
                f"> ✨ **All {len(report.items)} canonical quality gates are fully configured and active.**"
            )

        self._console.print("\n".join(lines))
        return report.exit_code


def create_governance_presenter(
    format_type: str = "table",
    console: Console | None = None,
) -> GovernancePresenterPort:
    """Factory creating GovernancePresenterPort instance for desired output format.

    Args:
        format_type: Output format name ('table', 'json', 'markdown').
        console: Optional Console instance.

    Returns:
        Configured GovernancePresenterPort adapter.

    Raises:
        ValueError: If format_type is not one of 'table', 'json', or 'markdown'.

    Notes/Architectural Intent:
        Centralizes presenter adapter selection by format keyword.
    """
    fmt = format_type.strip().lower()
    if fmt == "table":
        return RichGovernancePresenterAdapter(console=console)
    if fmt == "json":
        return JsonGovernancePresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownGovernancePresenterAdapter(console=console)

    raise ValueError(
        f"Unsupported presenter format: {format_type!r}. Supported formats: 'table', 'json', 'markdown'."
    )
