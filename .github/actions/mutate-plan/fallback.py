#!/usr/bin/env python3
"""Bare-Python fallback shim for the mutate-plan composite GitHub Action.

Notes/Architectural Intent:
    Invoked only when neither ``hexaqual`` nor ``uv`` is available on ``PATH``.
    Loads ``src/hexaqual/utils/mutation_slicing.py`` directly by file path so
    zero third-party dependencies are imported and zero LPT slicing logic is
    duplicated.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Run ``plan_mutation_matrix`` using the shared stdlib slicing module."""
    parser = argparse.ArgumentParser(description="Bare-Python fallback for hexaqual mutate plan")
    parser.add_argument("--mode", default="affected")
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--packages-root", default="packages")
    parser.add_argument("--root", default="src")
    parser.add_argument("--slices", type=int, default=12)
    parser.add_argument("--max-weight", type=int, default=450)
    args = parser.parse_args(argv)

    slicing_path = (
        Path(__file__).resolve().parents[3] / "src" / "hexaqual" / "utils" / "mutation_slicing.py"
    )
    spec = importlib.util.spec_from_file_location("mutation_slicing", slicing_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {slicing_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    matrix_obj, has_affected = mod.plan_mutation_matrix(
        args.mode,
        base_ref=args.base_ref,
        packages_root=Path(args.packages_root),
        root=Path(args.root),
        num_slices=args.slices,
        max_slice_weight=args.max_weight if args.max_weight > 0 else None,
    )
    output_lines = [
        f"matrix={json.dumps(matrix_obj)}",
        f"has_affected={'true' if has_affected else 'false'}",
    ]
    out_path = os.environ.get("GITHUB_OUTPUT", "").strip()
    if out_path:
        with Path(out_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(output_lines) + "\n")
    else:
        sys.stdout.write("\n".join(output_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
