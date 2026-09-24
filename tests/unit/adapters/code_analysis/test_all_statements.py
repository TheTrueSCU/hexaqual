"""Unit tests for all_statements code analysis adapter."""

from __future__ import annotations

from pathlib import Path

from hexaqual.adapters.code_analysis.all_statements import (
    AllStatementsAnalyzer,
    check_file_all,
    fix_file_all,
)


def test_check_file_all_clean(tmp_path: Path) -> None:
    """Verify clean sorted __all__ produces no errors."""
    f = tmp_path / "clean.py"
    f.write_text('__all__ = ["Alpha", "Beta"]\n', encoding="utf-8")
    assert check_file_all(f) == []


def test_check_file_all_out_of_order_and_duplicate(tmp_path: Path) -> None:
    """Verify out-of-order and duplicate symbols are caught."""
    f = tmp_path / "bad.py"
    f.write_text('__all__ = ["Beta", "Alpha", "Beta"]\n', encoding="utf-8")
    errors = check_file_all(f)
    assert len(errors) == 2


def test_fix_file_all_reformats(tmp_path: Path) -> None:
    """Verify fix_file_all sorts and deduplicates in-place."""
    f = tmp_path / "fixme.py"
    f.write_text('__all__ = ["Beta", "Alpha"]\n', encoding="utf-8")
    modified = fix_file_all(f)
    assert modified is True
    assert check_file_all(f) == []


def test_all_statements_analyzer_batch(tmp_path: Path) -> None:
    """Verify AllStatementsAnalyzer processes multiple files."""
    analyzer = AllStatementsAnalyzer()
    f1 = tmp_path / "f1.py"
    f2 = tmp_path / "f2.py"
    f1.write_text('__all__ = ["B", "A"]\n', encoding="utf-8")
    f2.write_text('__all__ = ["X", "Y"]\n', encoding="utf-8")

    errors = analyzer.check_files([f1, f2])
    assert len(errors) == 1

    modified = analyzer.fix_files([f1, f2])
    assert modified == [f1]
    assert analyzer.check_files([f1, f2]) == []
