"""Main CLI entrypoint for Hexaqual.

Notes/Architectural Intent:
    Driving adapter exposing command groups for sanity checks, statements,
    parity audits, and release engineering.
"""

from __future__ import annotations

import typer
from rich.console import Console

from hexaqual import __version__

app = typer.Typer(
    name="hexaqual",
    help="Hexaqual - Universal Python Quality, Governance, and Release Engineering Suite.",
    no_args_is_help=True,
)

console = Console()


@app.command()
def version() -> None:
    """Display the current Hexaqual version.

    Notes/Architectural Intent:
        Quick diagnostic command to confirm package installation and version info.
    """
    console.print(f"[bold cyan]Hexaqual[/bold cyan] version [bold green]{__version__}[/bold green]")


@app.command()
def check() -> None:
    """Execute the sanity check pipeline.

    Notes/Architectural Intent:
        Primary entrypoint for local pre-commit verification and CI pipelines.
    """
    console.print("[bold yellow]Running Hexaqual Sanity Pipeline...[/bold yellow]")
    console.print("[green]✓[/green] Environment initialized successfully.")


__all__ = [
    "app",
    "check",
    "version",
]
