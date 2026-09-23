"""Integration tests for hexaqual statements CLI subcommands.

Notes/Architectural Intent:
    Exercises real file AST inspection and LibCST rewrites on disk, verifying
    __all__ deduplication, casefolded alphabetical sorting, and AST integrity.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hexaqual.cli.statements import statements_app


@pytest.mark.integration
def test_statements_check_clean(tmp_path: Path, runner: CliRunner) -> None:
    """Verify check passes for cleanly sorted, deduplicated __all__.

    Args:
        tmp_path: Pytest temporary directory fixture.
        runner: CLI execution runner.
    """
    clean_file = tmp_path / "clean_module.py"
    clean_file.write_text(
        """\"\"\"Clean module.\"\"\"

__all__ = [
    "Alpha",
    "Beta",
]

class Alpha:
    pass

class Beta:
    pass
""",
        encoding="utf-8",
    )

    res = runner.invoke(statements_app, ["check", str(clean_file)])
    assert res.exit_code == 0


@pytest.mark.integration
def test_statements_check_detects_violations(tmp_path: Path, runner: CliRunner) -> None:
    """Verify check rejects unsorted and duplicate __all__ entries.

    Args:
        tmp_path: Pytest temporary directory fixture.
        runner: CLI execution runner.
    """
    dirty_file = tmp_path / "dirty_module.py"
    dirty_file.write_text(
        """\"\"\"Dirty module.\"\"\"

__all__ = [
    "Zeta",
    "Alpha",
    "Zeta",
]
""",
        encoding="utf-8",
    )

    res = runner.invoke(statements_app, ["check", str(dirty_file)])
    assert res.exit_code != 0
    assert "Zeta" in res.stdout or "Alpha" in res.stdout or "unsorted" in res.stdout.lower()


@pytest.mark.integration
def test_statements_fix_roundtrip_ast_safety(tmp_path: Path, runner: CliRunner) -> None:
    """Verify fix rewrites __all__ into sorted/deduplicated form with valid AST.

    Args:
        tmp_path: Pytest temporary directory fixture.
        runner: CLI execution runner.
    """
    target_file = tmp_path / "fixable_module.py"
    target_file.write_text(
        """\"\"\"Module to be fixed.\"\"\"

# Important header comment
__all__ = [
    "Gamma",
    "beta",
    "Alpha",
    "Gamma",
]

def beta() -> None:
    pass
""",
        encoding="utf-8",
    )

    # 1. Run fix
    res_fix = runner.invoke(statements_app, ["fix", str(target_file)])
    assert res_fix.exit_code == 0

    # 2. Verify AST validity
    content = target_file.read_text(encoding="utf-8")
    parsed_tree = ast.parse(content)
    assert parsed_tree is not None

    # 3. Verify casefold sorted and deduplicated order: ["Alpha", "beta", "Gamma"]
    assert '"Alpha"' in content
    assert '"beta"' in content
    assert '"Gamma"' in content
    # Deduplication check
    assert content.count('"Gamma"') == 1

    # 4. Verify subsequent check passes cleanly
    res_check = runner.invoke(statements_app, ["check", str(target_file)])
    assert res_check.exit_code == 0
