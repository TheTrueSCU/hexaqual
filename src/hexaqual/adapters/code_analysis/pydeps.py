"""Programmatic architecture dependency diagram generation utilities using pydeps.

Notes/Architectural Intent:
    Pure generation logic extracted to utils to decouple CLI presentation
    from internal dependency auditor adapters and runner pipelines.
"""

from __future__ import annotations

import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pydeps.pydeps import pydeps

from hexaqual.adapters.workspace import (
    ensure_tool_installed,
    get_package_directories,
    get_packages_directory,
)

__all__ = [
    "check_all_diagrams",
    "check_overview_diagram",
    "check_package_diagram",
    "generate_all_diagrams",
    "generate_overview_diagram",
    "generate_package_diagram",
]

_PYDEPS_ASSET_DIR = Path("docs") / "assets" / "pydeps"


def _output_dir(root: Path, create: bool = False) -> Path:
    """Return the absolute path to the pydeps asset directory.

    Args:
        root: Workspace repository root path.
        create: Whether to create the directory on disk if missing.

    Returns:
        Absolute Path to pydeps output directory.
    """
    out = root / _PYDEPS_ASSET_DIR
    if create:
        out.mkdir(parents=True, exist_ok=True)
    return out


def _get_overview_svg_path(root: Path) -> Path:
    """Resolve overview SVG diagram path, respecting existing naming conventions.

    Args:
        root: Repository root path.

    Returns:
        Path to the overview SVG asset.
    """
    out = _output_dir(root)
    candidates = [
        out / "hexastack_packages.svg",
        out / f"{root.name}_packages.svg",
        out / f"{root.name.replace('-', '_')}_packages.svg",
        out / "packages.svg",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return out / "hexastack_packages.svg"


def _get_package_entry_point(pkg_path: Path) -> Path | None:
    """Locate the Python package source entry point directory.

    Args:
        pkg_path: Path to package directory.

    Returns:
        Path to source directory or None if not located.
    """
    pkg_name = pkg_path.name
    candidates = [
        pkg_path / "src" / pkg_name,
        pkg_path / "src" / pkg_name.replace("-", "_"),
    ]
    for c in candidates:
        if c.is_dir():
            return c
    src_dir = pkg_path / "src"
    if src_dir.is_dir():
        subdirs = [p for p in src_dir.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))]
        if len(subdirs) == 1:
            return subdirs[0]
    return None


def _get_package_svg_path(pkg_path: Path, root: Path) -> Path:
    """Resolve destination SVG path for a package diagram.

    Args:
        pkg_path: Path to package directory.
        root: Repository root path.

    Returns:
        Path to destination SVG file.
    """
    out = _output_dir(root)
    pkg_name = pkg_path.name
    normalized_name = pkg_name.replace("-", "_")
    if (out / f"{normalized_name}.svg").is_file():
        return out / f"{normalized_name}.svg"
    return out / f"{pkg_name}.svg"


def generate_package_diagram(pkg_path: Path, root: Path) -> str | None:
    """Generate a dependency SVG for a single package.

    Args:
        pkg_path: Path to package directory.
        root: Repository root path.

    Returns:
        Relative path string of generated SVG, or None if skipped/errored.

    Notes/Architectural Intent:
        Invokes pydeps with standard formatting flags to create a standalone
        package dependency diagram.
    """
    _output_dir(root, create=True)
    svg_path = _get_package_svg_path(pkg_path, root)
    entry_point = _get_package_entry_point(pkg_path)

    if not entry_point or shutil.which("dot") is None:
        return None

    try:
        pydeps(
            fname=str(entry_point),
            format="svg",
            output=str(svg_path),
            show=False,
            no_show=True,
            cluster=True,
            max_bacon=2,
            rankdir="TB",
            include_missing=False,
        )
        return str(svg_path.relative_to(root))
    except Exception:
        return None


def check_package_diagram(pkg_path: Path, root: Path) -> tuple[bool, str]:
    """Verify if a package architecture diagram SVG is up to date.

    Args:
        pkg_path: Path to package directory.
        root: Repository root path.

    Returns:
        Tuple of (is_up_to_date, relative_path_or_reason).

    Notes/Architectural Intent:
        Generates a fresh diagram in a temporary location and performs a byte-for-byte
        comparison against the existing SVG asset to ensure zero drift.
    """
    svg_path = _get_package_svg_path(pkg_path, root)
    entry_point = _get_package_entry_point(pkg_path)

    if not entry_point:
        return True, f"No source directory for {pkg_path.name}"

    if shutil.which("dot") is None:
        return True, f"Graphviz 'dot' not installed (check skipped for {pkg_path.name})"

    if not svg_path.is_file():
        return False, f"{svg_path.relative_to(root)} does not exist"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_svg = Path(tmpdir) / svg_path.name
            pydeps(
                fname=str(entry_point),
                format="svg",
                output=str(tmp_svg),
                show=False,
                no_show=True,
                cluster=True,
                max_bacon=2,
                rankdir="TB",
                include_missing=False,
            )
            if not tmp_svg.is_file():
                return False, f"Failed to generate comparison diagram for {pkg_path.name}"

            if svg_path.read_bytes() == tmp_svg.read_bytes():
                return True, str(svg_path.relative_to(root))
            return False, str(svg_path.relative_to(root))
    except Exception as exc:
        return False, f"Error verifying diagram for {pkg_path.name}: {exc}"


