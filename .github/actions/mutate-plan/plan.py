#!/usr/bin/env python3
"""Standalone LPT-balanced mutation testing matrix planner for GitHub Actions.

Notes/Architectural Intent:
    Uses only the Python standard library so CI planning steps can invoke
    ``python3 "${{ github.action_path }}/plan.py"`` before installing project
    dependencies. Weights files and packages by AST mutable-site density,
    isolates oversized files into solo slices, dynamically expands slices under
    a per-slice weight cap, and emits slices heaviest-first (LPT dispatch order).
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
import subprocess
import sys
import tomllib
from pathlib import Path

DEFAULT_NUM_SLICES = 12
DEFAULT_MAX_SLICE_WEIGHT = 450

_HEAVY_MUTABLE_NODES = (ast.BinOp, ast.Compare, ast.BoolOp, ast.AugAssign)
_LIGHT_MUTABLE_NODES = (ast.UnaryOp, ast.If, ast.IfExp, ast.While, ast.Return)
_PER_FILE_OVERHEAD = 5


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """Return object IDs of string ``ast.Constant`` nodes used as docstrings."""
    doc_ids: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(
                node,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            )
            and node.body
        ):
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                doc_ids.add(id(first.value))
    return doc_ids


def estimate_ast_mutation_weight(source: str) -> int:
    """Estimate mutation workload weight of Python source code via AST analysis.

    Args:
        source: Python source text to analyze.

    Returns:
        Positive integer estimating relative gremlin generation workload.

    Notes/Architectural Intent:
        Counts operator, comparison, boolean, branch, return, and numeric/bool
        constant AST nodes while ignoring docstrings, comments, and blank lines.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return max(1, len(source.splitlines()))

    doc_ids = _docstring_node_ids(tree)
    weight = _PER_FILE_OVERHEAD
    for node in ast.walk(tree):
        if id(node) in doc_ids:
            continue
        if isinstance(node, _HEAVY_MUTABLE_NODES):
            weight += 3
        elif isinstance(node, _LIGHT_MUTABLE_NODES) or (
            isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool))
        ):
            weight += 1
    return weight


def _file_mutation_weight(path: Path) -> int:
    """Compute AST mutation weight for a Python source file on disk."""
    try:
        return estimate_ast_mutation_weight(path.read_text(encoding="utf-8"))
    except OSError:
        return _PER_FILE_OVERHEAD


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


def _package_mutation_weight(pkg_dir: Path) -> int:
    """Sum AST mutation weights under ``pkg_dir/src`` for LPT package ordering."""
    src_dir = pkg_dir / "src"
    if not src_dir.is_dir():
        return 0
    return sum(
        _file_mutation_weight(path)
        for path in src_dir.rglob("*.py")
        if path.name != "__init__.py" and "__pycache__" not in path.parts
    )


def _resolve_package_names(
    dir_names: list[str],
    packages_root: Path,
) -> list[str]:
    """Resolve distribution names from ``pyproject.toml`` sorted heaviest-first."""
    sized: list[tuple[int, str]] = []
    for dir_name in sorted(dir_names):
        pkg_dir = packages_root / dir_name
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue
        meta = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        dist_name = str(meta.get("project", {}).get("name", dir_name))
        sized.append((_package_mutation_weight(pkg_dir), dist_name))
    sized.sort(key=lambda item: (-item[0], item[1]))
    return [name for _weight, name in sized]


