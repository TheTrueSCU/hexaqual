"""CQRS command handlers for architecture and documentation generators.

Notes/Architectural Intent:
    Orchestrates execution of pydeps dependency diagram generation, USAGE.md catalog
    updates, and pytest-archon boundary test scaffolding, returning immutable domain reports.
"""

from __future__ import annotations

import difflib
import shutil
import subprocess
import tomllib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from hexaqual.adapters.code_analysis.pydeps import (
    check_overview_diagram,
    check_package_diagram,
    generate_overview_diagram,
    generate_package_diagram,
)
from hexaqual.adapters.code_analysis.usage_docs import (
    extract_command_tree_bfs,
    extract_subcommands_from_help,
)
from hexaqual.adapters.workspace import (
    get_canonical_scripts,
    get_package_directories,
    get_package_directory,
    get_present_layers,
    get_repo_root,
    get_workspace_scripts,
    resolve_affected_packages,
)
from hexaqual.domain.generators import (
    ArchonReport,
    GenerateArchonTestsCommand,
    GeneratePydepsCommand,
    GenerateUsageDocsCommand,
    PydepsDiagramResult,
    PydepsReport,
    UsageDocsReport,
)


def _resolve_workspace_commands(root: Path) -> dict[str, list[str]]:
    """Resolve commands and their aliases from workspace pyproject.toml."""
    scripts = get_workspace_scripts(root)
    if not scripts:
        candidates = [
            root / "pyproject.toml",
            root / "packages" / "hexaqual" / "pyproject.toml",
        ]
        pyproject_path = next((c for c in candidates if c.is_file()), root / "pyproject.toml")
        if pyproject_path.is_file():
            try:
                data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
                scripts = data.get("project", {}).get("scripts", {})
            except Exception:
                pass

    commands_map = get_canonical_scripts(scripts)
    if not commands_map:
        name = root.name
        pyproj = root / "pyproject.toml"
        if pyproj.is_file():
            try:
                data = tomllib.loads(pyproj.read_text(encoding="utf-8"))
                name = data.get("project", {}).get("name", root.name)
            except Exception:
                pass
        commands_map = {name: []}
    return commands_map


def _append_single_command_tree(
    primary_cmd: str,
    aliases: list[str],
    root: Path,
    lines: list[str],
) -> None:
    """Append unrolled command tree for a single primary entrypoint."""
    alias_str = f" / `{aliases[0]}`" if aliases else ""
    alias_badge = f" (alias: `{'`, `'.join(aliases)}`)" if aliases else ""
    lines[0] = f"# Hexaqual Quality Suite & CLI Catalog (`{primary_cmd}`{alias_str})"

    tree = extract_command_tree_bfs([primary_cmd], cwd=root)
    root_help = tree.get((primary_cmd,), "")

    lines.extend(
        [
            "",
            f"## 🚀 Unified Root Entrypoint (`{primary_cmd}`{alias_badge})",
            "",
            "```text",
            root_help,
            "```",
            "",
            "---",
            "",
            "## 🛠️ Complete Subcommand Tree Reference",
            "",
        ]
    )

    subcommand_keys = [k for k in sorted(tree.keys()) if len(k) > 1]
    for key in subcommand_keys:
        cmd_str = " ".join(key)
        depth = len(key)
        heading = "#" * min(depth + 1, 5)
        lines.append(f"{heading} `{cmd_str}`\n")
        lines.append("```text")
        lines.append(tree[key])
        lines.append("```\n")


def _append_multi_command_tree(
    commands_map: dict[str, list[str]],
    root: Path,
    lines: list[str],
) -> None:
    """Append unrolled command trees for multiple canonical scripts."""
    lines.extend(
        [
            "",
            "## 🛠️ Complete Command & Subcommand Reference",
            "",
        ]
    )
    for cmd_name, aliases in sorted(commands_map.items()):
        alias_badge = f" (aliases: `{'`, `'.join(aliases)}`)" if aliases else ""
        tree = extract_command_tree_bfs([cmd_name], cwd=root)
        cmd_help = tree.get((cmd_name,), "")
        lines.append(f"### `{cmd_name}`{alias_badge}\n")
        lines.append("```text")
        lines.append(cmd_help)
        lines.append("```\n")

        subcommand_keys = [k for k in sorted(tree.keys()) if len(k) > 1]
        for key in subcommand_keys:
            cmd_str = " ".join(key)
            depth = len(key)
            heading = "#" * min(depth + 2, 5)
            lines.append(f"{heading} `{cmd_str}`\n")
            lines.append("```text")
            lines.append(tree[key])
            lines.append("```\n")


