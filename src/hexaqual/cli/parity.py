"""CLI subcommands for test parity and optional extras parity verification.

Notes/Architectural Intent:
    Driving adapter exposing test and extras subcommands to enforce 1:1 test
    symmetry and validate optional dependencies forwarding into umbrella packaging.
"""

from __future__ import annotations

import typer

__all__ = [
    "parity_app",
    "parity_architecture",
    "parity_extras",
    "parity_test",
]

parity_app = typer.Typer(
    name="parity",
    help="Audit test symmetry and optional extras parity.",
    no_args_is_help=True,
)


@parity_app.command("test")
def parity_test(
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
) -> None:
    """Verify 1:1 symmetry between src modules and unit tests.

    Args:
        format_type: Output presentation format.

    Raises:
        typer.Exit: If parity violations are found.

    Notes/Architectural Intent:
        Driving adapter verifying src/ and tests/unit/ parity and __init__.py presence.
    """
    from hexaqual.adapters.presenters.governance import create_governance_presenter
    from hexaqual.utils.test_parity import (
        check_src_to_test_symmetry,
        check_test_directories_inits,
    )
    from hexaqual.utils.workspace import get_repo_root

    root = get_repo_root()
    init_errors = check_test_directories_inits(root)
    symmetry_errors = check_src_to_test_symmetry(root)

    presenter = create_governance_presenter(format_type=format_type)
    exit_code = presenter.present_test_parity(init_errors, symmetry_errors)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@parity_app.command("extras")
def parity_extras(
    diagram: bool = typer.Option(False, "--diagram", help="Generate Mermaid dependency diagram."),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
) -> None:
    """Audit optional extras parity across workspace subpackages and umbrella.

    Args:
        diagram: Whether to generate Mermaid extras graph.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If extras parity violations are found.

    Notes/Architectural Intent:
        Driving adapter validating subpackage extras forwarding into umbrella packaging.
    """
    from hexaqual.adapters.presenters.dependency import create_dependency_presenter
    from hexaqual.domain.dependencies import AuditExtrasParityCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    root = get_repo_root()
    bus = create_governance_bus(repo_root=root)
    res = bus.dispatch(AuditExtrasParityCommand(repo_root=root, generate_diagram=diagram))
    presenter = create_dependency_presenter(format_type=format_type)
    exit_code = presenter.present_extras_parity(res)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@parity_app.command("architecture")
def parity_architecture(
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output format (table, json, markdown)."
    ),
) -> None:
    """Audit architecture tests and boundary test parity across packages.

    Args:
        format_type: Output presentation format.

    Raises:
        typer.Exit: If architecture parity violations are found.

    Notes/Architectural Intent:
        Driving adapter verifying tests/architecture/test_hexagonal_boundaries.py
        and test directory inits exist across all workspace packages.
    """
    from hexaqual.adapters.presenters.governance import create_governance_presenter
    from hexaqual.utils.test_parity import check_architecture_test_parity
    from hexaqual.utils.workspace import get_repo_root

    root = get_repo_root()
    errors = check_architecture_test_parity(root)

    presenter = create_governance_presenter(format_type=format_type)
    exit_code = presenter.present_architecture_parity(errors)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
