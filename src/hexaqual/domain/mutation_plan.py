"""LPT-balanced mutation testing matrix planner for workspaces and packages.

Notes/Architectural Intent:
    Uses only the Python standard library so CI planning steps can invoke
    ``python3 -m hexaqual.domain.mutation_plan`` before installing project
    dependencies. Implements Longest-Processing-Time-first (LPT) ordering for
    both workspace package matrices (``affected`` / ``all``) and single-package
    file-level ``--gremlin-targets`` slicing (``slices``).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

DEFAULT_NUM_SLICES = 12


def _changed_files(base_ref: str) -> list[str]:
    """Return paths changed relative to ``origin/<base_ref>`` or ``HEAD~1``."""
    candidates = [f"origin/{base_ref}...HEAD", "HEAD~1...HEAD"] if base_ref else ["HEAD~1...HEAD"]
    for diff_range in candidates:
        res = subprocess.run(
            ["git", "diff", "--name-only", diff_range],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    return []


def _package_line_count(pkg_dir: Path) -> int:
    """Count Python source lines under ``pkg_dir/src`` for LPT ordering."""
    src_dir = pkg_dir / "src"
    if not src_dir.is_dir():
        return 0
    return sum(
        len(path.read_text(encoding="utf-8").splitlines())
        for path in src_dir.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _resolve_package_names(
    dir_names: list[str],
    packages_root: Path,
) -> list[str]:
    """Resolve distribution names from ``pyproject.toml`` sorted largest-first."""
    sized: list[tuple[int, str]] = []
    for dir_name in sorted(dir_names):
        pkg_dir = packages_root / dir_name
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue
        meta = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        dist_name = str(meta.get("project", {}).get("name", dir_name))
        sized.append((_package_line_count(pkg_dir), dist_name))
    sized.sort(key=lambda item: (-item[0], item[1]))
    return [name for _lines, name in sized]


def discover_affected_packages(
    base_ref: str = "main",
    packages_root: Path = Path("packages"),
) -> list[str]:
    """Discover directly affected workspace packages ordered largest-first (LPT).

    Args:
        base_ref: Git base branch name (e.g. ``main``).
        packages_root: Root directory containing workspace packages.

    Returns:
        List of affected package distribution names in LPT order.
    """
    changed = _changed_files(base_ref)
    touched_dirs: set[str] = set()
    for rel_path in changed:
        parts = Path(rel_path).parts
        if (
            len(parts) >= 2
            and parts[0] == packages_root.name
            and (rel_path.endswith(".py") or parts[-1] == "pyproject.toml")
        ):
            touched_dirs.add(parts[1])
    return _resolve_package_names(list(touched_dirs), packages_root)


def discover_all_packages(packages_root: Path = Path("packages")) -> list[str]:
    """Discover all workspace packages ordered largest-first (LPT).

    Args:
        packages_root: Root directory containing workspace packages.

    Returns:
        List of all package distribution names in LPT order.
    """
    if not packages_root.is_dir():
        return []
    dirs = [p.name for p in packages_root.iterdir() if p.is_dir()]
    return _resolve_package_names(dirs, packages_root)


def build_file_slices(
    root: Path = Path("src"),
    num_slices: int = DEFAULT_NUM_SLICES,
) -> list[dict[str, str]]:
    """Partition Python source files under ``root`` into balanced LPT slices.

    Args:
        root: Package source directory to partition.
        num_slices: Maximum number of parallel matrix slices.

    Returns:
        List of ``{"name": ..., "targets": ...}`` dictionaries.
    """
    if not root.is_dir():
        return []
    files = [
        (len(path.read_text(encoding="utf-8").splitlines()), str(path))
        for path in sorted(root.rglob("*.py"))
        if path.name != "__init__.py" and "__pycache__" not in path.parts
    ]
    if not files:
        return []

    files.sort(key=lambda item: (-item[0], item[1]))
    bucket_count = min(max(num_slices, 1), len(files))
    buckets: list[tuple[int, list[str]]] = [(0, []) for _ in range(bucket_count)]

    for line_count, rel_path in files:
        min_idx = min(range(bucket_count), key=lambda idx: buckets[idx][0])
        cur_lines, cur_paths = buckets[min_idx]
        cur_paths.append(rel_path)
        buckets[min_idx] = (cur_lines + line_count, cur_paths)

    return [
        {"name": f"slice-{idx + 1:02d}", "targets": ",".join(sorted(paths))}
        for idx, (_lines, paths) in enumerate(buckets)
        if paths
    ]


def plan_mutation_matrix(
    mode: str = "affected",
    *,
    base_ref: str = "main",
    packages_root: Path = Path("packages"),
    root: Path = Path("src"),
    num_slices: int = DEFAULT_NUM_SLICES,
) -> tuple[dict[str, object], bool]:
    """Build a GitHub Actions matrix payload for mutation testing.

    Args:
        mode: Planning mode (``affected``, ``all``, or ``slices``).
        base_ref: Git base branch for ``affected`` mode.
        packages_root: Workspace packages directory for ``affected`` / ``all``.
        root: Source directory for ``slices`` mode.
        num_slices: Maximum number of slices for ``slices`` mode.

    Returns:
        Tuple of ``(matrix_dict, has_affected)``.

    Raises:
        ValueError: If ``mode`` is not one of ``affected``, ``all``, ``slices``.
    """
    if mode == "affected":
        packages = discover_affected_packages(base_ref=base_ref, packages_root=packages_root)
        return {"package": packages}, bool(packages)
    if mode == "all":
        packages = discover_all_packages(packages_root=packages_root)
        return {"package": packages}, bool(packages)
    if mode == "slices":
        slices = build_file_slices(root=root, num_slices=num_slices)
        return {"include": slices}, bool(slices)
    msg = f"Unsupported mutation plan mode: {mode!r}"
    raise ValueError(msg)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint writing ``matrix`` and ``has_affected`` to ``$GITHUB_OUTPUT``."""
    parser = argparse.ArgumentParser(description="Plan LPT-balanced mutation matrix")
    parser.add_argument("--mode", default="affected", choices=("affected", "all", "slices"))
    parser.add_argument("--base-ref", default=os.environ.get("GITHUB_BASE_REF", "main"))
    parser.add_argument("--packages-root", default="packages")
    parser.add_argument("--root", default="src")
    parser.add_argument("--slices", type=int, default=DEFAULT_NUM_SLICES)
    args = parser.parse_args(argv)

    matrix_obj, has_affected = plan_mutation_matrix(
        args.mode,
        base_ref=args.base_ref,
        packages_root=Path(args.packages_root),
        root=Path(args.root),
        num_slices=args.slices,
    )
    matrix_json = json.dumps(matrix_obj)
    has_flag = "true" if has_affected else "false"
    output_lines = [f"matrix={matrix_json}", f"has_affected={has_flag}"]

    output_path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(output_lines) + "\n")
    else:
        sys.stdout.write("\n".join(output_lines) + "\n")
    return 0


__all__ = [
    "build_file_slices",
    "DEFAULT_NUM_SLICES",
    "discover_affected_packages",
    "discover_all_packages",
    "main",
    "plan_mutation_matrix",
]


if __name__ == "__main__":
    raise SystemExit(main())
