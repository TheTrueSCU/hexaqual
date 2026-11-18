"""Discover balanced mutation testing slices for GitHub Actions matrix execution.

Notes/Architectural Intent:
    Globs all Python source modules under ``src/hexaqual`` and uses
    Longest-Processing-Time-first (LPT) greedy bin-packing by line count to
    partition ``--gremlin-targets`` into balanced matrix slices.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_NUM_SLICES = 12


def build_mutation_slices(
    root: Path = Path("src/hexaqual"),
    num_slices: int = DEFAULT_NUM_SLICES,
) -> list[dict[str, str]]:
    """Partition Python source files under ``root`` into balanced slices.

    Args:
        root: Package source directory to partition into slices.
        num_slices: Maximum number of parallel matrix slices.

    Returns:
        List of ``{"name": ..., "targets": ...}`` dictionaries.
    """
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


def main() -> None:
    """Print GitHub Actions matrix output line."""
    payload = {"include": build_mutation_slices()}
    print(f"matrix={json.dumps(payload)}")


if __name__ == "__main__":
    main()