def generate_overview_diagram(root: Path) -> str | None:
    """Generate the monorepo-wide overview diagram.

    Args:
        root: Repository root path.

    Returns:
        Relative path string of generated SVG, or None if skipped/errored.

    Notes/Architectural Intent:
        Invokes pydeps on the packages directory to produce the monorepo overview
        architecture diagram.
    """
    _output_dir(root, create=True)
    svg_path = _get_overview_svg_path(root)
    packages_dir = get_packages_directory(root)

    if shutil.which("dot") is None:
        return None

    try:
        pydeps(
            fname=str(packages_dir),
            format="svg",
            output=str(svg_path),
            show=False,
            no_show=True,
            cluster=True,
            max_bacon=1,
            rankdir="TB",
            include_missing=False,
        )
        return str(svg_path.relative_to(root))
    except Exception:
        return None


def check_overview_diagram(root: Path) -> tuple[bool, str]:
    """Verify if the monorepo-wide overview diagram SVG is up to date.

    Args:
        root: Repository root path.

    Returns:
        Tuple of (is_up_to_date, relative_path_or_reason).

    Notes/Architectural Intent:
        Validates monorepo package graph SVG against a newly generated
        temporary diagram to catch added, deleted, or re-wired package dependencies.
    """
    svg_path = _get_overview_svg_path(root)
    packages_dir = get_packages_directory(root)

    if not packages_dir.is_dir():
        return True, "No packages directory found"

    if shutil.which("dot") is None:
        return True, "Graphviz 'dot' not installed (check skipped)"

    if not svg_path.is_file():
        return False, f"{svg_path.relative_to(root)} does not exist"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_svg = Path(tmpdir) / svg_path.name
            pydeps(
                fname=str(packages_dir),
                format="svg",
                output=str(tmp_svg),
                show=False,
                no_show=True,
                cluster=True,
                max_bacon=1,
                rankdir="TB",
                include_missing=False,
            )
            if not tmp_svg.is_file():
                return False, "Failed to generate comparison overview diagram"

            if svg_path.read_bytes() == tmp_svg.read_bytes():
                return True, str(svg_path.relative_to(root))
            return False, str(svg_path.relative_to(root))
    except Exception as exc:
        return False, f"Error verifying overview diagram: {exc}"


def generate_all_diagrams(
    root: Path,
    packages: list[Path] | None = None,
    parallel: bool = True,
) -> list[tuple[str, str]]:
    """Programmatically generate overview and all package SVGs.

    Args:
        root: Repository root path.
        packages: Optional list of specific package directories.
        parallel: Whether to run generation concurrently.

    Returns:
        List of tuples (package_or_overview_name, relative_svg_path).

    Notes/Architectural Intent:
        Coordinates parallel generation across package diagrams and the overview
        diagram.
    """
    ensure_tool_installed("pydeps", cli_command="pydeps", extra_name="diagrams")
    if shutil.which("dot") is None:
        return []
    target_pkgs = packages if packages is not None else get_package_directories(root)
    results: list[tuple[str, str]] = []

    if packages is None:
        overview_path = generate_overview_diagram(root)
        if overview_path:
            results.append(("Monorepo Overview", overview_path))

    if not parallel:
        for pkg in target_pkgs:
            path = generate_package_diagram(pkg, root)
            if path:
                results.append((pkg.name, path))
    else:
        with ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(generate_package_diagram, pkg, root): pkg.name
                for pkg in target_pkgs
            }
            for future in futures:
                pkg_name = futures[future]
                path = future.result()
                if path:
                    results.append((pkg_name, path))

    return results


def check_all_diagrams(
    root: Path,
    packages: list[Path] | None = None,
    parallel: bool = True,
) -> list[tuple[str, str, bool]]:
    """Programmatically verify overview and package SVGs for freshness.

    Args:
        root: Repository root path.
        packages: Optional list of specific package directories.
        parallel: Whether to run checks concurrently.

    Returns:
        List of tuples (name, relative_path_or_reason, is_up_to_date).

    Notes/Architectural Intent:
        Coordinates parallel verification across package diagrams and the overview
        diagram, providing diagnostic reporting for CI and sanity check pipelines.
    """
    ensure_tool_installed("pydeps", cli_command="pydeps", extra_name="diagrams")
    if shutil.which("dot") is None:
        return [("Architecture Diagrams", "Graphviz 'dot' not installed (check skipped)", True)]
    target_pkgs = packages if packages is not None else get_package_directories(root)
    results: list[tuple[str, str, bool]] = []

    if packages is None:
        overview_ok, overview_info = check_overview_diagram(root)
        results.append(("Monorepo Overview", overview_info, overview_ok))

    if not parallel:
        for pkg in target_pkgs:
            ok, info = check_package_diagram(pkg, root)
            results.append((pkg.name, info, ok))
    else:
        with ProcessPoolExecutor() as executor:
            futures = {
                executor.submit(check_package_diagram, pkg, root): pkg.name for pkg in target_pkgs
            }
            for future in futures:
                pkg_name = futures[future]
                ok, info = future.result()
                results.append((pkg_name, info, ok))

    return results
