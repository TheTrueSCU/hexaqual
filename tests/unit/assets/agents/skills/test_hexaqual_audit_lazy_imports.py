"""Unit tests for hexaqual_audit_lazy_imports skill.

Notes/Architectural Intent:
    Validates AST lazy import scanner, boundary bypass detection,
    standard library module detection, and CLI exit codes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hexaqual.assets.agents.skills.hexaqual_audit_lazy_imports import (
    audit_directory,
    audit_file,
    main,
)


def test_audit_file_clean(tmp_path: Path) -> None:
    """Verify that a file with top-level imports produces zero violations.

    Notes/Architectural Intent:
        Guarantees that standard compliant modules pass with empty violation lists.
    """
    clean_code = "import os\nimport sys\n\ndef compute(value: int) -> int:\n    return value * 2\n"
    src_file = tmp_path / "clean.py"
    src_file.write_text(clean_code, encoding="utf-8")

    violations = audit_file(src_file, tmp_path)
    violation_count = len(violations)
    assert violation_count == 0


def test_audit_file_stdlib_in_function(tmp_path: Path) -> None:
    """Verify that standard library imports inside functions are flagged.

    Notes/Architectural Intent:
        Enforces rule that stdlib modules must reside at module top-level.
    """
    bad_code = (
        "def run_command():\n    import subprocess\n    return subprocess.run(['echo', 'hello'])\n"
    )
    src_file = tmp_path / "bad.py"
    src_file.write_text(bad_code, encoding="utf-8")

    violations = audit_file(src_file, tmp_path)
    violation_count = len(violations)
    assert violation_count == 1
    assert violations[0].category == "stdlib-in-function"
    assert violations[0].imported_module == "subprocess"
    assert violations[0].function_name == "run_command"


def test_audit_file_adapter_to_infra_bypass(tmp_path: Path) -> None:
    """Verify that adapters importing from infra inside functions are flagged.

    Notes/Architectural Intent:
        Prevents ADR-001 architectural boundary circumvention.
    """
    adapter_dir = tmp_path / "src" / "pkg" / "adapters"
    adapter_dir.mkdir(parents=True)
    adapter_file = adapter_dir / "ui.py"

    code = (
        "def render():\n    from pkg.infra.registries import Registry\n    return Registry.list()\n"
    )
    adapter_file.write_text(code, encoding="utf-8")

    violations = audit_file(adapter_file, tmp_path)
    violation_count = len(violations)
    assert violation_count == 1
    assert violations[0].category == "boundary-bypass-adapter-to-infra"
    assert violations[0].imported_module == "pkg.infra.registries"


def test_audit_file_domain_impurity_bypass(tmp_path: Path) -> None:
    """Verify that domain entities importing from ports/adapters/infra are flagged.

    Notes/Architectural Intent:
        Enforces domain layer purity with zero outer layer dependencies.
    """
    domain_dir = tmp_path / "src" / "pkg" / "domain"
    domain_dir.mkdir(parents=True)
    domain_file = domain_dir / "model.py"

    code = (
        "def notify():\n"
        "    from pkg.adapters.notifications import AppriseAdapter\n"
        "    return AppriseAdapter()\n"
    )
    domain_file.write_text(code, encoding="utf-8")

    violations = audit_file(domain_file, tmp_path)
    violation_count = len(violations)
    assert violation_count == 1
    assert violations[0].category == "boundary-bypass-domain-purity"
    assert violations[0].imported_module == "pkg.adapters.notifications"


def test_audit_directory_skips_tests_by_default(tmp_path: Path) -> None:
    """Verify that tests/ directory is excluded by default but included when requested.

    Notes/Architectural Intent:
        Ensures production source code is strictly gated without failing on test mock imports.
    """
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_dummy.py"
    test_file.write_text("def test_foo():\n    import os\n    assert os.name\n", encoding="utf-8")

    default_violations = audit_directory(tmp_path, tmp_path, include_tests=False)
    default_count = len(default_violations)
    assert default_count == 0

    included_violations = audit_directory(tmp_path, tmp_path, include_tests=True)
    included_count = len(included_violations)
    assert included_count == 1


def test_main_cli_entrypoint_clean(tmp_path: Path) -> None:
    """Verify that main exits with code 0 on clean target.

    Notes/Architectural Intent:
        Validates CLI contract for integration into CI pipelines.
    """
    src_file = tmp_path / "clean.py"
    src_file.write_text("def ok(): pass\n", encoding="utf-8")

    with (
        patch("sys.argv", ["skill", str(src_file)]),
        patch("pathlib.Path.cwd", return_value=tmp_path),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    code = exc_info.value.code
    assert code == 0


def test_main_cli_entrypoint_violations(tmp_path: Path) -> None:
    """Verify that main exits with code 1 when violations exist.

    Notes/Architectural Intent:
        Ensures CI quality gate failure on detected unauthorized imports.
    """
    src_file = tmp_path / "bad.py"
    src_file.write_text("def bad():\n    import os\n", encoding="utf-8")

    with (
        patch("sys.argv", ["skill", str(src_file)]),
        patch("pathlib.Path.cwd", return_value=tmp_path),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()
    code = exc_info.value.code
    assert code == 1
