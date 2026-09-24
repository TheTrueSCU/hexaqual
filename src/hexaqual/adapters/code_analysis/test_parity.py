"""Filesystem and AST adapter for test directory integrity and 1:1 test parity auditing.

Notes/Architectural Intent:
    Provides filesystem inspection utilities verifying symmetry between packages/*/src
    and packages/*/tests without dependencies on higher-level framework layers.
    Guarantees that every source module has a corresponding unit test and that
    hexagonal boundary architectural tests are present where required.
"""

from __future__ import annotations

import os
from pathlib import Path

from hexaqual.adapters.workspace import get_package_module_dir

__all__ = [
    "check_architecture_test_parity",
    "check_package_parity",
    "check_src_to_test_symmetry",
    "check_test_directories_inits",
    "TestParityAnalyzer",
]

_EXEMPT_SRC_FILES: set[str] = {
    "src/hexastack/__main__.py",
    "src/hexastack_cli/__main__.py",
}

_EXEMPT_TEST_FILES: set[str] = {
    "test_package.py",
    "test_version.py",
}


def check_test_directories_inits(root_dir: Path) -> list[str]:
    """Ensure every sub-directory under packages/*/tests contains __init__.py.

    Args:
        root_dir: Directory containing packages/ directory or a package directory.

    Returns:
        List of missing __init__.py error descriptions.

    Notes/Architectural Intent:
        Prevents missing package namespace markers in test suites that break pytest discovery.
    """
    errors: list[str] = []
    packages_dir = root_dir / "packages" if (root_dir / "packages").is_dir() else root_dir

    if packages_dir.name == "packages":
        pkg_dirs = [p for p in sorted(packages_dir.iterdir()) if p.is_dir()]
    else:
        pkg_dirs = [packages_dir]

    for pkg in pkg_dirs:
        tests_dir = pkg / "tests"
        if not tests_dir.exists():
            continue

        for dirpath, _, _ in os.walk(tests_dir):
            if "__pycache__" in dirpath or ".pytest_cache" in dirpath:
                continue
            if Path(dirpath) == tests_dir:
                continue
            init_file = Path(dirpath) / "__init__.py"
            if not init_file.exists():
                errors.append(f"Missing __init__.py in test directory: {dirpath}")

    return errors


def _check_package_src_symmetry(
    pkg: Path,
    root_dir: Path,
    src_dir: Path,
    unit_tests_dir: Path,
) -> list[str]:
    """Verify each source module in a package has a corresponding unit test."""
    errors: list[str] = []
    for src_file in src_dir.rglob("*.py"):
        rel_root = src_file.relative_to(root_dir)
        if str(rel_root) in _EXEMPT_SRC_FILES or src_file.name == "__init__.py":
            continue

        rel_src = src_file.relative_to(src_dir)
        test_filename = f"test_{src_file.name}"
        test_parts = [*rel_src.parts[:-1], test_filename]
        expected_test = unit_tests_dir.joinpath(*test_parts)

        if not expected_test.is_file():
            errors.append(
                f"Missing unit test for {rel_root}: expected {expected_test.relative_to(root_dir)}"
            )
    return errors


def _check_package_test_symmetry(
    pkg: Path,
    root_dir: Path,
    src_dir: Path,
    unit_tests_dir: Path,
) -> list[str]:
    """Verify each unit test file corresponds to an existing source module."""
    errors: list[str] = []
    for test_file in unit_tests_dir.rglob("*.py"):
        if test_file.name == "__init__.py" or test_file.name in _EXEMPT_TEST_FILES:
            continue
        rel_test = test_file.relative_to(unit_tests_dir)
        if not test_file.name.startswith("test_"):
            continue

        src_filename = test_file.name.removeprefix("test_")
        src_parts = [*rel_test.parts[:-1], src_filename]
        expected_src = src_dir.joinpath(*src_parts)

        if not expected_src.is_file():
            errors.append(
                f"Orphaned unit test {test_file.relative_to(root_dir)}: expected source {expected_src.relative_to(root_dir)}"
            )
    return errors


def check_package_parity(pkg_dir: Path, repo_root: Path) -> list[str]:
    """Audit test directory inits and 1:1 source-to-test symmetry for a package.

    Args:
        pkg_dir: Package directory.
        repo_root: Root path of repository.

    Returns:
        List of parity violation errors.

    Notes/Architectural Intent:
        Scoped package-level parity check used in pre-commit and local fast gates.
    """
    errors: list[str] = []
    errors.extend(check_test_directories_inits(pkg_dir))

    src_dir = pkg_dir / "src" / pkg_dir.name
    unit_tests_dir = pkg_dir / "tests" / "unit"

    if src_dir.exists() and unit_tests_dir.exists():
        errors.extend(_check_package_src_symmetry(pkg_dir, repo_root, src_dir, unit_tests_dir))
        errors.extend(_check_package_test_symmetry(pkg_dir, repo_root, src_dir, unit_tests_dir))

    return errors


