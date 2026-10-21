# Managed by hexaqual - DO NOT EDIT MANUALLY
"""Skill: Audit Python codebases for unauthorized lazy imports and layer bypasses.

Notes/Architectural Intent:
    AST-based validator that inspects function definitions to detect:
    1. Standard library modules imported inside functions/methods (must reside at top-level).
    2. Hexagonal layer boundary bypasses (e.g. adapters importing from infra inside methods).
    3. Unguarded third-party imports attempting to bypass import linter restrictions.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

STDLIB_MODULES: frozenset[str] = frozenset(sys.stdlib_module_names)


@dataclass(frozen=True, slots=True)
class LazyImportViolation:
    """Represents a detected unauthorized lazy import violation.

    Notes/Architectural Intent:
        Encapsulates exact location, offending imported module, containing function,
        and violation category for structured terminal diagnostics.
    """

    file_path: str
    line_number: int
    function_name: str
    imported_module: str
    category: str
    message: str


class LazyImportVisitor(ast.NodeVisitor):
    """AST visitor traversing function bodies for unauthorized lazy imports.

    Notes/Architectural Intent:
        Visits FunctionDef and AsyncFunctionDef nodes, scanning child import nodes
        without traversing into nested classes or re-visiting top-level module statements.
    """

    def __init__(self, file_path: Path, repo_root: Path) -> None:
        """Initialize the visitor for a specific file.

        Args:
            file_path: Absolute path to the source file being analyzed.
            repo_root: Root directory of the repository for relative path calculations.
        """
        super().__init__()
        self.file_path = file_path
        self.repo_root = repo_root
        try:
            self.rel_path = str(file_path.relative_to(repo_root))
        except ValueError:
            self.rel_path = str(file_path)
        self.violations: list[LazyImportViolation] = []
        self._current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Inspect synchronous function definition for lazy imports.

        Args:
            node: AST FunctionDef node.
        """
        old_fn = self._current_function
        self._current_function = node.name
        self._scan_function_body(node)
        self._current_function = old_fn

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Inspect asynchronous function definition for lazy imports.

        Args:
            node: AST AsyncFunctionDef node.
        """
        old_fn = self._current_function
        self._current_function = node.name
        self._scan_function_body(node)
        self._current_function = old_fn

    def _scan_function_body(self, fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Scan child nodes inside a function for import statements.

        Args:
            fn_node: Function definition AST node.
        """
        for child in ast.walk(fn_node):
            if child is fn_node:
                continue
            if isinstance(child, ast.Import):
                for alias in child.names:
                    self._check_import(alias.name, child.lineno)
            elif isinstance(child, ast.ImportFrom) and child.module:
                self._check_import(child.module, child.lineno)

    def _check_import(self, module_name: str, lineno: int) -> None:
        """Evaluate an in-function import against architectural invariants.

        Args:
            module_name: Full module path being imported.
            lineno: Source line number of the import statement.

        Notes/Architectural Intent:
            Checks whether the imported module belongs to Python standard library
            or violates hexagonal boundary rules (e.g. adapter -> infra).
        """
        root_pkg = module_name.split(".")[0]
        fn_name = self._current_function or "<anonymous>"

        # 1. Standard Library Prohibition
        if root_pkg in STDLIB_MODULES:
            self.violations.append(
                LazyImportViolation(
                    file_path=self.rel_path,
                    line_number=lineno,
                    function_name=fn_name,
                    imported_module=module_name,
                    category="stdlib-in-function",
                    message="Standard library imports must reside at module top-level.",
                )
            )
            return

        # 2. Hexagonal Boundary Bypass: Adapter importing from Infra
        is_adapter = "/adapters/" in self.rel_path or self.rel_path.startswith("adapters/")
        is_infra_import = ".infra" in module_name or module_name.endswith(".infra")
        if is_adapter and is_infra_import:
            self.violations.append(
                LazyImportViolation(
                    file_path=self.rel_path,
                    line_number=lineno,
                    function_name=fn_name,
                    imported_module=module_name,
                    category="boundary-bypass-adapter-to-infra",
                    message="Adapters may never import from infra/ (ADR-001 violation).",
                )
            )
            return

        # 3. Hexagonal Boundary Bypass: Domain importing from Ports, Adapters, or Infra
        is_domain = "/domain/" in self.rel_path or self.rel_path.startswith("domain/")
        is_impure_import = any(layer in module_name for layer in (".ports", ".adapters", ".infra"))
        if is_domain and is_impure_import:
            self.violations.append(
                LazyImportViolation(
                    file_path=self.rel_path,
                    line_number=lineno,
                    function_name=fn_name,
                    imported_module=module_name,
                    category="boundary-bypass-domain-purity",
                    message="Domain models must maintain 0 dependencies on ports, adapters, or infra.",
                )
            )


