"""Main CLI entrypoint for Hexaqual.

Notes/Architectural Intent:
    Unified driving adapter assembling modular Typer sub-applications
    and root commands for sanity checks, __all__ statements, test and extras
    parity, test execution, mutation testing, release engineering, GitHub operations,
    and documentation.
"""

from __future__ import annotations

import typer
from rich.console import Console

from hexaqual import __version__
from hexaqual.cli.check import check, register_check_commands, sanity
from hexaqual.cli.deps import (
    deps_app,
    deps_audit,
    deps_linter,
    deps_linter_generate,
    deps_pydeps,
)
from hexaqual.cli.docs import docs_app, docs_usage
from hexaqual.cli.gh import (
    gh_app,
    gh_checks,
    gh_code_scanning,
    gh_pr,
    gh_repo,
    gh_security,
)
from hexaqual.cli.mutate import mutate_app, mutate_inspect, mutate_run
from hexaqual.cli.parity import parity_app, parity_extras, parity_test
from hexaqual.cli.release import (
    release_app,
    release_build,
    release_check,
    release_publish,
    release_reproducible,
)
from hexaqual.cli.statements import statements_app, statements_check, statements_fix
from hexaqual.cli.test import (
    test_app,
    test_boundary,
    test_impact,
    test_redundancy,
    test_run,
)

__all__ = [
    "app",
    "check",
    "deps_app",
    "deps_audit",
    "deps_linter",
    "deps_linter_generate",
    "deps_pydeps",
    "docs_app",
    "docs_usage",
    "gh_app",
    "gh_checks",
    "gh_code_scanning",
    "gh_pr",
    "gh_repo",
    "gh_security",
    "mutate_app",
    "mutate_inspect",
    "mutate_run",
    "parity_app",
    "parity_extras",
    "parity_test",
    "release_app",
    "release_build",
    "release_check",
    "release_publish",
    "release_reproducible",
    "sanity",
    "statements_app",
    "statements_check",
    "statements_fix",
    "test_app",
    "test_boundary",
    "test_impact",
    "test_redundancy",
    "test_run",
    "version",
]

app = typer.Typer(
    name="hexaqual",
    help="Hexaqual - Universal Python Quality, Governance, and Release Engineering Suite.",
    no_args_is_help=True,
)

console = Console()

# Register root check/sanity commands
register_check_commands(app)

# Mount modular sub-applications
app.add_typer(statements_app)
app.add_typer(parity_app)
app.add_typer(test_app)
app.add_typer(deps_app)
app.add_typer(mutate_app)
app.add_typer(release_app)
app.add_typer(gh_app)
app.add_typer(docs_app)


@app.command()
def version() -> None:
    """Display the current Hexaqual version.

    Notes/Architectural Intent:
        Quick diagnostic command to confirm package installation and version info.
    """
    console.print(f"[bold cyan]Hexaqual[/bold cyan] version [bold green]{__version__}[/bold green]")