def check_src_to_test_symmetry(root_dir: Path) -> list[str]:
    """Ensure every src module has a matching unit test and vice versa across all packages.

    Args:
        root_dir: Root path of repository containing packages/ directory.

    Returns:
        List of symmetry violation descriptions.

    Notes/Architectural Intent:
        Iterates over all workspace packages, inspecting 1:1 source and test module symmetry.
    """
    errors: list[str] = []

    packages_dir = root_dir / "packages"
    if not packages_dir.exists():
        module_dir = get_package_module_dir(root_dir)
        unit_tests_dir = root_dir / "tests" / "unit"
        if module_dir and module_dir.exists() and unit_tests_dir.exists():
            errors.extend(
                _check_package_src_symmetry(root_dir, root_dir, module_dir, unit_tests_dir)
            )
            errors.extend(
                _check_package_test_symmetry(root_dir, root_dir, module_dir, unit_tests_dir)
            )
        return errors

    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue

        src_dir = pkg / "src" / pkg.name
        unit_tests_dir = pkg / "tests" / "unit"

        if not src_dir.exists() or not unit_tests_dir.exists():
            continue

        errors.extend(_check_package_src_symmetry(pkg, root_dir, src_dir, unit_tests_dir))
        errors.extend(_check_package_test_symmetry(pkg, root_dir, src_dir, unit_tests_dir))

    return errors


def _check_package_arch_dir(pkg: Path, root_dir: Path) -> list[str]:
    """Verify architecture tests inside a single package directory."""
    errors: list[str] = []
    arch_dir = pkg / "tests" / "architecture"
    if not arch_dir.is_dir():
        errors.append(
            f"Missing architecture tests directory in {pkg.relative_to(root_dir)}: expected tests/architecture/"
        )
        return errors

    if not (arch_dir / "__init__.py").is_file():
        errors.append(f"Missing __init__.py in {arch_dir.relative_to(root_dir)}")

    if not list(arch_dir.glob("test_*.py")):
        errors.append(
            f"Missing architecture tests in {arch_dir.relative_to(root_dir)}: expected test_hexagonal_boundaries.py"
        )
    return errors


def check_architecture_test_parity(root_dir: Path) -> list[str]:
    """Verify presence of architecture tests across all packages in a workspace.

    Args:
        root_dir: Root path of repository containing packages/ directory or package root.

    Returns:
        List of architecture test parity violation error messages.

    Notes/Architectural Intent:
        Enforces that every workspace package with a source tree contains
        `tests/architecture/test_hexagonal_boundaries.py` and `tests/architecture/__init__.py`.
        Also validates that repository-level architecture tests exist and have init files.
    """
    errors: list[str] = []
    packages_dir = root_dir / "packages"

    if packages_dir.is_dir():
        for pkg in sorted(packages_dir.iterdir()):
            if pkg.is_dir() and (pkg / "src").is_dir():
                errors.extend(_check_package_arch_dir(pkg, root_dir))
    else:
        # Single-package repository
        arch_dir = root_dir / "tests" / "architecture"
        if (root_dir / "src").is_dir() and arch_dir.is_dir():
            if not (arch_dir / "__init__.py").is_file():
                errors.append(f"Missing __init__.py in {arch_dir.relative_to(root_dir)}")
            if not list(arch_dir.glob("test_*.py")):
                errors.append(f"Missing architecture tests in {arch_dir.relative_to(root_dir)}")

    # Check root architecture directory if present in multi-package repository
    root_arch_dir = root_dir / "tests" / "architecture"
    if root_arch_dir.is_dir() and not (root_arch_dir / "__init__.py").is_file():
        errors.append(f"Missing __init__.py in {root_arch_dir.relative_to(root_dir)}")

    return errors


class TestParityAnalyzer:
    """Secondary adapter wrapping test parity inspection for CQRS handlers and CLI."""

    def audit_parity(self, repo_root: Path) -> list[str]:
        """Audit 1:1 source-to-test symmetry across the repository.

        Args:
            repo_root: Root directory of the repository or workspace.

        Returns:
            List of violation error messages.
        """
        return check_src_to_test_symmetry(repo_root)

    def audit_architecture_parity(self, repo_root: Path) -> list[str]:
        """Audit hexagonal architecture test presence across packages.

        Args:
            repo_root: Root directory of the repository or workspace.

        Returns:
            List of violation error messages.
        """
        return check_architecture_test_parity(repo_root)
