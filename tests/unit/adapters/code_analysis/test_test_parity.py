"""Unit tests for test_parity code analysis adapter."""

from __future__ import annotations

from pathlib import Path

from hexaqual.adapters.code_analysis.test_parity import (
    TestParityAnalyzer,
    check_architecture_test_parity,
    check_package_parity,
    check_src_to_test_symmetry,
    check_test_directories_inits,
)


def test_check_test_directories_inits(tmp_path: Path) -> None:
    """Verify detection of missing __init__.py files in test subdirectories."""
    tests_dir = tmp_path / "tests" / "unit" / "sub"
    tests_dir.mkdir(parents=True)
    errors = check_test_directories_inits(tmp_path)
    assert len(errors) == 2  # missing in unit/ and sub/

    (tmp_path / "tests" / "unit" / "__init__.py").touch()
    (tests_dir / "__init__.py").touch()
    errors_clean = check_test_directories_inits(tmp_path)
    assert errors_clean == []


def test_check_package_parity_clean(tmp_path: Path) -> None:
    """Verify clean 1:1 symmetry between src and tests/unit."""
    pkg_dir = tmp_path / "packages" / "mypkg"
    src_dir = pkg_dir / "src" / "mypkg"
    unit_dir = pkg_dir / "tests" / "unit"
    src_dir.mkdir(parents=True)
    unit_dir.mkdir(parents=True)

    (unit_dir / "__init__.py").touch()
    (src_dir / "__init__.py").touch()
    (src_dir / "mod.py").touch()
    (unit_dir / "test_mod.py").touch()

    errors = check_package_parity(pkg_dir, tmp_path)
    assert errors == []


def test_check_package_parity_missing_and_orphaned(tmp_path: Path) -> None:
    """Verify detection of missing unit tests and orphaned unit tests."""
    pkg_dir = tmp_path / "packages" / "mypkg"
    src_dir = pkg_dir / "src" / "mypkg"
    unit_dir = pkg_dir / "tests" / "unit"
    src_dir.mkdir(parents=True)
    unit_dir.mkdir(parents=True)

    (unit_dir / "__init__.py").touch()
    (src_dir / "untested.py").touch()
    (unit_dir / "test_orphan.py").touch()

    errors = check_package_parity(pkg_dir, tmp_path)
    assert any("Missing unit test" in e for e in errors)
    assert any("Orphaned unit test" in e for e in errors)


def test_check_src_to_test_symmetry_workspace(tmp_path: Path) -> None:
    """Verify check_src_to_test_symmetry iterates across workspace packages."""
    assert check_src_to_test_symmetry(tmp_path) == []

    pkg_dir = tmp_path / "packages" / "pkg1"
    src_dir = pkg_dir / "src" / "pkg1"
    unit_dir = pkg_dir / "tests" / "unit"
    src_dir.mkdir(parents=True)
    unit_dir.mkdir(parents=True)
    (unit_dir / "__init__.py").touch()
    (src_dir / "solo.py").touch()

    errors = check_src_to_test_symmetry(tmp_path)
    assert len(errors) == 1
    assert "Missing unit test" in errors[0]


def test_check_architecture_test_parity(tmp_path: Path) -> None:
    """Verify check_architecture_test_parity checks tests/architecture in packages."""
    pkg_dir = tmp_path / "packages" / "pkg_a"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True)

    errors = check_architecture_test_parity(tmp_path)
    assert len(errors) == 1
    assert "Missing architecture tests directory" in errors[0]

    arch_dir = pkg_dir / "tests" / "architecture"
    arch_dir.mkdir(parents=True)
    errors = check_architecture_test_parity(tmp_path)
    assert any("Missing __init__.py" in e for e in errors)
    assert any("Missing architecture tests" in e for e in errors)

    (arch_dir / "__init__.py").touch()
    (arch_dir / "test_hexagonal_boundaries.py").touch()
    errors_clean = check_architecture_test_parity(tmp_path)
    assert errors_clean == []


def test_test_parity_analyzer_class(tmp_path: Path) -> None:
    """Verify TestParityAnalyzer delegating methods."""
    analyzer = TestParityAnalyzer()
    assert analyzer.audit_parity(tmp_path) == []
    assert analyzer.audit_architecture_parity(tmp_path) == []
