"""AST parsing and formatting adapter for __all__ integrity checking and auto-sorting.

Notes/Architectural Intent:
    Provides AST-driven inspection and formatting of __all__ declarations without framework
    dependencies. Implements deduplication and casefold alphabetical ordering to guarantee
    consistent, predictable public module surfaces.
"""

from __future__ import annotations

import ast
from collections.abc import Sequence
from pathlib import Path

__all__ = [
    "AllStatementsAnalyzer",
    "check_file_all",
    "fix_file_all",
]


def _find_all_nodes(tree: ast.Module) -> list[ast.Assign]:
    """Return top-level __all__ assignment nodes from a parsed module."""
    return [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    ]


def _extract_symbols(node: ast.Assign) -> list[str]:
    """Extract string literal elements from an __all__ assignment node."""
    if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
        return [
            elt.value
            for elt in node.value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    return []


def check_file_all(py_file: Path) -> list[str]:
    """Inspect a single Python file for __all__ integrity violations.

    Args:
        py_file: Path to Python source file.

    Returns:
        List of violation description strings.

    Notes/Architectural Intent:
        Flags duplicates and casefold alphabetical sorting violations.
    """
    try:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        return []

    errors: list[str] = []
    for node in _find_all_nodes(tree):
        symbols = _extract_symbols(node)
        seen: set[str] = set()
        duplicates: list[str] = []
        for s in symbols:
            if s in seen:
                duplicates.append(s)
            else:
                seen.add(s)
        if duplicates:
            errors.append(f"{py_file}: Duplicate symbol(s) in __all__: {sorted(set(duplicates))}")

        if isinstance(node.value, (ast.List, ast.Tuple)):
            sorted_symbols = sorted(symbols, key=str.casefold)
            if symbols != sorted_symbols:
                errors.append(
                    f"{py_file}: __all__ is not sorted alphabetically. Expected order: {sorted_symbols}"
                )

    return errors


def fix_file_all(py_file: Path) -> bool:
    """Format and alphabetize __all__ declarations in a Python file.

    Args:
        py_file: Path to Python source file.

    Returns:
        True if the file was modified, False otherwise.

    Notes/Architectural Intent:
        Rewrites AST assignment nodes in-place using casefold sorting.
    """
    try:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        return False

    modified = False
    new_content = content

    for node in _find_all_nodes(tree):
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            continue

        symbols = _extract_symbols(node)
        deduped = sorted(set(symbols), key=str.casefold)
        if deduped == symbols and len(deduped) == len(symbols):
            continue

        formatted_list = "[\n" + "".join(f'    "{sym}",\n' for sym in deduped) + "]"
        node_src = ast.get_source_segment(content, node)
        if node_src:
            new_content = new_content.replace(node_src, f"__all__ = {formatted_list}", 1)
            modified = True

    if modified:
        py_file.write_text(new_content, encoding="utf-8")
    return modified


class AllStatementsAnalyzer:
    """Secondary adapter providing batch inspection and auto-sorting of __all__ declarations."""

    def check_files(self, files: Sequence[Path]) -> list[str]:
        """Check multiple Python files for __all__ violations.

        Args:
            files: Sequence of Python file paths.

        Returns:
            Aggregated list of violation messages.

        Notes/Architectural Intent:
            Aggregates results across entire subpackages or the whole monorepo.
        """
        all_errors: list[str] = []
        for file in files:
            all_errors.extend(check_file_all(file))
        return all_errors

    def fix_files(self, files: Sequence[Path]) -> list[Path]:
        """Auto-format and alphabetize __all__ statements in multiple Python files.

        Args:
            files: Sequence of Python file paths to inspect and format.

        Returns:
            List of Path objects for files that were modified.

        Notes/Architectural Intent:
            Enables batch self-healing of __all__ statements across workspaces.
        """
        modified: list[Path] = []
        for file in files:
            if fix_file_all(file):
                modified.append(file)
        return modified
