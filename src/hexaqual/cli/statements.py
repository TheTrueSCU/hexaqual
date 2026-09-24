"""CLI subcommands for __all__ export statements auditing and formatting.

Notes/Architectural Intent:
    Driving adapter exposing check and fix subcommands for sorting,
    deduplicating, and verifying __all__ declarations across Python source modules.
"""

from __future__ import annotations

import typer

__all__ = [
    "statements_app",
    "statements_check",
    "statements_fix",
]

statements_app = typer.Typer(
    name="statements",
    help="Audit and format __all__ statements.",
    no_args_is_help=True,
)


@statements_app.command("check")
def statements_check(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
    files: list[str] | None = typer.Argument(None, help="Target files or directories."),
) -> None:
    """Validate __all__ declarations across targeted files.

    Args:
        packages: Optional sequence of package names to inspect.
        format_type: Output presentation format.
        files: Optional explicit list of files or directories.

    Raises:
        typer.Exit: If validation errors are encountered.

    Notes/Architectural Intent:
        Driving adapter delegating to AST statement inspection and governance presenter.
    """
    from hexaqual.adapters.code_analysis.all_statements import check_file_all
    from hexaqual.adapters.presenters.governance import create_governance_presenter
    from hexaqual.infra.workspace import get_repo_root, resolve_target_python_files

    root = get_repo_root()
    py_files = resolve_target_python_files(files=files, packages=packages, repo_root=root)
    all_errors: list[str] = []
    for f in py_files:
        all_errors.extend(check_file_all(f))

    presenter = create_governance_presenter(format_type=format_type)
    exit_code = presenter.present_all_statements(all_errors)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@statements_app.command("fix")
def statements_fix(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
    files: list[str] | None = typer.Argument(None, help="Target files or directories."),
) -> None:
    """Format __all__ declarations in target Python files.

    Args:
        packages: Optional sequence of package names to inspect.
        format_type: Output presentation format.
        files: Optional explicit list of files or directories.

    Notes/Architectural Intent:
        Driving adapter sorting, deduplicating, and formatting __all__ statements.
    """
    from hexaqual.adapters.code_analysis.all_statements import fix_file_all
    from hexaqual.adapters.presenters.governance import create_governance_presenter
    from hexaqual.infra.workspace import get_repo_root, resolve_target_python_files

    root = get_repo_root()
    py_files = resolve_target_python_files(files=files, packages=packages, repo_root=root)
    formatted_count = sum(fix_file_all(f) for f in py_files)

    presenter = create_governance_presenter(format_type=format_type)
    presenter.present_all_statements([], modified_count=formatted_count)