def build_tools_usage_markdown(root: Path) -> str:
    """Generate canonical USAGE.md by unrolling the complete command hierarchy via BFS."""
    commands_map = _resolve_workspace_commands(root)

    lines: list[str] = [
        "# Hexaqual Quality Suite & CLI Catalog",
        "",
        "> Canonical developer command reference and CLI catalog automatically generated from the complete command hierarchy.",
        "",
        "---",
        "",
        "## 🏛️ Dogfooding Hexagonal Architecture",
        "",
        "`hexaqual` is built strictly according to Hexagonal Architecture design principles:",
        "- **`domain/`**: Pure data contracts (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).",
        "- **`ports/`**: Clean interface contracts (`GitHubApiPort`, `GovernancePresenterPort`, `ToolRunnerPort`, `PyPiClientPort`).",
        "- **`adapters/`**: Pluggable presenters (`rich`, `json`, `plain`), subcommands, and runners.",
        "- **`cli/`**: Unified Typer CLI driving adapter (`hexaqual`).",
        "- **`infra/`**: Command dispatchers, handlers, and execution orchestration.",
        "- **`utils/`**: Workspace discovery, AST parsing, and package graph resolvers.",
        "",
        "---",
        "",
        "## ⚙️ Output Presentation Formats",
        "",
        "All inspection commands support `--format / -f`:",
        "- **`auto` (default)**: Automatically outputs interactive ANSI tables/panels when attached to a terminal TTY, and switches to clean, tab-delimited plain text (`TSV`) when standard output is piped into Unix filters (`grep`, `awk`, `cut`, `xargs`, etc.).",
        "- **`rich`**: Interactive Rich tables and color-coded status badges.",
        "- **`json`**: Structured JSON for automation, CI scripts, and AI agents.",
        "- **`plain`**: Machine-readable TSV stream.",
        "",
        "---",
    ]

    if len(commands_map) == 1:
        primary_cmd, aliases = next(iter(commands_map.items()))
        _append_single_command_tree(primary_cmd, aliases, root, lines)
    else:
        _append_multi_command_tree(commands_map, root, lines)

    return "\n".join(lines).strip() + "\n"


def build_umbrella_usage_markdown(root: Path) -> str:
    """Generate canonical USAGE.md for the umbrella hexastack package using BFS command tree traversal."""
    tree = extract_command_tree_bfs(["hexastack"], cwd=root)
    main_help = tree.get(("hexastack",), "")
    subcommands = extract_subcommands_from_help(main_help)

    lines: list[str] = [
        "# Hexastack CLI & Framework Usage Guide (`hexastack`)",
        "",
        "> Canonical reference guide and command catalog for the Hexastack Unified Developer CLI.",
        "",
        "---",
        "",
        "## 🚀 Unified Entrypoint (`hexastack`)",
        "",
        "```text",
        main_help,
        "```",
        "",
        "---",
        "",
        "## 🛠️ Subcommand Reference Catalog",
        "",
    ]

    for sub in subcommands:
        sub_help = tree.get(("hexastack", sub), "")
        lines.append(f"### `hexastack {sub}`\n")
        lines.append("```text")
        lines.append(sub_help)
        lines.append("```\n")

    return "\n".join(lines).strip() + "\n"


def resolve_usage_target_rel_path(target_key: str, root: Path) -> str:
    """Resolve relative file path for a usage documentation target.

    Args:
        target_key: Target key identifier (e.g. package name or root project name).
        root: Workspace root path.

    Returns:
        Relative file path string for USAGE.md.

    Notes/Architectural Intent:
        Dynamically cross-references discovered usage targets or packages directory
        without hardcoded literal maps or package names.
    """
    targets = discover_usage_targets(root)
    if target_key in targets:
        target_path = targets[target_key]
        try:
            return str(target_path.relative_to(root))
        except ValueError:
            return str(target_path)

    pkg_dir = root / "packages" / target_key
    if pkg_dir.is_dir():
        return f"packages/{target_key}/USAGE.md"

    return "USAGE.md"


