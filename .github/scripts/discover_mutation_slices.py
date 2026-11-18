"""Discover balanced mutation testing slices for GitHub Actions matrix execution.

Notes/Architectural Intent:
    Emits a single ``matrix=<json>`` line suitable for ``$GITHUB_OUTPUT`` by
    splitting ``domain``, ``ports``, ``cli``, ``infra``, each ``adapters/``
    subdirectory, and top-level ``adapters/*.py`` modules into independent slices.
"""

from __future__ import annotations

import json
from pathlib import Path


def build_mutation_slices(root: Path = Path("src/hexaqual")) -> list[dict[str, str]]:
    """Build ordered list of mutation target slices under ``root``.

    Args:
        root: Package source directory to partition into slices.

    Returns:
        List of ``{"name": ..., "targets": ...}`` dictionaries.
    """
    slices: list[dict[str, str]] = []
    for layer in ("domain", "ports", "cli", "infra"):
        layer_dir = root / layer
        if layer_dir.is_dir():
            slices.append({"name": layer, "targets": str(layer_dir)})

    adapters_dir = root / "adapters"
    if adapters_dir.is_dir():
        for subdir in sorted(adapters_dir.iterdir()):
            if subdir.is_dir() and subdir.name != "__pycache__":
                slices.append({"name": f"adapters-{subdir.name}", "targets": str(subdir)})
        top_files = sorted(
            str(file_path)
            for file_path in adapters_dir.glob("*.py")
            if file_path.name != "__init__.py"
        )
        if top_files:
            slices.append({"name": "adapters-root", "targets": ",".join(top_files)})
    return slices


def main() -> None:
    """Print GitHub Actions matrix output line."""
    payload = {"include": build_mutation_slices()}
    print(f"matrix={json.dumps(payload)}")


if __name__ == "__main__":
    main()
