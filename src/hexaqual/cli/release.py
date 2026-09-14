"""CLI subcommands for distribution build, PyPI check, and smart publishing.

Notes/Architectural Intent:
    Driving adapter exposing package building, verification against PyPI registry,
    reproducible build audits, and dependency-ordered smart publishing.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

__all__ = [
    "release_app",
    "release_build",
    "release_check",
    "release_publish",
    "release_reproducible",
]

release_app = typer.Typer(
    name="release",
    help="Distribution package building, validation, and PyPI publishing.",
    no_args_is_help=True,
)

console = Console()


@release_app.command("build")
def release_build(
    dist_dir: Path | None = typer.Option(
        None, "--dist-dir", help="Output directory (default: dist/)."
    ),
    format_type: str = typer.Option("rich", "-f", "--format", help="Output format."),
) -> None:
    """Build distribution packages (sdist and wheel).

    Args:
        dist_dir: Destination directory.
        format_type: Output format.

    Raises:
        typer.Exit: If build fails.

    Notes/Architectural Intent:
        Builds reproducible distribution packages.
    """
    from hexaqual.commands.pypi import build_all_packages

    exit_code = build_all_packages(out_dir=dist_dir, format_name=format_type)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@release_app.command("check")
def release_check(
    package: str | None = typer.Option(
        None, "-p", "--package", help="Target package name (default: all)."
    ),
    format_type: str = typer.Option("rich", "-f", "--format", help="Output format."),
) -> None:
    """Validate package build distributions and PyPI release versions.

    Args:
        package: Optional specific package name to check.
        format_type: Output format.

    Raises:
        typer.Exit: If validation fails.

    Notes/Architectural Intent:
        Queries PyPI to verify current version status.
    """
    from hexaqual.adapters.presenters.pypi import create_pypi_presenter
    from hexaqual.adapters.runners.pypi_runner import SubprocessPyPiRunnerAdapter
    from hexaqual.commands.pypi import _DelegatingPyPiClient
    from hexaqual.domain.pypi import CheckPyPiReleasesCommand
    from hexaqual.infra.bootstrap import create_governance_bus

    client = _DelegatingPyPiClient(SubprocessPyPiRunnerAdapter())
    bus = create_governance_bus(pypi_client=client)
    report = bus.dispatch(CheckPyPiReleasesCommand(package_name=package))
    presenter = create_pypi_presenter(format_type, console=console)
    presenter.present_check(report)


@release_app.command("publish")
def release_publish(
    dist_dir: Path | None = typer.Option(None, "--dist-dir", help="Directory containing packages."),
    build: bool = typer.Option(True, "--build/--no-build", help="Build before publishing."),
    token: str | None = typer.Option(None, "--token", help="PyPI upload token."),
    delay: float = typer.Option(2.0, "--delay", help="Delay between uploads."),
    force: bool = typer.Option(False, "--force", help="Force upload."),
    format_type: str = typer.Option("rich", "-f", "--format", help="Output format."),
) -> None:
    """Build and publish packages to PyPI, skipping existing releases.

    Args:
        dist_dir: Directory containing packages.
        build: Whether to build packages before upload.
        token: PyPI upload token.
        delay: Delay between package uploads.
        force: Force upload even if exists.
        format_type: Output format.

    Raises:
        typer.Exit: If publishing fails.

    Notes/Architectural Intent:
        Smart publisher skipping published versions and respecting rate limits.
    """
    from hexaqual.commands.pypi import build_all_packages, publish_packages

    if build:
        build_rc = build_all_packages(out_dir=dist_dir, format_name=format_type)
        if build_rc != 0:
            console.print("[bold red]Failed to build packages. Aborting publish.[/bold red]")
            raise typer.Exit(code=build_rc)

    exit_code = publish_packages(
        dist_dir=dist_dir,
        token=token,
        delay=delay,
        skip_existing=not force,
        format_name=format_type,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@release_app.command("reproducible")
def release_reproducible(
    format_type: str = typer.Option("rich", "-f", "--format", help="Output format."),
) -> None:
    """Verify bit-for-bit reproducible wheel package builds.

    Args:
        format_type: Output format.

    Raises:
        typer.Exit: If reproducible build check fails.

    Notes/Architectural Intent:
        Builds twice in clean isolated environments and compares SHA256 hashes.
    """
    from hexaqual.commands.pypi import verify_reproducible_builds

    exit_code = verify_reproducible_builds(format_name=format_type)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