def discover_usage_targets(root: Path) -> dict[str, Path]:
    """Discover all packages or root defining [project.scripts].

    Args:
        root: Workspace root directory.

    Returns:
        Mapping of target name -> Path to its USAGE.md destination.

    Notes/Architectural Intent:
        Dynamically checks root and packages/ directories for pyproject.toml files
        containing CLI scripts. Zero hardcoded package names.
    """
    targets: dict[str, Path] = {}

    root_pyproject = root / "pyproject.toml"
    if root_pyproject.is_file():
        try:
            data = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))
            if data.get("project", {}).get("scripts"):
                name = data.get("project", {}).get("name", root.name)
                targets[name] = root / "USAGE.md"
        except Exception:
            pass

    packages_dir = root / "packages"
    if packages_dir.is_dir():
        for pkg_dir in sorted(packages_dir.iterdir()):
            pyproj = pkg_dir / "pyproject.toml"
            if pyproj.is_file():
                try:
                    data = tomllib.loads(pyproj.read_text(encoding="utf-8"))
                    if data.get("project", {}).get("scripts"):
                        name = data.get("project", {}).get("name", pkg_dir.name)
                        targets[name] = pkg_dir / "USAGE.md"
                except Exception:
                    pass

    return targets


def _get_changed_files_for_git() -> list[str]:
    """Retrieve modified files from git staged/unstaged or HEAD commit."""
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        # Ignore git diff failure when outside git workspace
        return []


def resolve_impacted_usage_targets(root: Path) -> list[str]:
    """Resolve target names impacted by git diff changes.

    Args:
        root: Workspace root directory.

    Returns:
        List of target names to process.

    Notes/Architectural Intent:
        Dynamically cross-references changed files with discovered target directories.
    """
    targets = discover_usage_targets(root)
    if not (root / "packages").is_dir():
        return list(targets.keys())

    changed = _get_changed_files_for_git()
    if not changed:
        return list(targets.keys())

    affected = resolve_affected_packages(changed, root)
    if affected is None:
        return list(targets.keys())

    matched = [t for t in targets if t in affected or any(t.endswith(a) for a in affected)]
    return matched or list(targets.keys())


class GeneratePydepsHandler:
    """Handler executing pydeps architecture dependency diagram generation."""

    def __init__(self, root: Path | None = None, parallel: bool = True) -> None:
        """Initialize GeneratePydepsHandler with workspace root.

        Args:
            root: Root path of monorepo workspace.
            parallel: Whether to execute diagram generation concurrently.
        """
        self._root = root or get_repo_root()
        self._parallel = parallel

    def _check_single_package(self, pkg: Path) -> PydepsDiagramResult:
        """Verify a single package diagram."""
        ok, info = check_package_diagram(pkg, self._root)
        return PydepsDiagramResult(
            name=pkg.name,
            path=info,
            success=ok,
            is_stale=not ok,
            details="" if ok else "Diagram is stale or missing",
        )

    def _check_packages(self, packages: list[Path]) -> list[PydepsDiagramResult]:
        """Verify package diagrams sequentially or concurrently."""
        if not self._parallel:
            return [self._check_single_package(pkg) for pkg in packages]

        results: list[PydepsDiagramResult] = []
        with ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(check_package_diagram, pkg, self._root): pkg.name
                for pkg in packages
            }
            for future in futures:
                pkg_name = futures[future]
                ok, info = future.result()
                results.append(
                    PydepsDiagramResult(
                        name=pkg_name,
                        path=info,
                        success=ok,
                        is_stale=not ok,
                        details="" if ok else "Diagram is stale or missing",
                    )
                )
        return results

    def _generate_single_package(self, pkg: Path) -> PydepsDiagramResult:
        """Generate a single package diagram."""
        path = generate_package_diagram(pkg, self._root)
        return PydepsDiagramResult(
            name=pkg.name,
            path=path or "",
            success=bool(path),
            is_stale=False,
        )

    def _generate_packages(self, packages: list[Path]) -> list[PydepsDiagramResult]:
        """Generate package diagrams sequentially or concurrently."""
        if not self._parallel:
            return [self._generate_single_package(pkg) for pkg in packages]

        results: list[PydepsDiagramResult] = []
        with ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(generate_package_diagram, pkg, self._root): pkg.name
                for pkg in packages
            }
            for future in futures:
                pkg_name = futures[future]
                path = future.result()
                results.append(
                    PydepsDiagramResult(
                        name=pkg_name,
                        path=path or "",
                        success=bool(path),
                        is_stale=False,
                    )
                )
        return results

    def _handle_check(self, command: GeneratePydepsCommand, packages: list[Path]) -> PydepsReport:
        """Execute check mode for overview and package diagrams."""
        if shutil.which("dot") is None:
            return PydepsReport(
                results=(
                    PydepsDiagramResult(
                        name="Architecture Diagrams",
                        path="",
                        success=True,
                        is_stale=False,
                        details="Graphviz 'dot' not installed (check skipped)",
                    ),
                ),
                is_successful=True,
                is_check=True,
            )

        results: list[PydepsDiagramResult] = []
        if not command.packages:
            overview_ok, overview_info = check_overview_diagram(self._root)
            results.append(
                PydepsDiagramResult(
                    name="Monorepo Overview",
                    path=overview_info,
                    success=overview_ok,
                    is_stale=not overview_ok,
                    details="" if overview_ok else "Diagram is stale or missing",
                )
            )
        results.extend(self._check_packages(packages))
        all_ok = all(r.success for r in results) if results else True
        return PydepsReport(results=tuple(results), is_successful=all_ok, is_check=True)

    def _handle_generate(
        self, command: GeneratePydepsCommand, packages: list[Path]
    ) -> PydepsReport:
        """Execute generate mode for overview and package diagrams."""
        if shutil.which("dot") is None:
            return PydepsReport(
                results=(
                    PydepsDiagramResult(
                        name="Architecture Diagrams",
                        path="",
                        success=False,
                        is_stale=False,
                        details="Graphviz 'dot' not installed (generation aborted)",
                    ),
                ),
                is_successful=False,
                is_check=False,
            )

        results: list[PydepsDiagramResult] = []
        if not command.packages:
            overview_path = generate_overview_diagram(self._root)
            if overview_path:
                results.append(
                    PydepsDiagramResult(
                        name="Monorepo Overview",
                        path=overview_path,
                        success=True,
                    )
                )
        results.extend(self._generate_packages(packages))
        all_ok = all(r.success for r in results) if results else True
        return PydepsReport(results=tuple(results), is_successful=all_ok, is_check=False)

    def handle(self, command: GeneratePydepsCommand) -> PydepsReport:
        """Execute pydeps diagram generation or verification across targeted packages.

        Args:
            command: GeneratePydepsCommand specifying target packages and check mode.

        Returns:
            PydepsReport with results for each generated or verified SVG.

        Notes/Architectural Intent:
            Concurrently generates or validates individual package dependency diagrams using
            multiprocessing when parallel is True, or sequentially when False.
        """
        if command.packages:
            packages = [get_package_directory(p, self._root) for p in command.packages]
        else:
            packages = get_package_directories(self._root)

        if command.check_only:
            return self._handle_check(command, packages)
        return self._handle_generate(command, packages)


