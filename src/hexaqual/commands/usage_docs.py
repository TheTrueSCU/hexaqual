"""Automated USAGE.md generator and verification quality gate for Hexastack packages."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from rich.console import Console

from hexaqual.infra.handlers.generators import (
    build_tools_usage_markdown,
    build_umbrella_usage_markdown,
    resolve_impacted_usage_targets,
    resolve_usage_target_rel_path,
)

console = Console()


def process_package_usage(
    target_key: str,
    root: Path,
    verify: bool,
    fix: bool,
) -> bool:
    """Process USAGE.md for a given target package. Returns True if in sync / fixed."""
    rel_path = resolve_usage_target_rel_path(target_key, root)
    usage_file = root / rel_path

    pyproject_path = usage_file.parent / "pyproject.toml"
    if not pyproject_path.is_file():
        pyproject_path = root / "pyproject.toml"
    new_content = build_tools_usage_markdown(pyproject_path.parent)

    if verify and not fix:
        if not usage_file.is_file():
            console.print(f"[bold red]❌ {rel_path} does not exist.[/bold red]")
            return False
        current_content = usage_file.read_text(encoding="utf-8")
        if current_content.strip() != new_content.strip():
            console.print(
                f"[bold red]❌ {rel_path} is out of date. Run 'uv run generate-usage-docs --fix' to update.[/bold red]"
            )
            diff_lines = list(
                difflib.unified_diff(
                    current_content.splitlines(),
                    new_content.splitlines(),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    lineterm="",
                )
            )
            if diff_lines:
                console.print("\n".join(diff_lines[:40]))
            return False
        console.print(f"[bold green]✓ {rel_path} is up to date.[/bold green]")
        return True

    # Fix / generate mode
    usage_file.write_text(new_content, encoding="utf-8")
    console.print(f"[bold green]✓ Updated {rel_path}[/bold green]")
    return True


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for generate-usage-docs.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 for success/up-to-date, 1 if out of date).

    Notes/Architectural Intent:
        Dispatches GenerateUsageDocsCommand across the governance bus and renders
        results via the configured GeneratorPresenterPort.
    """
    parser = argparse.ArgumentParser(
        description="Generate, verify, and fix USAGE.md documentation for Hexastack packages."
    )
    parser.add_argument(
        "-p",
        "--package",
        default=None,
        help="Target package to process (default: auto-detected based on git changes or all)",
    )
    parser.add_argument(
        "-A",
        "--affected",
        action="store_true",
        help="Detect and process only affected packages with CLI impact.",
    )
    parser.add_argument(
        "--check",
        "--verify",
        dest="verify",
        action="store_true",
        help="Verify whether USAGE.md files match in-memory generation (pre-commit quality gate).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Re-generate and format USAGE.md files directly on disk.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output presentation format (default: table).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Root path of repository (default: auto-detected).",
    )
    args = parser.parse_args(argv)

    from hexaqual.adapters.presenters.generators import (
        create_generator_presenter,
    )
    from hexaqual.domain.generators import GenerateUsageDocsCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    repo_root = args.root or get_repo_root()
    bus = create_governance_bus(repo_root=repo_root)
    presenter = create_generator_presenter(args.format)

    cmd = GenerateUsageDocsCommand(
        package=args.package,
        affected_only=args.affected or (args.verify and args.package is None),
        check_only=args.verify,
        fix=args.fix or (not args.verify),
    )
    report = bus.dispatch(cmd)
    code = presenter.present_usage_docs(report)
    if argv is None:
        sys.exit(code)
    return code


__all__ = [
    "build_tools_usage_markdown",
    "build_umbrella_usage_markdown",
    "main",
    "process_package_usage",
    "resolve_impacted_usage_targets",
]
