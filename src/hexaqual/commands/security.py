"""GitHub PR Security and Review Comments Inspector command powered by Typer."""

from __future__ import annotations

from typing import Annotated

import typer

from hexaqual.adapters.presenters.security import present_security_comments
from hexaqual.domain.github import InspectSecurityCommentsCommand, OutputFormat
from hexaqual.infra.bootstrap import create_governance_bus

app = typer.Typer(
    help="Inspect security and review comments on a GitHub PR.",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def security(
    pr_number: Annotated[
        int,
        typer.Argument(
            help="Pull request number.",
        ),
    ],
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format: auto (detects pipes), rich (interactive tables), json (structured), plain (TSV).",
        ),
    ] = OutputFormat.AUTO,
) -> None:
    """Fetch and display review comments and security findings for a PR."""
    try:
        bus = create_governance_bus()
        report = bus.dispatch(InspectSecurityCommentsCommand(pr_number=pr_number))

        present_security_comments(report.threads, pr_number, output_format=output_format)
    except Exception as exc:
        typer.secho(f"Error querying PR comments: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for gh-security command."""
    try:
        app(args=argv, standalone_mode=False)
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)


__all__ = ["app", "main", "security"]
