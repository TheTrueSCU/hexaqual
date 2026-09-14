"""GitHub PR check auditor command powered by Typer and Presenters."""

from __future__ import annotations

from typing import Annotated

import typer

from hexaqual.adapters.presenters.github import create_github_presenter
from hexaqual.domain.github import InspectChecksCommand, OutputFormat
from hexaqual.infra.bootstrap import create_governance_bus

app = typer.Typer(
    help="Inspect GitHub CI and status checks.",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def checks(
    ref_or_pr: Annotated[
        str,
        typer.Argument(
            help="Pull request number or commit ref/branch name.",
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
    """Inspect CI status checks for a given PR number or Git ref."""
    try:
        bus = create_governance_bus()
        report = bus.dispatch(InspectChecksCommand(ref_or_pr=ref_or_pr))

        presenter = create_github_presenter(output_format=output_format.value)
        exit_code = presenter.present_checks(report)
        if exit_code != 0:
            raise typer.Exit(code=exit_code)
    except typer.Exit:
        raise
    except Exception as exc:
        typer.secho(f"Error querying GitHub checks: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for gh-checks."""
    try:
        app(args=argv, standalone_mode=False)
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)


__all__ = ["app", "checks", "main"]