def _filter_target_map(
    all_targets: dict[str, Path],
    root: Path,
    package: str | None,
    affected_only: bool,
) -> dict[str, Path]:
    """Filter discovered usage targets based on package or impact criteria.

    Args:
        all_targets: Mapping of discovered target names to USAGE.md paths.
        root: Workspace repository root directory.
        package: Optional specific package name to filter for.
        affected_only: Whether to restrict to packages impacted by git diff.

    Returns:
        Filtered dictionary mapping target names to their USAGE.md file paths.

    Notes/Architectural Intent:
        Extracted from GenerateUsageDocsHandler to maintain strict cognitive
        complexity compliance under 25.
    """
    if package and package != "all":
        if package in all_targets:
            return {package: all_targets[package]}
        target_map = {
            k: v for k, v in all_targets.items() if k == package or v.parent.name == package
        }
        if target_map:
            return target_map
        pkg_dir = root / "packages" / package
        if pkg_dir.is_dir():
            return {package: pkg_dir / "USAGE.md"}
        return {}

    if affected_only:
        impacted = resolve_impacted_usage_targets(root)
        target_map = {k: all_targets[k] for k in impacted if k in all_targets}
        if target_map or (root / "packages").is_dir():
            return target_map
        return all_targets

    return all_targets


def _process_target_file(
    usage_file: Path,
    root: Path,
    check_only: bool,
    fix: bool,
) -> tuple[str, str, str | None]:
    """Process a single USAGE.md file for currency or updates.

    Args:
        usage_file: Target USAGE.md file path.
        root: Workspace repository root directory.
        check_only: Whether to only audit without modifying files.
        fix: Whether to write updated markdown to disk.

    Returns:
        Tuple of (status, relative_path, diff_content_if_any).
        Status is one of 'stale', 'up_to_date', or 'updated'.

    Notes/Architectural Intent:
        Extracted from GenerateUsageDocsHandler to isolate diff computation
        and file I/O operations from target orchestration.
    """
    pyproject_path = usage_file.parent / "pyproject.toml"
    if not pyproject_path.is_file():
        pyproject_path = root / "pyproject.toml"
    new_content = build_tools_usage_markdown(pyproject_path.parent)

    try:
        rel_path = str(usage_file.relative_to(root))
    except ValueError:
        rel_path = str(usage_file)

    if check_only and not fix:
        if not usage_file.is_file():
            return "stale", rel_path, f"File {rel_path} does not exist."

        current_content = usage_file.read_text(encoding="utf-8")
        if current_content.strip() != new_content.strip():
            diff_lines = list(
                difflib.unified_diff(
                    current_content.splitlines(),
                    new_content.splitlines(),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    lineterm="",
                )
            )
            return "stale", rel_path, "\n".join(diff_lines)
        return "up_to_date", rel_path, None

    usage_file.write_text(new_content, encoding="utf-8")
    return "updated", rel_path, None


