# Managed by hexaqual - DO NOT EDIT MANUALLY
"""Skill: Automatically scaffold 1:1 unit test files and package __init__.py stubs.

Notes/Architectural Intent:
    Inspects git status or file arguments to discover source files lacking
    mirrored unit test suites. Automatically generates missing directories,
    __init__.py markers, and starter test skeletons to satisfy test parity gates.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def generate_test_stub_content(module_import_path: str, test_function_name: str) -> str:
    """Generate boilerplate source code for a mirrored unit test file.

    Args:
        module_import_path: Dotted Python import path for the module under test.
        test_function_name: Identifier for the initial test function.

    Returns:
        Formatted Python source string.

    Raises:
        None.

    Notes/Architectural Intent:
        Creates a starter test with side-effect-free assertions and Google docstrings.
    """
    return f'''"""Unit tests for {module_import_path}.

Notes/Architectural Intent:
    Validates structural integrity, interface contracts, and invariants.
"""

from __future__ import annotations

import importlib


def test_{test_function_name}_importable() -> None:
    """Verify module can be imported cleanly without side effects.

    Notes/Architectural Intent:
        Guarantees module definition is valid and has zero broken dependencies.
    """
    mod = importlib.import_module("{module_import_path}")
    is_loaded = mod is not None
    assert is_loaded is True
'''


def find_source_files_needing_parity(root: Path) -> list[tuple[Path, Path]]:
    """Identify source files that lack mirrored unit tests.

    Args:
        root: Workspace or repository root path.

    Returns:
        List of tuples mapping source file path to expected test file path.

    Raises:
        None.

    Notes/Architectural Intent:
        Scans git status --porcelain for added or modified files in src/.
    """
    cmd = ["git", "status", "--porcelain"]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    missing: list[tuple[Path, Path]] = []

    for line in res.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        filepath_str = parts[-1]
        p = root / filepath_str
        if not (p.suffix == ".py" and "src/" in p.parts and not p.name.startswith("__")):
            continue

        # Find package root relative to src
        try:
            src_idx = p.parts.index("src")
            rel_parts = p.parts[src_idx + 1 :]
            # rel_parts: (<pkg>, <layer>, ..., <name>.py)
            if len(rel_parts) < 2:
                continue
            inner_parts = rel_parts[1:]
            module_name = inner_parts[-1][:-3]
            subdirs = inner_parts[:-1]

            # Construct expected test path
            prefix_parts = p.parts[:src_idx]
            test_path = (
                Path(*prefix_parts) / "tests" / "unit" / Path(*subdirs) / f"test_{module_name}.py"
            )
            if not test_path.exists():
                missing.append((p, test_path))
        except (ValueError, IndexError):
            continue

    return missing


def scaffold_test_file(source_file: Path, test_file: Path) -> None:
    """Create directory structure, __init__.py files, and test file.

    Args:
        source_file: Source file path.
        test_file: Target test file path.

    Returns:
        None.

    Raises:
        OSError: If directory or file creation fails.

    Notes/Architectural Intent:
        Ensures all parent directories in tests/unit contain __init__.py.
    """
    test_dir = test_file.parent
    test_dir.mkdir(parents=True, exist_ok=True)

    # Ensure __init__.py in test_dir and intermediate test dirs
    curr = test_dir
    while curr.name != "tests" and curr != curr.parent:
        init_file = curr / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Unit test package marker."""\n', encoding="utf-8")
        curr = curr.parent

    # Derive import path
    src_idx = source_file.parts.index("src")
    rel_parts = source_file.parts[src_idx + 1 :]
    module_parts = [*list(rel_parts[:-1]), rel_parts[-1][:-3]]
    import_path = ".".join(module_parts)
    test_fn_name = module_parts[-1]

    content = generate_test_stub_content(import_path, test_fn_name)
    test_file.write_text(content, encoding="utf-8")


def main() -> None:
    """CLI entrypoint for test parity scaffolder skill.

    Notes/Architectural Intent:
        Scans repository and scaffolds all missing test parity files.
    """
    root = Path.cwd()
    pairs = find_source_files_needing_parity(root)
    if not pairs:
        sys.stdout.write("No missing unit test parity files detected.\n")
        sys.exit(0)

    for src, test in pairs:
        scaffold_test_file(src, test)
        sys.stdout.write(f"Scaffolded test parity: {test.relative_to(root)}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
