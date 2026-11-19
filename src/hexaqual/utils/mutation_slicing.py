"""AST-weighted, capacity-capped LPT bin packing and mutation matrix planning.

Notes/Architectural Intent:
    Shared pure-stdlib utility module imported by both the Hexaqueue cluster
    runner adapter and the ``hexaqual mutate plan`` CLI command so AST mutation
    weighting, heavy-file isolation, dynamic slice expansion, and LPT dispatch
    ordering have a single source of truth with zero external dependencies.
"""

from __future__ import annotations

import ast
import math
import subprocess
import tomllib
from collections.abc import Sequence
from pathlib import Path

DEFAULT_MAX_CLUSTER_SLICES = 16
DEFAULT_MAX_SLICE_WEIGHT = 450
DEFAULT_NUM_SLICES = 12

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
        Falls back to line count if ``source`` cannot be parsed.
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


def estimate_file_mutation_weight(path: Path) -> int:
    """Estimate mutation workload weight for a Python file on disk.

    Args:
        path: Filesystem path to a Python source file.

    Returns:
        Positive integer estimating relative gremlin generation workload.

    Notes/Architectural Intent:
        Returns ``_PER_FILE_OVERHEAD`` when the file cannot be read.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return _PER_FILE_OVERHEAD
    return estimate_ast_mutation_weight(source)


def _pack_into_buckets(
    items: list[tuple[int, str]],
    bucket_count: int,
) -> list[tuple[int, list[str]]]:
    """Pack sorted ``(weight, path)`` items into ``bucket_count`` LPT buckets."""
    buckets: list[tuple[int, list[str]]] = [(0, []) for _ in range(bucket_count)]
    for weight, target in items:
        min_idx = min(range(bucket_count), key=lambda idx: buckets[idx][0])
        cur_weight, cur_paths = buckets[min_idx]
        cur_paths.append(target)
        buckets[min_idx] = (cur_weight + weight, cur_paths)
    return [(w, sorted(paths)) for w, paths in buckets if paths]


def partition_targets_lpt(
    weighted_items: Sequence[tuple[int, str]],
    *,
    min_slices: int = 1,
    max_slices: int = DEFAULT_MAX_CLUSTER_SLICES,
    max_slice_weight: int | None = DEFAULT_MAX_SLICE_WEIGHT,
) -> list[tuple[int, list[str]]]:
    """Partition weighted target files into capacity-capped LPT slices.

    Args:
        weighted_items: Sequence of ``(weight, target_path)`` tuples.
        min_slices: Minimum number of slices to produce (bounded by file count).
        max_slices: Upper bound on total slices produced.
        max_slice_weight: Optional per-slice AST weight cap. When set, files
            with ``weight >= max_slice_weight`` are isolated into solo slices
            and remaining files expand dynamically to stay near the cap.

    Returns:
        List of ``(total_weight, sorted_target_paths)`` tuples ordered
        heaviest-first (LPT dispatch order).

    Notes/Architectural Intent:
        Isolating oversized files prevents extra files from piling onto dense
        modules, while heaviest-first ordering schedules the slowest slice first.
    """
    if not weighted_items:
        return []

    ordered = sorted(weighted_items, key=lambda item: (-item[0], item[1]))
    clamped_max = max(1, max_slices)
    clamped_min = min(max(1, min_slices), clamped_max, len(ordered))

    if max_slice_weight is None or max_slice_weight <= 0:
        packed = _pack_into_buckets(ordered, clamped_min)
        packed.sort(key=lambda item: (-item[0], item[1][0]))
        return packed

    solo_limit = clamped_max - 1 if len(ordered) > clamped_max else clamped_max
    solo: list[tuple[int, str]] = []
    rest: list[tuple[int, str]] = []
    for item in ordered:
        if item[0] >= max_slice_weight and len(solo) < solo_limit:
            solo.append(item)
        else:
            rest.append(item)

    slices: list[tuple[int, list[str]]] = [(w, [p]) for w, p in solo]
    if rest:
        remaining_slots = max(1, clamped_max - len(solo))
        rest_total = sum(w for w, _ in rest)
        min_rest_buckets = max(1, clamped_min - len(solo))
        needed_buckets = max(min_rest_buckets, math.ceil(rest_total / max_slice_weight))
        bucket_count = min(len(rest), remaining_slots, needed_buckets)
        slices.extend(_pack_into_buckets(rest, bucket_count))

    slices.sort(key=lambda item: (-item[0], item[1][0]))
    return slices


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
        estimate_file_mutation_weight(path)
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
        immediately on bounded worker pools.
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


def _format_slices(
    packed: list[tuple[int, list[str]]],
    *,
    prefix: str = "slice",
    extra: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Format packed ``(weight, paths)`` tuples into matrix include dicts."""
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
            disables capacity capping).

    Returns:
        List of ``{"name": ..., "targets": ...}`` dictionaries ordered
        heaviest-first.

    Notes/Architectural Intent:
        Isolates oversized modules into solo slices and dynamically chooses
        slice count up to ``num_slices`` based on AST mutation density.
    """
    if not root.is_dir():
        return []
    files = [
        (estimate_file_mutation_weight(path), str(path))
        for path in sorted(root.rglob("*.py"))
        if path.name != "__init__.py" and "__pycache__" not in path.parts
    ]
    min_slices = 1 if (max_slice_weight and max_slice_weight > 0) else num_slices
    packed = partition_targets_lpt(
        files,
        min_slices=min_slices,
        max_slices=num_slices,
        max_slice_weight=max_slice_weight,
    )
    return _format_slices(packed)


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

    min_slices = 1 if (max_slice_weight and max_slice_weight > 0) else num_slices

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
                by_pkg.setdefault(parts[1], []).append(
                    (estimate_file_mutation_weight(path), pkg_rel)
                )

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
            packed = partition_targets_lpt(
                by_pkg.get(matched_dir, []),
                min_slices=min_slices,
                max_slices=num_slices,
                max_slice_weight=max_slice_weight,
            )
            slices.extend(
                _format_slices(
                    packed,
                    prefix=f"{dist_name}-slice",
                    extra={"package": dist_name},
                )
            )
        return slices

    single_files = [
        (estimate_file_mutation_weight(Path(rel)), rel)
        for rel in changed
        if rel.endswith(".py")
        and Path(rel).name != "__init__.py"
        and Path(rel).is_file()
        and Path(rel).is_relative_to(root)
    ]
    packed = partition_targets_lpt(
        single_files,
        min_slices=min_slices,
        max_slices=num_slices,
        max_slice_weight=max_slice_weight,
    )
    return _format_slices(packed)


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


__all__ = [
    "build_changed_slices",
    "build_file_slices",
    "DEFAULT_MAX_CLUSTER_SLICES",
    "DEFAULT_MAX_SLICE_WEIGHT",
    "DEFAULT_NUM_SLICES",
    "discover_affected_packages",
    "discover_all_packages",
    "estimate_ast_mutation_weight",
    "estimate_file_mutation_weight",
    "partition_targets_lpt",
    "plan_mutation_matrix",
]
