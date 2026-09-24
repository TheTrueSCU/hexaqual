"""CLI Driving Adapter for Scoped Sanity Check Runner.

Notes/Architectural Intent:
    Acts strictly as a driving adapter: parses CLI arguments, builds domain
    commands, dispatches them through the CommandBusPort, and forwards reports
    to the GovernancePresenterPort.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from hexaqual.adapters.workspace import (
    get_example_directory,
    get_package_directories,
    get_package_directory,
    get_repo_root,
    is_multipackage_workspace,
)
from hexaqual.domain.governance import (
    SanityTarget,
)

__all__ = [
    "resolve_targets",
    "SanityTarget",
]


def _create_package_target(name: str, pkg_dir: Path) -> SanityTarget:
    """Construct SanityTarget for a package directory."""
    src_dir = pkg_dir / "src"
    test_dir = pkg_dir / "tests"
    return SanityTarget(
        name=name,
        kind="package",
        path=pkg_dir,
        src_paths=(src_dir,) if src_dir.is_dir() else (pkg_dir,),
        test_paths=(test_dir,) if test_dir.is_dir() else (),
    )


def _create_example_target(name: str, ex_dir: Path) -> SanityTarget:
    """Construct SanityTarget for an example directory."""
    src_dir = ex_dir / "src"
    test_dir = ex_dir / "tests"
    return SanityTarget(
        name=name,
        kind="example",
        path=ex_dir,
        src_paths=(src_dir,) if src_dir.is_dir() else (ex_dir,),
        test_paths=(test_dir,) if test_dir.is_dir() else (),
    )


def _detect_git_targets(repo_root: Path) -> list[SanityTarget]:
    """Inspect git status for modified packages and examples."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return []

    touched_pkgs: set[str] = set()
    touched_examples: set[str] = set()

    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        rel_path = line[3:].strip()
        parts = Path(rel_path).parts
        if len(parts) >= 2 and parts[0] == "packages":
            touched_pkgs.add(parts[1])
        elif len(parts) >= 2 and parts[0] == "examples":
            touched_examples.add(parts[1])

    targets: list[SanityTarget] = []
    for pkg in sorted(touched_pkgs):
        try:
            pkg_dir = get_package_directory(pkg, repo_root)
            if pkg_dir.is_dir():
                targets.append(_create_package_target(pkg, pkg_dir))
        except RuntimeError:
            continue

    for ex in sorted(touched_examples):
        try:
            ex_dir = get_example_directory(ex, repo_root)
            if ex_dir.is_dir():
                targets.append(_create_example_target(ex, ex_dir))
        except RuntimeError:
            continue

    return targets


def _resolve_package_targets(packages: list[str] | None, repo_root: Path) -> list[SanityTarget]:
    """Resolve target packages from CLI package arguments.

    Args:
        packages: List of package names or 'all'.
        repo_root: Root path of the repository.

    Returns:
        List of SanityTarget objects for packages.
    """
    if not packages:
        return []
    targets: list[SanityTarget] = []
    for pkg in packages:
        if pkg == "all":
            for p in get_package_directories(repo_root):
                targets.append(_create_package_target(p.name, p))
        else:
            pkg_dir = get_package_directory(pkg, repo_root)
            targets.append(_create_package_target(pkg, pkg_dir))
    return targets


def _resolve_example_targets(examples: list[str] | None, repo_root: Path) -> list[SanityTarget]:
    """Resolve example projects from CLI arguments.

    Args:
        examples: List of example names.
        repo_root: Root path of the repository.

    Returns:
        List of SanityTarget objects for examples.
    """
    if not examples:
        return []
    return [_create_example_target(ex, get_example_directory(ex, repo_root)) for ex in examples]


def _resolve_file_targets(files: list[str] | None, repo_root: Path) -> list[SanityTarget]:
    """Resolve individual file targets from CLI arguments.

    Args:
        files: List of file paths.
        repo_root: Root path of the repository.

    Returns:
        List of SanityTarget objects for files.
    """
    if not files:
        return []
    targets: list[SanityTarget] = []
    for f in files:
        file_p = Path(f) if Path(f).is_absolute() else (repo_root / f)
        if file_p.exists():
            targets.append(
                SanityTarget(
                    name=file_p.name,
                    kind="file",
                    path=file_p,
                    src_paths=(file_p,),
                    test_paths=(),
                )
            )
    return targets


def _resolve_fallback_targets(repo_root: Path) -> list[SanityTarget]:
    """Resolve fallback targets via git status or whole-workspace default.

    Args:
        repo_root: Root path of the repository.

    Returns:
        List of SanityTarget objects.
    """
    git_targets = _detect_git_targets(repo_root)
    if git_targets:
        return git_targets
    return [_create_package_target(p.name, p) for p in get_package_directories(repo_root)]


def resolve_targets(
    args: Any = None,
    repo_root: Path | None = None,
    packages: list[str] | None = None,
    examples: list[str] | None = None,
    files: list[str] | None = None,
    all_targets: bool = False,
) -> list[SanityTarget]:
    """Resolve target list based on CLI arguments and workspace layout.

    Args:
        args: Optional legacy parsed command-line arguments.
        repo_root: Root path of the repository.
        packages: Optional sequence of package names.
        examples: Optional sequence of example project names.
        files: Optional sequence of explicit files.
        all_targets: Whether to target all packages unconditionally.

    Returns:
        List of SanityTarget objects to audit.

    Notes/Architectural Intent:
        Resolves explicit package/example/file requests first. If in a multi-package
        workspace, -p filters packages. If in a singular package repository, defaults
        to the root package. If an examples directory exists, -e adds examples.
    """
    root = repo_root or get_repo_root()

    if args is not None:
        packages = getattr(args, "packages", None)
        examples = getattr(args, "examples", None)
        files = getattr(args, "files", None)
        all_targets = getattr(args, "all_targets", False)

    targets: list[SanityTarget] = []

    if packages:
        targets.extend(_resolve_package_targets(packages, root))

    if examples:
        targets.extend(_resolve_example_targets(examples, root))

    if files:
        targets.extend(_resolve_file_targets(files, root))

    if all_targets:
        if is_multipackage_workspace(root):
            for p in get_package_directories(root):
                targets.append(_create_package_target(p.name, p))
        else:
            targets.append(_create_package_target(root.name, root))

    if not targets:
        if is_multipackage_workspace(root):
            targets.extend(_resolve_fallback_targets(root))
        else:
            targets.append(_create_package_target(root.name, root))

    return targets
