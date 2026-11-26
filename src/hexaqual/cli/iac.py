"""CLI subcommands for auto-detecting Infrastructure-as-Code quality and security gates.

Notes/Architectural Intent:
    Driving adapter exposing ``hexaqual iac check``, ``hexaqual iac discover``, and
    ``hexaqual iac fmt`` over the governance CQRS bus and multi-format IaC presenters.
"""

from __future__ import annotations

from pathlib import Path

import typer

from hexaqual.cli.options import (
    append_step_summary,
    format_option,
    resolve_format,
    summary_option,
)
from hexaqual.domain.iac import (
    DiscoverIacAssetsCommand,
    IacToolName,
    RunIacAuditCommand,
)

__all__ = [
    "iac_app",
    "iac_check",
    "iac_discover",
    "iac_fmt",
]

iac_app = typer.Typer(
    name="iac",
    help="Auto-detecting IaC linting, formatting, and misconfiguration scanning.",
    no_args_is_help=True,
)


def _parse_tool_names(raw_values: list[str] | None, param_hint: str) -> tuple[IacToolName, ...]:
    """Parse repeatable or comma-separated tool name CLI flags into ``IacToolName`` values."""
    if not raw_values:
        return ()
    parsed: list[IacToolName] = []
    for raw in raw_values:
        for token in raw.split(","):
            cleaned = token.strip().lower()
            if not cleaned:
                continue
            try:
                parsed.append(IacToolName(cleaned))
            except ValueError as exc:
                valid = ", ".join(tool.value for tool in IacToolName)
                raise typer.BadParameter(
                    f"Unknown IaC tool '{cleaned}'. Valid tools: {valid}.",
                    param_hint=param_hint,
                ) from exc
    return tuple(parsed)


def _resolve_root_dir(root: Path | None) -> Path:
    """Resolve explicit ``--root`` directory or auto-detect repository root."""
    if root is not None:
        return root.resolve()
    from hexaqual.adapters.workspace import get_repo_root

    return get_repo_root()


@iac_app.command("check")
def iac_check(
    paths: list[Path] | None = typer.Argument(
        None,
        help="Optional IaC files or directories to scan (defaults to entire repository).",
    ),
    tools: list[str] | None = typer.Option(
        None,
        "-t",
        "--tool",
        help="Specific IaC tool(s) to execute (repeatable or comma-separated).",
    ),
    skip: list[str] | None = typer.Option(
        None,
        "--skip",
        help="Specific IaC tool(s) to skip (repeatable or comma-separated).",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Auto-format OpenTofu/Terraform files before checking.",
    ),
    init_tofu: bool = typer.Option(
        False,
        "--init",
        help="Run 'tofu init -backend=false' for uninitialized OpenTofu/Terraform modules.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Fail instead of skipping when a matching IaC tool binary is missing or module is uninitialized.",
    ),
    severity: str = typer.Option(
        "HIGH,CRITICAL",
        "--severity",
        help="Comma-separated Trivy severity threshold (e.g. 'HIGH,CRITICAL').",
    ),
    shellcheck_severity: str = typer.Option(
        "warning",
        "--shellcheck-severity",
        help="Minimum ShellCheck severity ('error', 'warning', 'info', 'style').",
    ),
    hadolint_threshold: str = typer.Option(
        "warning",
        "--hadolint-threshold",
        help="Hadolint --failure-threshold level ('error', 'warning', 'info', 'style', 'ignore').",
    ),
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, rich, json, markdown, auto).",
    ),
    step_summary: bool = summary_option(
        help_text="Append Markdown IaC audit summary to $GITHUB_STEP_SUMMARY.",
    ),
    root: Path | None = typer.Option(
        None,
        "--root",
        help="Target repository root directory (defaults to auto-detected repo root).",
    ),
) -> None:
    """Execute auto-detecting IaC formatting, linting, and misconfiguration scanning gates.

    Args:
        paths: Optional file or directory paths narrowing discovery scope.
        tools: Optional explicit subset of IaC tools to execute.
        skip: Optional IaC tools to exclude.
        fix: Whether to auto-format OpenTofu/Terraform files.
        init_tofu: Whether to initialize uninitialized OpenTofu modules offline.
        strict: Fail instead of skip when required binaries or initialization are missing.
        severity: Trivy severity filter string.
        shellcheck_severity: Minimum ShellCheck severity floor.
        hadolint_threshold: Hadolint failure threshold level.
        format_type: Presentation format (``table``, ``rich``, ``json``, ``markdown``, ``auto``).
        step_summary: Whether to append Markdown report to ``$GITHUB_STEP_SUMMARY``.
        root: Optional target repository root directory.

    Raises:
        typer.BadParameter: If an unknown tool name or unsupported format is provided.
        typer.Exit: If any IaC gate fails.

    Notes/Architectural Intent:
        Gracefully skips when no IaC assets are discovered so universal hooks and
        CI templates can enable IaC checks unconditionally on Python repositories.
    """
    from hexaqual.adapters.presenters.iac import (
        MarkdownIacPresenterAdapter,
        create_iac_presenter,
    )
    from hexaqual.infra.bootstrap import create_governance_bus

    parsed_tools = _parse_tool_names(tools, "--tool")
    parsed_skips = _parse_tool_names(skip, "--skip")
    repo_root = _resolve_root_dir(root)
    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")

    try:
        presenter = create_iac_presenter(format_type=resolved_fmt)
    except ValueError as err:
        raise typer.BadParameter(str(err), param_hint="--format") from err

    bus = create_governance_bus(repo_root=repo_root)
    cmd = RunIacAuditCommand(
        repo_root=repo_root,
        paths=tuple(paths) if paths else (),
        tools=parsed_tools,
        skip_tools=parsed_skips,
        fix=fix,
        init_tofu=init_tofu,
        strict=strict,
        severity=severity,
        shellcheck_severity=shellcheck_severity,
        hadolint_threshold=hadolint_threshold,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_iac_audit(report)

    if step_summary:
        md_text = MarkdownIacPresenterAdapter().render_iac_audit_markdown(report)
        append_step_summary(md_text)

    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@iac_app.command("discover")
def iac_discover(
    paths: list[Path] | None = typer.Argument(
        None,
        help="Optional files or directories to scan (defaults to entire repository).",
    ),
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, rich, json, markdown, auto).",
    ),
    root: Path | None = typer.Option(
        None,
        "--root",
        help="Target repository root directory (defaults to auto-detected repo root).",
    ),
) -> None:
    """Discover IaC artifacts and inspect external analyzer binary readiness.

    Args:
        paths: Optional files or directories narrowing discovery scope.
        format_type: Presentation format (``table``, ``rich``, ``json``, ``markdown``, ``auto``).
        root: Optional target repository root directory.

    Raises:
        typer.BadParameter: If an unsupported output format is requested.

    Notes/Architectural Intent:
        Provides deterministic asset discovery and PATH visibility before running
        automated CI or pre-commit gates.
    """
    from hexaqual.adapters.presenters.iac import create_iac_presenter
    from hexaqual.infra.bootstrap import create_governance_bus

    repo_root = _resolve_root_dir(root)
    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    try:
        presenter = create_iac_presenter(format_type=resolved_fmt)
    except ValueError as err:
        raise typer.BadParameter(str(err), param_hint="--format") from err

    bus = create_governance_bus(repo_root=repo_root)
    report = bus.dispatch(
        DiscoverIacAssetsCommand(
            repo_root=repo_root,
            paths=tuple(paths) if paths else (),
        )
    )
    presenter.present_iac_inventory(report)


