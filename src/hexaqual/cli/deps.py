"""CLI subcommands for dependency auditing, architecture diagrams, and import boundaries.

Notes/Architectural Intent:
    Driving adapter exposing commands for auditing workspace dependencies with deptry,
    generating pydeps architecture graphs, and verifying hexagonal contracts via import-linter.
"""

from __future__ import annotations

from pathlib import Path

import typer

__all__ = [
    "deps_app",
    "deps_audit",
    "deps_deptry",
    "deps_linter",
    "deps_linter_generate",
    "deps_pydeps",
]

deps_app = typer.Typer(
    name="deps",
    help="Audit dependencies, generate import diagrams, and check architectural boundaries.",
    no_args_is_help=True,
)


@deps_app.command("audit")
def deps_audit(
    diagrams: bool = typer.Option(
        False, "--diagrams", help="Regenerate all Pydeps SVG import graphs and Mermaid diagrams."
    ),
    deptry_only: bool = typer.Option(
        False, "--deptry-only", help="Only run deptry source import audits."
    ),
    extras_only: bool = typer.Option(
        False, "--extras-only", help="Only run optional extras parity checks."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output representation format (table, json, markdown)."
    ),
) -> None:
    """Execute unified audit across dependencies, optional extras, and tools.

    Args:
        diagrams: Whether to regenerate Pydeps SVGs and Mermaid diagrams.
        deptry_only: Whether to restrict execution to deptry source import audits.
        extras_only: Whether to restrict execution to extras parity validation.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If dependency or extras auditing detects violations.

    Notes/Architectural Intent:
        Dispatches RunUnifiedDepsAuditCommand across the governance bus.
    """
    from hexaqual.adapters.presenters.dependency import create_dependency_presenter
    from hexaqual.domain.dependencies import RunUnifiedDepsAuditCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import get_repo_root

    repo_root = get_repo_root()
    bus = create_governance_bus()
    presenter = create_dependency_presenter(format_type)

    cmd = RunUnifiedDepsAuditCommand(
        repo_root=repo_root,
        check_deptry=not extras_only,
        check_extras=not deptry_only,
        check_tools=True,
        generate_diagrams=diagrams,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_unified_deps_audit(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@deps_app.command("pydeps")
def deps_pydeps(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
) -> None:
    """Generate architecture dependency diagrams using pydeps.

    Args:
        packages: Optional sequence of packages to graph.
        format_type: Output presentation format.

    Raises:
        typer.Exit: If diagram generation encounters errors.

    Notes/Architectural Intent:
        Ensures pydeps availability and dispatches GeneratePydepsCommand.
    """
    from hexaqual.adapters.presenters.generators import create_generator_presenter
    from hexaqual.domain.generators import GeneratePydepsCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import ensure_tool_installed

    ensure_tool_installed("pydeps", cli_command="pydeps", extra_name="diagrams")

    bus = create_governance_bus()
    presenter = create_generator_presenter(format_type)

    cmd = GeneratePydepsCommand(
        packages=tuple(packages) if packages else (),
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_pydeps(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@deps_app.command("linter")
def deps_linter(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
    all_packages: bool = typer.Option(
        False, "-a", "--all", help="Run across all packages unconditionally."
    ),
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
    files: list[str] | None = typer.Argument(None, help="Optional changed files list."),
) -> None:
    """Evaluate hexagonal architecture contract boundaries using import-linter.

    Args:
        packages: Optional sequence of package names to check.
        all_packages: Whether to verify all workspace packages.
        format_type: Output presentation format.
        files: Optional sequence of file paths to determine affected packages.

    Raises:
        typer.Exit: If import boundary contracts are broken.

    Notes/Architectural Intent:
        Enforces clean hexagonal dependencies between domain, ports, adapters, and infra.
    """
    from hexaqual.adapters.presenters.dependency import create_dependency_presenter
    from hexaqual.domain.dependencies import RunImportLinterCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import (
        ensure_tool_installed,
        get_package_directories,
        get_package_directory,
        get_packages_directory,
        get_repo_root,
    )

    ensure_tool_installed("importlinter", cli_command="lint-imports", extra_name="governance")

    root = get_repo_root()
    packages_dir = get_packages_directory(root)
    all_pkgs = get_package_directories(root)

    if packages:
        target_dirs = tuple(get_package_directory(p, root) for p in packages)
    elif all_packages or not files:
        target_dirs = tuple(p for p in all_pkgs if (p / "pyproject.toml").is_file())
    else:
        matched: list[Path] = []
        for file_str in files:
            try:
                rel = Path(file_str).relative_to(packages_dir)
                pkg_dir = packages_dir / rel.parts[0]
                if (pkg_dir / "pyproject.toml").is_file() and pkg_dir not in matched:
                    matched.append(pkg_dir)
            except ValueError:
                continue
        target_dirs = tuple(matched)

    bus = create_governance_bus()
    presenter = create_dependency_presenter(format_type)

    cmd = RunImportLinterCommand(
        repo_root=root,
        packages=target_dirs,
        all_packages=all_packages,
    )
    report = bus.dispatch(cmd)
    exit_code = presenter.present_import_linter(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@deps_app.command("linter-generate")
def deps_linter_generate(
    packages: list[str] | None = typer.Option(None, "-p", "--package", help="Target package(s)."),
) -> None:
    """Generate default hexagonal [tool.importlinter] contracts in pyproject.toml files.

    Args:
        packages: Optional sequence of packages for which to generate contracts.

    Notes/Architectural Intent:
        Generates standard forbidden-contract configurations forbidding adapters from
        importing infra, ports from importing adapters/infra, and domain from importing any layer.
    """
    from hexaqual.domain.dependencies import GenerateImportLinterConfigCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import (
        get_package_directories,
        get_package_directory,
        get_repo_root,
    )

    root = get_repo_root()
    if packages:
        target_dirs = tuple(get_package_directory(p, root) for p in packages)
    else:
        target_dirs = tuple(get_package_directories(root))

    bus = create_governance_bus()
    cmd = GenerateImportLinterConfigCommand(
        repo_root=root,
        packages=target_dirs,
    )
    bus.dispatch(cmd)


@deps_app.command("deptry")
def deps_deptry(
    format_type: str = typer.Option(
        "table", "-f", "--format", help="Output presentation format (table, json, markdown)."
    ),
) -> None:
    """Run deptry dependency analysis across workspace packages.

    Args:
        format_type: Output presentation format.

    Raises:
        typer.Exit: If unused or missing dependencies are detected.

    Notes/Architectural Intent:
        Driving adapter dispatching RunDeptryAuditCommand across all workspace packages.
    """
    from hexaqual.adapters.presenters.dependency import create_dependency_presenter
    from hexaqual.domain.dependencies import RunDeptryAuditCommand
    from hexaqual.infra.bootstrap import create_governance_bus
    from hexaqual.utils.workspace import ensure_tool_installed, get_repo_root

    ensure_tool_installed("deptry", cli_command="deptry", extra_name="governance")

    root = get_repo_root()
    bus = create_governance_bus(repo_root=root)
    presenter = create_dependency_presenter(format_type)

    cmd = RunDeptryAuditCommand(repo_root=root)
    report = bus.dispatch(cmd)
    exit_code = presenter.present_deptry_audit(report)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