def discover_affected_packages(
    base_ref: str = "main",
    packages_root: Path = Path("packages"),
) -> list[str]:
    """Discover directly affected workspace packages ordered heaviest-first (LPT).

    Args:
        base_ref: Git base branch name (e.g. ``main``).
        packages_root: Root directory containing workspace packages.

    Returns:
        List of affected package distribution names in LPT order.

    Notes/Architectural Intent:
        Prioritizes heaviest packages first so long-running mutation jobs start
        immediately on bounded GitHub Actions / Hexaqueue worker pools.
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
    """Discover all workspace packages ordered heaviest-first (LPT).

    Args:
        packages_root: Root directory containing workspace packages.

    Returns:
        List of all package distribution names in LPT order.

    Notes/Architectural Intent:
        Used for scheduled weekly full-workspace mutation sweeps.
    """
    if not packages_root.is_dir():
        return []
    dirs = [p.name for p in packages_root.iterdir() if p.is_dir()]
    return _resolve_package_names(dirs, packages_root)


def _pack_buckets(
    items: list[tuple[int, str]],
    bucket_count: int,
) -> list[tuple[int, list[str]]]:
    """Pack sorted ``(weight, path)`` items into ``bucket_count`` LPT buckets."""
    buckets: list[tuple[int, list[str]]] = [(0, []) for _ in range(bucket_count)]
    for weight, rel_path in items:
        min_idx = min(range(bucket_count), key=lambda idx: buckets[idx][0])
        cur_weight, cur_paths = buckets[min_idx]
        cur_paths.append(rel_path)
        buckets[min_idx] = (cur_weight + weight, cur_paths)
    return [(w, sorted(paths)) for w, paths in buckets if paths]


def _lpt_pack_files(
    files: list[tuple[int, str]],
    num_slices: int,
    *,
    max_slice_weight: int | None = DEFAULT_MAX_SLICE_WEIGHT,
    prefix: str = "slice",
    extra: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Pack ``(weight, rel_path)`` pairs into capacity-capped LPT slices."""
    if not files:
        return []
    ordered = sorted(files, key=lambda item: (-item[0], item[1]))
    clamped_max = max(1, num_slices)

    if max_slice_weight is None or max_slice_weight <= 0:
        packed = _pack_buckets(ordered, min(clamped_max, len(ordered)))
    else:
        solo_limit = clamped_max - 1 if len(ordered) > clamped_max else clamped_max
        solo: list[tuple[int, str]] = []
        rest: list[tuple[int, str]] = []
        for item in ordered:
            if item[0] >= max_slice_weight and len(solo) < solo_limit:
                solo.append(item)
            else:
                rest.append(item)

        packed = [(w, [p]) for w, p in solo]
        if rest:
            remaining_slots = max(1, clamped_max - len(solo))
            rest_total = sum(w for w, _ in rest)
            needed = max(1, math.ceil(rest_total / max_slice_weight))
            bucket_count = min(len(rest), remaining_slots, needed)
            packed.extend(_pack_buckets(rest, bucket_count))

    packed.sort(key=lambda item: (-item[0], item[1][0]))

    result: list[dict[str, str]] = []
    for idx, (_weight, paths) in enumerate(packed):
        entry = {"name": f"{prefix}-{idx + 1:02d}", "targets": ",".join(paths)}
        if extra:
            entry.update(extra)
        result.append(entry)
    return result


def build_file_slices(
    root: Path = Path("src"),
    num_slices: int = DEFAULT_NUM_SLICES,
    *,
    max_slice_weight: int | None = DEFAULT_MAX_SLICE_WEIGHT,
) -> list[dict[str, str]]:
    """Partition Python source files under ``root`` into balanced LPT slices.

    Args:
        root: Package source directory to partition.
        num_slices: Maximum number of parallel matrix slices.
        max_slice_weight: Optional per-slice AST weight cap (``None`` or ``0``
            disables capacity capping and uses ``num_slices`` directly).

    Returns:
        List of ``{"name": ..., "targets": ...}`` dictionaries ordered
        heaviest-first.

    Notes/Architectural Intent:
        Isolates oversized modules into dedicated slices and dynamically
        chooses slice count up to ``num_slices`` based on AST mutation density.
    """
    if not root.is_dir():
        return []
    files = [
        (_file_mutation_weight(path), str(path))
        for path in sorted(root.rglob("*.py"))
        if path.name != "__init__.py" and "__pycache__" not in path.parts
    ]
    return _lpt_pack_files(files, num_slices, max_slice_weight=max_slice_weight)


