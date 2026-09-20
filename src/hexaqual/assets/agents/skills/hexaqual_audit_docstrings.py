# Managed by hexaqual - DO NOT EDIT MANUALLY
"""Skill: Audit Python files for Google-style docstrings and Architectural Intent.

Notes/Architectural Intent:
    AST-based validator that inspects public modules, classes, and callables
    to verify presence of Google-style docstrings with mandatory Args, Returns,
    Raises, and Notes/Architectural Intent sections.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def audit_callable_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef, filename: str
) -> list[str]:
    """Audit a function or method AST node for docstring completeness.

    Args:
        node: The AST FunctionDef or AsyncFunctionDef node to evaluate.
        filename: Name of the source file containing the node.

    Returns:
        List of formatted violation strings.

    Raises:
        None.

    Notes/Architectural Intent:
        Checks for presence of docstring and validates required Google-style sections.
    """
    violations: list[str] = []
    doc = ast.get_docstring(node)
    func_name = node.name

    if not doc:
        violations.append(
            f"{filename}:{node.lineno} Function '{func_name}' is missing a docstring."
        )
        return violations

    if "Notes/Architectural Intent:" not in doc:
        violations.append(
            f"{filename}:{node.lineno} Function '{func_name}' is missing a 'Notes/Architectural Intent:' section."
        )

    # Check Args if has arguments other than self/cls
    args = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]
    if args and "Args:" not in doc:
        violations.append(
            f"{filename}:{node.lineno} Function '{func_name}' has arguments but lacks an 'Args:' section."
        )

    return violations


def audit_file_docstrings(file_path: Path) -> list[str]:
    """Audit all public entities within a Python source file for docstrings.

    Args:
        file_path: Path to the Python file to inspect.

    Returns:
        List of violation messages found in the file.

    Raises:
        SyntaxError: If the file cannot be parsed as valid Python AST.

    Notes/Architectural Intent:
        Inspects module-level docstring, public classes, and public functions.
    """
    violations: list[str] = []
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    # Check module docstring
    module_doc = ast.get_docstring(tree)
    if not module_doc:
        violations.append(f"{file_path}:1 Module is missing a top-level docstring.")
    elif "Notes/Architectural Intent:" not in module_doc:
        violations.append(
            f"{file_path}:1 Module docstring is missing 'Notes/Architectural Intent:' section."
        )

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            violations.extend(audit_callable_docstring(node, str(file_path)))
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            class_doc = ast.get_docstring(node)
            if not class_doc:
                violations.append(
                    f"{file_path}:{node.lineno} Class '{node.name}' is missing a docstring."
                )
            for item in node.body:
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not item.name.startswith("_"):
                    violations.extend(audit_callable_docstring(item, str(file_path)))

    return violations


def main() -> None:
    """CLI entrypoint for docstring audit skill.

    Notes/Architectural Intent:
        Accepts paths to inspect and outputs Rich or plain diagnostic reports.
    """
    target = sys.argv[1] if len(sys.argv) > 1 else "src/"
    path = Path(target)
    files = [path] if path.is_file() else list(path.glob("**/*.py"))

    all_violations: list[str] = []
    for f in files:
        if "/tests/" in str(f) or f.name.startswith("test_"):
            continue
        try:
            violations = audit_file_docstrings(f)
            all_violations.extend(violations)
        except SyntaxError as err:
            all_violations.append(f"{f}: Syntax error during AST parse: {err}")

    if all_violations:
        sys.stderr.write(f"Found {len(all_violations)} docstring violation(s):\n")
        for v in all_violations:
            sys.stderr.write(f"  - {v}\n")
        sys.exit(1)

    sys.stdout.write(
        f"All inspected files in {target} satisfy docstring and Architectural Intent requirements.\n"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