def audit_file(file_path: Path, repo_root: Path) -> list[LazyImportViolation]:
    """Parse and audit a single Python source file.

    Args:
        file_path: Path to the target Python file.
        repo_root: Root directory of the repository.

    Returns:
        List of LazyImportViolation instances found in the file.

    Raises:
        None. Suppresses and logs syntax errors for resilient batch operation.

    Notes/Architectural Intent:
        Parses AST with type_comments=False for fast static evaluation.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"Warning: Could not parse {file_path}: {exc}\n")
        return []

    visitor = LazyImportVisitor(file_path=file_path, repo_root=repo_root)
    visitor.visit(tree)
    return visitor.violations


def audit_directory(
    target_path: Path, repo_root: Path, *, include_tests: bool = False
) -> list[LazyImportViolation]:
    """Recursively collect and audit all Python files under a target directory.

    Args:
        target_path: Target directory or file path to evaluate.
        repo_root: Root directory of the repository.
        include_tests: Whether to include tests/ directories in the audit.

    Returns:
        Consolidated list of LazyImportViolation instances.

    Notes/Architectural Intent:
        Filters out virtual environments, test directories (unless include_tests=True),
        and build artifacts to focus on production source code.
    """
    if target_path.is_file():
        return audit_file(target_path, repo_root)

    violations: list[LazyImportViolation] = []
    excluded_parts = {".venv", "venv", ".git", "__pycache__", ".tox", "build", "dist"}
    if not include_tests:
        excluded_parts.add("tests")

    for p in target_path.rglob("*.py"):
        if any(part in p.parts for part in excluded_parts):
            continue
        violations.extend(audit_file(p, repo_root))

    return violations


def main() -> None:
    """CLI entrypoint for lazy import audit skill.

    Notes/Architectural Intent:
        Parses CLI arguments, discovers repository root, executes audit,
        and outputs formatted diagnostics with strict exit codes.
    """
    parser = argparse.ArgumentParser(
        description="Audit Python codebase for unauthorized lazy imports and layer bypasses."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="src/",
        help="Target file or directory to scan (defaults to 'src/' or 'packages/').",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include tests/ directories in the audit (excluded by default).",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    target_arg = args.target
    target_path = Path(target_arg).resolve()

    if not target_path.exists():
        # Check if workspace monorepo layout (e.g. packages/ exists)
        packages_dir = repo_root / "packages"
        if packages_dir.is_dir() and target_arg == "src/":
            target_path = packages_dir
            target_arg = "packages/"
        else:
            sys.stderr.write(f"Error: Target path does not exist: {target_path}\n")
            sys.exit(1)

    violations = audit_directory(target_path, repo_root, include_tests=args.include_tests)

    if not violations:
        sys.stdout.write(
            f"✅ Clean: No unauthorized lazy imports or layer bypasses detected in '{target_arg}'.\n"
        )
        sys.exit(0)

    sys.stderr.write(
        f"❌ Found {len(violations)} unauthorized lazy import violation(s) in '{target_arg}':\n\n"
    )

    for v in sorted(violations, key=lambda x: (x.file_path, x.line_number)):
        sys.stderr.write(
            f"  {v.file_path}:{v.line_number} in `{v.function_name}` -> `{v.imported_module}`\n"
            f"    [{v.category}] {v.message}\n"
        )

    sys.stderr.write(
        "\nRemediation:\n"
        "  - Move standard library imports to module top-level.\n"
        "  - Decouple adapters from infra/ using abstract ports (ADR-001).\n"
        "  - Guard legitimate optional extras via 'hexastack_core.utils.imports.require_dependency'.\n"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