class GenerateUsageDocsHandler:
    """Handler evaluating or updating USAGE.md catalog files."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize GenerateUsageDocsHandler with workspace root."""
        self._root = root or get_repo_root()

    def handle(self, command: GenerateUsageDocsCommand) -> UsageDocsReport:
        """Audit or regenerate USAGE.md documentation across discovered targets.

        Args:
            command: GenerateUsageDocsCommand specifying check or fix behavior.

        Returns:
            UsageDocsReport detailing updated, up-to-date, or stale files.

        Notes/Architectural Intent:
            Dynamically discovers all packages with scripts, groups by entrypoint
            to eliminate alias redundancy, and validates/generates USAGE.md.
        """
        all_targets = discover_usage_targets(self._root)
        target_map = _filter_target_map(
            all_targets, self._root, command.package, command.affected_only
        )
        if not target_map:
            target_map = {self._root.name: self._root / "USAGE.md"}

        up_to_date: list[str] = []
        updated: list[str] = []
        stale: list[str] = []
        diffs: list[tuple[str, str]] = []

        for usage_file in target_map.values():
            status, rel_path, diff = _process_target_file(
                usage_file, self._root, command.check_only, command.fix
            )
            if status == "stale":
                stale.append(rel_path)
                if diff:
                    diffs.append((rel_path, diff))
            elif status == "up_to_date":
                up_to_date.append(rel_path)
            else:
                updated.append(rel_path)

        return UsageDocsReport(
            up_to_date_files=tuple(up_to_date),
            updated_files=tuple(updated),
            stale_files=tuple(stale),
            diffs=tuple(diffs),
            is_valid=len(stale) == 0,
        )


class GenerateArchonTestsHandler:
    """Handler scaffolding pytest-archon hexagonal boundary tests."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize GenerateArchonTestsHandler with workspace root."""
        self._root = root or get_repo_root()

    def handle(self, command: GenerateArchonTestsCommand) -> ArchonReport:
        """Scaffold pytest-archon boundary tests across packages.

        Args:
            command: GenerateArchonTestsCommand with target packages and force flag.

        Returns:
            ArchonReport with list of generated and skipped test paths.

        Notes/Architectural Intent:
            Checks for standard hexagonal architectural layers (domain, ports, adapters,
            infra) before writing boundary assertions.
        """
        packages = (
            [get_package_directory(p, self._root) for p in command.packages]
            if command.packages
            else get_package_directories(self._root)
        )

        generated: list[str] = []
        skipped: list[str] = []

        for pkg_path in packages:
            pkg_name = pkg_path.name
            if not get_present_layers(pkg_path):
                skipped.append(pkg_name)
                continue

            test_lines = [
                f'"""Hexagonal architecture boundary tests for {pkg_name}."""',
                "",
                "from hexastack_core.testing import assert_clean_architecture",
                "",
                "",
                f"def test_{pkg_name.replace('-', '_')}_clean_architecture():",
                f'    """Assert {pkg_name} strictly complies with Hexagonal layer isolation."""',
                f'    assert_clean_architecture("{pkg_name.replace("-", "_")}")',
                "",
            ]
            arch_dir = pkg_path / "tests" / "architecture"
            arch_dir.mkdir(parents=True, exist_ok=True)
            target_file = arch_dir / "test_hexagonal_boundaries.py"
            if target_file.exists() and not command.force:
                skipped.append(pkg_name)
                continue

            target_file.write_text("\n".join(test_lines).strip() + "\n", encoding="utf-8")
            generated.append(str(target_file.relative_to(self._root)))

        return ArchonReport(
            generated_files=tuple(generated),
            skipped_files=tuple(skipped),
            is_successful=True,
        )


__all__ = [
    "build_tools_usage_markdown",
    "build_umbrella_usage_markdown",
    "discover_usage_targets",
    "GenerateArchonTestsHandler",
    "GeneratePydepsHandler",
    "GenerateUsageDocsHandler",
    "resolve_impacted_usage_targets",
    "resolve_usage_target_rel_path",
]
