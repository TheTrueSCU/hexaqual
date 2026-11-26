"""Multi-format IaC audit and discovery presenters implementing IacPresenterPort.

Notes/Architectural Intent:
    Decouples domain IaC audit and inventory reports from rendering targets,
    supporting Rich terminal tables, structured JSON payloads, and GitHub
    Flavored Markdown summaries per ADR-002.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexaqual.domain.iac import (
    IacAuditReport,
    IacCheckStatus,
    IacFinding,
    IacInventoryReport,
)
from hexaqual.ports.iac import IacPresenterPort

__all__ = [
    "create_iac_presenter",
    "JsonIacPresenterAdapter",
    "MarkdownIacPresenterAdapter",
    "RichIacPresenterAdapter",
]

_MAX_RENDERED_FINDINGS = 50


def _rel_display(path: Path, root: Path) -> str:
    """Format a path relative to ``root`` when possible."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _format_location(finding: IacFinding) -> str:
    """Format ``file_path:line`` string for display."""
    if finding.line is not None:
        return f"{finding.file_path}:{finding.line}"
    return finding.file_path


def _serialize_inventory(report: IacInventoryReport) -> dict[str, Any]:
    """Serialize ``IacInventoryReport`` into a JSON-compatible dictionary."""
    inv = report.inventory
    root = report.repo_root
    return {
        "repo_root": str(root),
        "has_any": inv.has_any,
        "total_files": inv.total_files,
        "assets": {
            "tofu_dirs": [_rel_display(p, root) for p in inv.tofu_dirs],
            "tofu_files": [_rel_display(p, root) for p in inv.tofu_files],
            "dockerfiles": [_rel_display(p, root) for p in inv.dockerfiles],
            "k8s_paths": [_rel_display(p, root) for p in inv.k8s_paths],
            "shell_scripts": [_rel_display(p, root) for p in inv.shell_scripts],
        },
        "tools": [
            {
                "tool": t.tool.value,
                "binary": t.binary,
                "installed": t.installed,
                "resolved_path": t.resolved_path or None,
            }
            for t in report.tools
        ],
    }


def _serialize_audit(report: IacAuditReport) -> dict[str, Any]:
    """Serialize ``IacAuditReport`` into a JSON-compatible dictionary."""
    inv = report.inventory
    return {
        "status": "PASS" if report.exit_code == 0 else "FAIL",
        "exit_code": report.exit_code,
        "total_duration": round(report.total_duration, 4),
        "has_iac_assets": inv.has_any,
        "total_files": inv.total_files,
        "total_findings": len(report.findings),
        "results": [
            {
                "tool": r.tool.value,
                "category": r.category.value,
                "status": r.status.value,
                "duration": round(r.duration, 4),
                "targets_checked": r.targets_checked,
                "findings_count": len(r.findings),
                "details": r.details,
                "error_output": r.error_output or None,
            }
            for r in report.results
        ],
        "findings": [
            {
                "tool": f.tool.value,
                "category": f.category.value,
                "severity": f.severity.value,
                "rule_id": f.rule_id,
                "file_path": f.file_path,
                "line": f.line,
                "message": f.message,
                "remediation": f.remediation or None,
            }
            for f in report.findings
        ],
    }