@iac_app.command("fmt")
def iac_fmt(
    paths: list[Path] | None = typer.Argument(
        None,
        help="Optional OpenTofu/Terraform files or directories to format.",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Check HCL formatting without modifying files (default behavior).",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Automatically format OpenTofu/Terraform files in-place.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Fail instead of skipping when 'tofu'/'terraform' is not installed.",
    ),
    format_type: str = format_option(
        default="table",
        help_text="Output presentation format (table, rich, json, markdown, auto).",
    ),
    root: Path | None = typer.Option(
        None,
        "--root",
        help="Target repository root directory (defaults to auto-detected repo root).",
    ),
) -> None:
    """Check or apply canonical HCL formatting via ``tofu fmt``.

    Args:
        paths: Optional OpenTofu/Terraform paths to inspect or format.
        check: Explicitly enforce check-only mode without modifying files.
        fix: Automatically format OpenTofu/Terraform files in-place.
        strict: Fail instead of skipping when ``tofu``/``terraform`` is missing.
        format_type: Presentation format (``table``, ``rich``, ``json``, ``markdown``, ``auto``).
        root: Optional target repository root directory.

    Raises:
        typer.BadParameter: If mutually exclusive flags or an invalid format are passed.
        typer.Exit: If unformatted HCL files remain or strict check fails.

    Notes/Architectural Intent:
        Focused shorthand for OpenTofu/Terraform formatting parity in local workflows.
    """
    from hexaqual.adapters.presenters.iac import create_iac_presenter
    from hexaqual.infra.bootstrap import create_governance_bus

    if check and fix:
        raise typer.BadParameter(
            "--check and --fix cannot be used together.",
            param_hint="--fix",
        )

    repo_root = _resolve_root_dir(root)
    resolved_fmt = resolve_format(format_type, default_tty="table", default_pipe="json")
    try:
        presenter = create_iac_presenter(format_type=resolved_fmt)
    except ValueError as err:
        raise typer.BadParameter(str(err), param_hint="--format") from err

    bus = create_governance_bus(repo_root=repo_root)
    report = bus.dispatch(
        RunIacAuditCommand(
            repo_root=repo_root,
            paths=tuple(paths) if paths else (),
            tools=(IacToolName.TOFU_FMT,),
            fix=fix,
            strict=strict,
        )
    )
    exit_code = presenter.present_iac_audit(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