def build_changed_slices(
    base_ref: str = "main",
    packages_root: Path = Path("packages"),
    root: Path = Path("src"),
    num_slices: int = DEFAULT_NUM_SLICES,
    *,
    max_slice_weight: int | None = DEFAULT_MAX_SLICE_WEIGHT,
) -> list[dict[str, str]]:
    """Partition changed Python source files into LPT-balanced matrix slices.

    Args:
        base_ref: Git base branch name (e.g. ``main``).
        packages_root: Workspace packages directory for monorepo layouts.
        root: Source directory for single-package layouts.
        num_slices: Maximum number of parallel slices per package.
        max_slice_weight: Optional per-slice AST weight cap.

    Returns:
        List of slice dictionaries containing ``name``, ``targets``, and
        (for workspaces) ``package``.

    Notes/Architectural Intent:
        Restricts PR mutation runs to modified Python modules so PR feedback
        completes in minutes while still isolating heavy modified files.
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
                by_pkg.setdefault(parts[1], []).append((_file_mutation_weight(path), pkg_rel))

        slices: list[dict[str, str]] = []
        for dist_name in _resolve_package_names(list(by_pkg.keys()), packages_root):
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
                        == dist_name
                    )
                    or d == dist_name
                ),
                dist_name,
            )
            slices.extend(
                _lpt_pack_files(
                    by_pkg.get(matched_dir, []),
                    num_slices,
                    max_slice_weight=max_slice_weight,
                    prefix=f"{dist_name}-slice",
                    extra={"package": dist_name},
                )
            )
        return slices

    single_files = [
        (_file_mutation_weight(Path(rel)), rel)
        for rel in changed
        if rel.endswith(".py")
        and Path(rel).name != "__init__.py"
        and Path(rel).is_file()
        and Path(rel).is_relative_to(root)
    ]
    return _lpt_pack_files(single_files, num_slices, max_slice_weight=max_slice_weight)


def plan_mutation_matrix(
    mode: str = "affected",
    *,
    base_ref: str = "main",
    packages_root: Path = Path("packages"),
    root: Path = Path("src"),
    num_slices: int = DEFAULT_NUM_SLICES,
    max_slice_weight: int | None = DEFAULT_MAX_SLICE_WEIGHT,
) -> tuple[dict[str, object], bool]:
    """Build a GitHub Actions matrix payload for mutation testing.

    Args:
        mode: Planning mode (``affected``, ``all``, ``slices``, or ``changed-slices``).
        base_ref: Git base branch for ``affected`` / ``changed-slices`` modes.
        packages_root: Workspace packages directory for monorepo layouts.
        root: Source directory for single-package layouts.
        num_slices: Maximum number of slices for slice-based modes.
        max_slice_weight: Optional per-slice AST weight cap.

    Returns:
        Tuple of ``(matrix_dict, has_affected)``.

    Raises:
        ValueError: If ``mode`` is not supported.

    Notes/Architectural Intent:
        Produces a JSON-serializable dict compatible with GitHub Actions
        ``strategy.matrix``.
    """
    if mode == "affected":
        packages = discover_affected_packages(base_ref=base_ref, packages_root=packages_root)
        return {"package": packages}, bool(packages)
    if mode == "all":
        packages = discover_all_packages(packages_root=packages_root)
        return {"package": packages}, bool(packages)
    if mode == "slices":
        slices = build_file_slices(
            root=root, num_slices=num_slices, max_slice_weight=max_slice_weight
        )
        return {"include": slices}, bool(slices)
    if mode == "changed-slices":
        slices = build_changed_slices(
            base_ref=base_ref,
            packages_root=packages_root,
            root=root,
            num_slices=num_slices,
            max_slice_weight=max_slice_weight,
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
    parser.add_argument("--max-weight", type=int, default=DEFAULT_MAX_SLICE_WEIGHT)
    args = parser.parse_args(argv)

    max_weight = args.max_weight if args.max_weight > 0 else None
    matrix_obj, has_affected = plan_mutation_matrix(
        args.mode,
        base_ref=args.base_ref,
        packages_root=Path(args.packages_root),
        root=Path(args.root),
        num_slices=args.slices,
        max_slice_weight=max_weight,
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
    "DEFAULT_MAX_SLICE_WEIGHT",
    "DEFAULT_NUM_SLICES",
    "discover_affected_packages",
    "discover_all_packages",
    "estimate_ast_mutation_weight",
    "main",
    "plan_mutation_matrix",
]


if __name__ == "__main__":
    raise SystemExit(main())