class RichIacPresenterAdapter(IacPresenterPort):
    """Rich terminal presenter rendering IaC audits and asset inventories."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with an optional Rich console instance.

        Args:
            console: Optional Rich ``Console`` sink.
        """
        self._console = console or Console()

    def _render_findings_table(self, findings: tuple[IacFinding, ...]) -> None:
        """Render detailed findings table capped at ``_MAX_RENDERED_FINDINGS`` rows."""
        if not findings:
            return
        ftable = Table(
            title="IaC Findings & Diagnostics",
            box=box.ROUNDED,
            header_style="bold yellow",
            expand=True,
        )
        ftable.add_column("Tool", style="bold", ratio=1)
        ftable.add_column("Severity", justify="center", ratio=1)
        ftable.add_column("Rule", style="cyan", ratio=1)
        ftable.add_column("Location", style="magenta", ratio=2)
        ftable.add_column("Message", ratio=4)

        for finding in findings[:_MAX_RENDERED_FINDINGS]:
            ftable.add_row(
                finding.tool.value,
                finding.severity.value,
                finding.rule_id or "-",
                _format_location(finding),
                finding.message,
            )

        self._console.print(ftable)
        if len(findings) > _MAX_RENDERED_FINDINGS:
            remaining = len(findings) - _MAX_RENDERED_FINDINGS
            self._console.print(
                f"[dim]... {remaining} additional finding(s) omitted; use --format json for full output.[/dim]"
            )

    def present_iac_audit(self, report: IacAuditReport) -> int:
        """Render IaC lint, validation, and misconfiguration scan outcomes in Rich tables.

        Args:
            report: Aggregated ``IacAuditReport``.

        Returns:
            Process exit code (0 if clean, 1 if failures occurred).
        """
        table = Table(
            title="Hexaqual IaC Quality & Security Dashboard",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Tool", style="bold", ratio=2)
        table.add_column("Category", style="magenta", ratio=1)
        table.add_column("Status", justify="center", ratio=1)
        table.add_column("Targets", justify="right", ratio=1)
        table.add_column("Findings", justify="right", ratio=1)
        table.add_column("Duration", justify="right", ratio=1)
        table.add_column("Details", style="dim", ratio=3)

        status_styles = {
            IacCheckStatus.PASS: "[bold green]✅ PASS[/bold green]",
            IacCheckStatus.FAIL: "[bold red]❌ FAIL[/bold red]",
            IacCheckStatus.SKIP: "[yellow]⏭️ SKIP[/yellow]",
        }
        for res in report.results:
            table.add_row(
                res.tool.value,
                res.category.value,
                status_styles.get(res.status, res.status.value),
                str(res.targets_checked),
                str(len(res.findings)),
                f"{res.duration:.2f}s",
                res.details,
            )

        self._console.print()
        self._console.print(table)
        self._render_findings_table(report.findings)

        failures = [r for r in report.results if r.status == IacCheckStatus.FAIL]
        for fail in failures:
            if fail.error_output and not fail.findings:
                self._console.print(
                    Panel(
                        fail.error_output,
                        title=f"[bold red]❌ {fail.tool.value} Error[/bold red]",
                        border_style="red",
                    )
                )

        if not report.inventory.has_any:
            self._console.print(
                Panel(
                    f"[yellow]⏭️ No IaC assets discovered under {report.repo_root}; skipped cleanly.[/yellow]",
                    border_style="yellow",
                )
            )
        elif failures:
            self._console.print(
                Panel(
                    f"[bold red]❌ {len(failures)} IaC gate(s) failed ({len(report.findings)} finding(s)) in {report.total_duration:.2f}s.[/bold red]",
                    border_style="red",
                )
            )
        else:
            self._console.print(
                Panel(
                    f"[bold green]✨ All IaC gates completed cleanly in {report.total_duration:.2f}s![/bold green]",
                    border_style="green",
                )
            )
        return report.exit_code

    def present_iac_inventory(self, report: IacInventoryReport) -> int:
        """Render discovered IaC assets and tool availability tables.

        Args:
            report: Aggregated ``IacInventoryReport``.

        Returns:
            Process exit code (always 0).
        """
        inv = report.inventory
        asset_table = Table(
            title="Discovered IaC Assets",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        asset_table.add_column("Category", style="bold magenta", ratio=2)
        asset_table.add_column("Count", justify="right", ratio=1)
        asset_table.add_column("Paths", style="dim", ratio=5)

        root = report.repo_root
        rows = [
            ("OpenTofu / Terraform Dirs", inv.tofu_dirs),
            ("OpenTofu / Terraform Files", inv.tofu_files),
            ("Dockerfiles", inv.dockerfiles),
            ("Kubernetes / Helm", inv.k8s_paths),
            ("Shell Scripts", inv.shell_scripts),
        ]
        for label, items in rows:
            preview = ", ".join(_rel_display(p, root) for p in items[:5])
            if len(items) > 5:
                preview += f" (+{len(items) - 5} more)"
            asset_table.add_row(label, str(len(items)), preview or "-")

        self._console.print()
        self._console.print(asset_table)

        tool_table = Table(
            title="External IaC Tool Readiness",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        tool_table.add_column("Gate", style="bold", ratio=2)
        tool_table.add_column("Binary", style="cyan", ratio=1)
        tool_table.add_column("Status", justify="center", ratio=1)
        tool_table.add_column("Resolved Path", style="dim", ratio=4)

        for tool_info in report.tools:
            status_txt = (
                "[bold green]✅ INSTALLED[/bold green]"
                if tool_info.installed
                else "[yellow]⏭️ MISSING[/yellow]"
            )
            tool_table.add_row(
                tool_info.tool.value,
                tool_info.binary,
                status_txt,
                tool_info.resolved_path or "-",
            )

        self._console.print(tool_table)
        return 0


class JsonIacPresenterAdapter(IacPresenterPort):
    """Machine-readable JSON presenter for IaC audit and discovery outputs."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with an optional Rich console sink.

        Args:
            console: Optional ``Console`` instance.
        """
        self._console = console or Console()

    def present_iac_audit(self, report: IacAuditReport) -> int:
        """Serialize ``IacAuditReport`` as pretty-printed JSON.

        Args:
            report: Aggregated ``IacAuditReport``.

        Returns:
            Process exit code.
        """
        self._console.out(json.dumps(_serialize_audit(report), indent=2), highlight=False)
        return report.exit_code

    def present_iac_inventory(self, report: IacInventoryReport) -> int:
        """Serialize ``IacInventoryReport`` as pretty-printed JSON.

        Args:
            report: Aggregated ``IacInventoryReport``.

        Returns:
            Process exit code (always 0).
        """
        self._console.out(json.dumps(_serialize_inventory(report), indent=2), highlight=False)
        return 0


class MarkdownIacPresenterAdapter(IacPresenterPort):
    """GitHub-flavored Markdown presenter for IaC CI step summaries and docs."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with an optional Rich console sink.

        Args:
            console: Optional ``Console`` instance.
        """
        self._console = console or Console()

    def render_iac_audit_markdown(self, report: IacAuditReport) -> str:
        """Format ``IacAuditReport`` into GitHub-flavored Markdown.

        Args:
            report: Aggregated ``IacAuditReport``.

        Returns:
            Rendered Markdown text.
        """
        lines = [
            "### Hexaqual IaC Quality & Security Dashboard",
            "",
            "| Tool | Category | Status | Targets | Findings | Duration | Details |",
            "| :--- | :--- | :---: | ---: | ---: | ---: | :--- |",
        ]
        icons = {
            IacCheckStatus.PASS: "✅ PASS",
            IacCheckStatus.FAIL: "❌ FAIL",
            IacCheckStatus.SKIP: "⏭️ SKIP",
        }
        for res in report.results:
            icon = icons.get(res.status, res.status.value)
            lines.append(
                f"| `{res.tool.value}` | {res.category.value} | {icon} | "
                f"{res.targets_checked} | {len(res.findings)} | {res.duration:.2f}s | {res.details} |"
            )

        lines.append("")
        if report.findings:
            lines.extend(
                [
                    "#### Findings",
                    "",
                    "| Tool | Severity | Rule | Location | Message |",
                    "| :--- | :---: | :--- | :--- | :--- |",
                ]
            )
            for finding in report.findings[:_MAX_RENDERED_FINDINGS]:
                msg = finding.message.replace("|", "\\|").replace("\n", " ")
                lines.append(
                    f"| `{finding.tool.value}` | {finding.severity.value} | "
                    f"`{finding.rule_id or '-'}` | `{_format_location(finding)}` | {msg} |"
                )
            lines.append("")

        if not report.inventory.has_any:
            lines.append("> ⏭️ **No IaC assets discovered; checks skipped cleanly.**")
        elif report.exit_code == 0:
            lines.append(
                f"> ✨ **All IaC gates completed cleanly in {report.total_duration:.2f}s.**"
            )
        else:
            failures = sum(1 for r in report.results if r.status == IacCheckStatus.FAIL)
            lines.append(
                f"> ❌ **{failures} IaC gate(s) failed ({len(report.findings)} finding(s)) in {report.total_duration:.2f}s.**"
            )
        return "\n".join(lines)

    def render_iac_inventory_markdown(self, report: IacInventoryReport) -> str:
        """Format ``IacInventoryReport`` into GitHub-flavored Markdown.

        Args:
            report: Aggregated ``IacInventoryReport``.

        Returns:
            Rendered Markdown text.
        """
        inv = report.inventory
        lines = [
            "### Discovered IaC Assets & Tool Readiness",
            "",
            f"- **OpenTofu / Terraform Dirs**: {len(inv.tofu_dirs)}",
            f"- **OpenTofu / Terraform Files**: {len(inv.tofu_files)}",
            f"- **Dockerfiles**: {len(inv.dockerfiles)}",
            f"- **Kubernetes / Helm Paths**: {len(inv.k8s_paths)}",
            f"- **Shell Scripts**: {len(inv.shell_scripts)}",
            "",
            "| Gate | Binary | Status | Path |",
            "| :--- | :--- | :---: | :--- |",
        ]
        for tool_info in report.tools:
            status_txt = "✅ INSTALLED" if tool_info.installed else "⏭️ MISSING"
            path_txt = f"`{tool_info.resolved_path}`" if tool_info.resolved_path else "-"
            lines.append(
                f"| `{tool_info.tool.value}` | `{tool_info.binary}` | {status_txt} | {path_txt} |"
            )
        return "\n".join(lines)

    def present_iac_audit(self, report: IacAuditReport) -> int:
        """Print Markdown IaC audit summary and return exit status.

        Args:
            report: Aggregated ``IacAuditReport``.

        Returns:
            Process exit code.
        """
        self._console.print(self.render_iac_audit_markdown(report))
        return report.exit_code

    def present_iac_inventory(self, report: IacInventoryReport) -> int:
        """Print Markdown IaC inventory report and return 0.

        Args:
            report: Aggregated ``IacInventoryReport``.

        Returns:
            Process exit code (always 0).
        """
        self._console.print(self.render_iac_inventory_markdown(report))
        return 0


def create_iac_presenter(
    format_type: str = "table",
    console: Console | None = None,
) -> IacPresenterPort:
    """Factory creating an ``IacPresenterPort`` adapter for the requested format.

    Args:
        format_type: Presentation format (``table``, ``rich``, ``json``, ``markdown``, ``md``).
        console: Optional Rich ``Console`` sink.

    Returns:
        Configured ``IacPresenterPort`` instance.

    Raises:
        ValueError: If ``format_type`` is unrecognized.

    Notes/Architectural Intent:
        Matches ``create_governance_presenter`` factory semantics across output formats.
    """
    fmt = format_type.strip().lower()
    if fmt in ("table", "rich"):
        return RichIacPresenterAdapter(console=console)
    if fmt == "json":
        return JsonIacPresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownIacPresenterAdapter(console=console)

    raise ValueError(
        f"Unsupported IaC presenter format: {format_type!r}. "
        "Supported formats: 'table', 'rich', 'json', 'markdown'."
    )
