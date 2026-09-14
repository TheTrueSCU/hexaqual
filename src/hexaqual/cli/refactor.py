"""CLI subcommands for AST code refactoring and function/method alphabetization.

Notes/Architectural Intent:
    Driving adapter exposing AST transformation operations including LibCST
    deterministic symbol alphabetization and Rope refactoring actions across packages.
"""

from __future__ import annotations

from pathlib import Path

import typer

__all__ = [
    "refactor_alphabetize",
    "refactor_app",
    "refactor_extract",
    "refactor_move",
    "refactor_rename",
    "refactor_run",
]

refactor_app = typer.Typer(
    name="refactor",
    help="AST symbol alphabetization and Python code refactoring.",
    no_args_is_help=True,
)


@refactor_app.command("alphabetize")
def refactor_alphabetize(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    all_packages: bool = typer.Option(False, "-a", "--all", help="Format across all packages."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview reordering without modifying disk."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
    files: list[str] | None = typer.Argument(None, help="Specific files or directories to format."),
) -> None:
    """Sort functions and class methods alphabetically using LibCST.

    Args:
        packages: Optional sequence of target package names.
        all_packages: Whether to format all workspace packages.
        dry_run: Preview reordering without modifying disk.
        format_type: Output presentation format.
        files: Optional sequence of files or directories to format.

    Raises:
        typer.Exit: If alphabetization fails or detects errors.

    Notes/Architectural Intent:
        Dispatches AlphabetizeCodeCommand across the governance bus.
    """
    from hexaqual.adapters.presenters.refactoring import create_refactoring_presenter
    from hexaqual.domain.refactoring import AlphabetizeCodeCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import (
        get_package_directories,
        get_package_directory,
        get_repo_root,
    )

    root = get_repo_root()
    target_paths: list[Path] = []
    if files:
        target_paths.extend(Path(f) for f in files)
    elif packages:
        target_paths.extend(get_package_directory(p, root) for p in packages)
    elif all_packages:
        target_paths.extend(get_package_directories(root))
    else:
        target_paths.append(root)

    bus = create_governance_bus(repo_root=root)
    presenter = create_refactoring_presenter(format_type)
    cmd = AlphabetizeCodeCommand(targets=tuple(target_paths), dry_run=dry_run)
    report = bus.dispatch(cmd)
    exit_code = presenter.present_alphabetize(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@refactor_app.command("rename")
def refactor_rename(
    file: Path = typer.Option(
        ..., "--file", "-f", help="Target python file containing the symbol."
    ),
    line: int = typer.Option(..., "--line", "-l", help="1-based line number of symbol."),
    col: int = typer.Option(..., "--col", "-c", help="1-based column offset of symbol."),
    new_name: str = typer.Option(..., "--new-name", "-n", help="New identifier name."),
    root: Path | None = typer.Option(None, "--root", "-r", help="Project root directory."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview rename without saving."),
) -> None:
    """Rename a symbol project-wide using Rope.

    Args:
        file: Target python file.
        line: 1-based line number.
        col: 1-based column offset.
        new_name: New symbol name.
        root: Optional root directory.
        dry_run: Preview only.

    Raises:
        typer.Exit: If refactoring fails.

    Notes/Architectural Intent:
        Executes AST symbol renaming via Rope project engine.
    """
    import argparse

    from hexaqual.commands.rope import handle_rename
    from hexaqual.utils.workspace import ensure_tool_installed, get_repo_root

    ensure_tool_installed("rope", extra_name="rope")
    proj_root = root or get_repo_root()
    args = argparse.Namespace(
        file=str(file),
        line=line,
        col=col,
        new_name=new_name,
        root=str(proj_root),
        dry_run=dry_run,
    )
    try:
        handle_rename(args)
    except Exception as exc:
        typer.echo(f"Rename failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@refactor_app.command("extract")
def refactor_extract(
    file: Path = typer.Option(..., "--file", "-f", help="Target python file."),
    start_line: int = typer.Option(..., "--start-line", "-s", help="1-based start line."),
    end_line: int = typer.Option(..., "--end-line", "-e", help="1-based end line."),
    extracted_name: str = typer.Option(
        ..., "--name", "-n", help="Name for the extracted function/method."
    ),
    root: Path | None = typer.Option(None, "--root", "-r", help="Project root directory."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview extraction without saving."),
) -> None:
    """Extract code block into a new function or method using Rope.

    Args:
        file: Target python file.
        start_line: 1-based start line.
        end_line: 1-based end line.
        extracted_name: Name for the extracted function/method.
        root: Optional root directory.
        dry_run: Preview only.

    Raises:
        typer.Exit: If extraction fails.

    Notes/Architectural Intent:
        Executes method extraction via Rope AST refactoring.
    """
    import argparse

    from hexaqual.commands.rope import handle_extract_method
    from hexaqual.utils.workspace import ensure_tool_installed, get_repo_root

    ensure_tool_installed("rope", extra_name="rope")
    proj_root = root or get_repo_root()
    args = argparse.Namespace(
        file=str(file),
        start_line=start_line,
        end_line=end_line,
        name=extracted_name,
        root=str(proj_root),
        dry_run=dry_run,
    )
    try:
        handle_extract_method(args)
    except Exception as exc:
        typer.echo(f"Extract failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@refactor_app.command("move")
def refactor_move(
    source_file: Path = typer.Option(..., "--source-file", "-s", help="Source python file."),
    dest_file: Path = typer.Option(..., "--dest-file", "-d", help="Destination python file."),
    line: int = typer.Option(..., "--line", "-l", help="1-based line number of symbol to move."),
    col: int = typer.Option(..., "--col", "-c", help="1-based column offset of symbol."),
    root: Path | None = typer.Option(None, "--root", "-r", help="Project root directory."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview move without saving."),
) -> None:
    """Move a symbol or class to another module project-wide using Rope.

    Args:
        source_file: Source python file.
        dest_file: Destination python file.
        line: 1-based line number.
        col: 1-based column offset.
        root: Optional root directory.
        dry_run: Preview only.

    Raises:
        typer.Exit: If move fails.

    Notes/Architectural Intent:
        Executes symbol relocation across module boundaries via Rope.
    """
    import argparse

    from hexaqual.commands.rope import handle_move_symbol
    from hexaqual.utils.workspace import ensure_tool_installed, get_repo_root

    ensure_tool_installed("rope", extra_name="rope")
    proj_root = root or get_repo_root()
    args = argparse.Namespace(
        source_file=str(source_file),
        dest_file=str(dest_file),
        line=line,
        col=col,
        root=str(proj_root),
        dry_run=dry_run,
    )
    try:
        handle_move_symbol(args)
    except Exception as exc:
        typer.echo(f"Move failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@refactor_app.command(
    "run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def refactor_run(
    ctx: typer.Context,
) -> None:
    """Run interactive or advanced Rope refactoring operations.

    Args:
        ctx: Typer context capturing extra positional and option arguments.

    Raises:
        typer.Exit: If refactoring fails.

    Notes/Architectural Intent:
        Passes CLI arguments directly to the Rope refactoring command dispatcher.
    """
    import sys

    from hexaqual.commands.rope import run_main

    orig_argv = sys.argv
    try:
        sys.argv = ["hexaqual refactor run", *ctx.args]
        exit_code = run_main() or 0
        if exit_code != 0:
            raise typer.Exit(code=exit_code)
    finally:
        sys.argv = orig_argv
