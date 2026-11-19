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


def _lpt_pack_files(
    files: list[tuple[int, str]],
    num_slices: int,
    *,
    prefix: str = "slice",
    extra: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Pack ``(line_count, rel_path)`` pairs into balanced LPT slices."""
    if not files:
        return []
    ordered = sorted(files, key=lambda item: (-item[0], item[1]))
    bucket_count = min(max(num_slices, 1), len(ordered))
    buckets: list[tuple[int, list[str]]] = [(0, []) for _ in range(bucket_count)]

    for line_count, rel_path in ordered:
        min_idx = min(range(bucket_count), key=lambda idx: buckets[idx][0])
        cur_lines, cur_paths = buckets[min_idx]
        cur_paths.append(rel_path)
        buckets[min_idx] = (cur_lines + line_count, cur_paths)

    result: list[dict[str, str]] = []
    for idx, (_lines, paths) in enumerate(buckets):
        if not paths:
            continue
        entry = {"name": f"{prefix}-{idx + 1:02d}", "targets": ",".join(sorted(paths))}
        if extra:
            entry.update(extra)
        result.append(entry)
    return result


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
    return _lpt_pack_files(files, num_slices)


def build_changed_slices(
    base_ref: str = "main",
    packages_root: Path = Path("packages"),
    root: Path = Path("src"),
    num_slices: int = DEFAULT_NUM_SLICES,
) -> list[dict[str, str]]:
    """Partition changed Python source files into LPT-balanced matrix slices.

    Args:
        base_ref: Git base branch name (e.g. ``main``).
        packages_root: Workspace packages directory for monorepo layouts.
        root: Source directory for single-package layouts.
        num_slices: Maximum number of parallel slices per package.

    Returns:
        List of slice dictionaries containing ``name``, ``targets``, and
        (for workspaces) ``package``.
    """
    changed = _changed_files(base_ref)
    if not changed:
        return []

    if packages_root.is_dir():
        by_pkg: dict[str, list[tuple[int, str]]] = {}
        for rel_path in changed:
            path = Path(rel_path)
            parts = path.parts
            if (
                len(parts) >= 4
                and parts[0] == packages_root.name
                and parts[2] == "src"
                and rel_path.endswith(".py")
                and path.name != "__init__.py"
                and path.is_file()
            ):
                pkg_rel = str(Path(*parts[2:]))
                lines = len(path.read_text(encoding="utf-8").splitlines())
                by_pkg.setdefault(parts[1], []).append((lines, pkg_rel))

        slices: list[dict[str, str]] = []
        for dir_name in _resolve_package_names(list(by_pkg.keys()), packages_root):
            # Map dist_name back to dir_name if needed
            matched_dir = next(
                (
                    d
                    for d in by_pkg
                    if (
                        (packages_root / d / "pyproject.toml").is_file()
                        and tomllib.loads(
                            (packages_root / d / "pyproject.toml").read_text(encoding="utf-8")
                        )
                        .get("project", {})
                        .get("name", d)
                        == dir_name
                    )
                    or d == dir_name
                ),
                dir_name,
            )
            slices.extend(
                _lpt_pack_files(
                    by_pkg.get(matched_dir, []),
                    num_slices,
                    prefix=f"{dir_name}-slice",
                    extra={"package": dir_name},
                )
            )
        return slices

    single_files = [
        (len(Path(rel).read_text(encoding="utf-8").splitlines()), rel)
        for rel in changed
        if rel.endswith(".py")
        and Path(rel).name != "__init__.py"
        and Path(rel).is_file()
        and Path(rel).is_relative_to(root)
    ]
    return _lpt_pack_files(single_files, num_slices)


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
    if mode == "changed-slices":
        slices = build_changed_slices(
            base_ref=base_ref,
            packages_root=packages_root,
            root=root,
            num_slices=num_slices,
        )
        return {"include": slices}, bool(slices)
    msg = f"Unsupported mutation plan mode: {mode!r}"
    raise ValueError(msg)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint writing ``matrix`` and ``has_affected`` to ``$GITHUB_OUTPUT``."""
    parser = argparse.ArgumentParser(description="Plan LPT-balanced mutation matrix")
    parser.add_argument(
        "--mode",
        default="affected",
        choices=("affected", "all", "slices", "changed-slices"),
    )
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
    "build_changed_slices",
    "build_file_slices",
    "DEFAULT_NUM_SLICES",
    "discover_affected_packages",
    "discover_all_packages",
    "main",
    "plan_mutation_matrix",
]


if __name__ == "__main__":
    raise SystemExit(main())
