"""Unit tests for rope commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hexaqual.adapters.code_analysis.rope import (
    alphabetize_main,
    get_line_offsets,
    get_offset,
    handle_change_signature,
    handle_extract_method,
    handle_extract_var,
    handle_find_occurrences,
    handle_inline,
    handle_move_module,
    handle_move_symbol,
    handle_rename,
    handle_use_function,
    run_main,
    sort_python_file,
)


def test_rope_callables() -> None:
    """Verify rope callables."""
    assert callable(alphabetize_main)
    assert callable(run_main)
    assert callable(sort_python_file)
    assert callable(get_line_offsets)
    assert callable(get_offset)
    assert callable(handle_rename)
    assert callable(handle_change_signature)
    assert callable(handle_extract_method)
    assert callable(handle_extract_var)
    assert callable(handle_find_occurrences)
    assert callable(handle_inline)
    assert callable(handle_move_module)
    assert callable(handle_move_symbol)
    assert callable(handle_use_function)


def test_cst_alphabetizer(tmp_path: Path) -> None:
    """Verify LibCST transformer alphabetizes functions and methods properly."""
    py_file = tmp_path / "sample.py"
    code = """
def zebra():
    pass

def alpha():
    pass

class MyClass:
    def __init__(self):
        pass

    def zoo(self):
        pass

    def bar(self):
        pass
"""
    py_file.write_text(code, encoding="utf-8")
    modified = sort_python_file(py_file)
    assert modified is True

    new_code = py_file.read_text(encoding="utf-8")
    assert new_code.find("def alpha") < new_code.find("def zebra")
    assert new_code.find("def bar") < new_code.find("def zoo")


def test_get_line_offsets(tmp_path: Path) -> None:
    """Verify character offset calculation."""
    f = tmp_path / "test.py"
    f.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
    start, end = get_line_offsets(f, 1, 2)
    assert start == 0
    assert end == len("line 1\nline 2\n")


def test_get_offset(tmp_path: Path) -> None:
    """Verify column/line offset calculation."""
    f = tmp_path / "test.py"
    f.write_text("abc\ndef\n", encoding="utf-8")
    offset = get_offset(f, 2, 2)
    assert offset == len("abc\n") + 1


@patch(
    "sys.argv",
    [
        "rope-run",
        "rename",
        "--file",
        "foo.py",
        "--line",
        "1",
        "--col",
        "1",
        "--new-name",
        "bar",
    ],
)
@patch("hexaqual.adapters.code_analysis.rope.handle_rename")
def test_rope_run_dispatch(mock_rename: MagicMock) -> None:
    """Verify rope run_main dispatches rename subcommand."""
    code = run_main()
    assert code == 0
    mock_rename.assert_called_once()


def test_alphabetize_main_execution(tmp_path: Path) -> None:
    """Verify alphabetize_main sorts targeted python files."""
    py_file = tmp_path / "foo.py"
    py_file.write_text("def b(): pass\ndef a(): pass\n", encoding="utf-8")

    with (
        patch("hexaqual.adapters.code_analysis.rope.ensure_tool_installed"),
        patch(
            "hexaqual.adapters.code_analysis.rope.sort_python_file", return_value=True
        ) as mock_sort,
    ):
        code = alphabetize_main([str(py_file), "--format", "json"])
        assert code == 0
        assert mock_sort.called


def test_handle_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify handle_rename refactors symbol name in project."""
    import argparse

    from hexaqual.adapters.code_analysis.rope import handle_rename

    monkeypatch.chdir(tmp_path)
    mod = tmp_path / "sample_rename.py"
    mod.write_text("my_var = 123\nprint(my_var)\n", encoding="utf-8")

    args = argparse.Namespace(
        root=str(tmp_path),
        file="sample_rename.py",
        line=1,
        col=1,
        new_name="renamed_var",
        dry_run=False,
    )
    handle_rename(args)
    content = mod.read_text(encoding="utf-8")
    assert "renamed_var = 123" in content


def test_handle_extract_method(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify handle_extract_method extracts line range into a function."""
    import argparse

    from hexaqual.adapters.code_analysis.rope import handle_extract_method

    monkeypatch.chdir(tmp_path)
    calc = tmp_path / "sample_calc.py"
    calc.write_text(
        "def main():\n    a = 1\n    b = 2\n    return a + b\n",
        encoding="utf-8",
    )

    args = argparse.Namespace(
        root=str(tmp_path),
        file="sample_calc.py",
        start_line=2,
        end_line=3,
        name="compute_vals",
        dry_run=False,
    )
    handle_extract_method(args)
    content = calc.read_text(encoding="utf-8")
    assert "compute_vals" in content


def test_handle_sort_methods(tmp_path: Path) -> None:
    """Verify _handle_sort_methods sorts methods and handles missing files."""
    from hexaqual.adapters.code_analysis.rope import _handle_sort_methods

    f = tmp_path / "unordered.py"
    f.write_text("def z(): pass\ndef a(): pass\n", encoding="utf-8")

    res = _handle_sort_methods(f, root_dir=tmp_path)
    assert res is True
    assert f.read_text(encoding="utf-8").find("def a") < f.read_text(encoding="utf-8").find("def z")

    # Already sorted file
    res_sorted = _handle_sort_methods(f, root_dir=tmp_path)
    assert res_sorted is False

    # Missing file
    res_missing = _handle_sort_methods(tmp_path / "missing.py", root_dir=tmp_path)
    assert res_missing is False


def test_handle_extract_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify handle_extract_var extracts an expression into a variable."""
    import argparse

    from hexaqual.adapters.code_analysis.rope import handle_extract_var

    monkeypatch.chdir(tmp_path)
    var_file = tmp_path / "sample_var.py"
    var_file.write_text("def get_num():\n    return 10 + 20\n", encoding="utf-8")

    args = argparse.Namespace(
        root=str(tmp_path),
        file="sample_var.py",
        start_line=2,
        start_col=12,
        end_line=2,
        end_col=19,
        name="my_sum",
        dry_run=False,
    )
    handle_extract_var(args)
    content = var_file.read_text(encoding="utf-8")
    assert "my_sum" in content


def test_handle_inline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify handle_inline inlines a variable."""
    import argparse

    from hexaqual.adapters.code_analysis.rope import handle_inline

    monkeypatch.chdir(tmp_path)
    inline_file = tmp_path / "sample_inline.py"
    inline_file.write_text("x = 10\ny = x + 5\n", encoding="utf-8")

    args = argparse.Namespace(
        root=str(tmp_path),
        file="sample_inline.py",
        line=1,
        col=1,
        dry_run=False,
    )
    handle_inline(args)
    content = inline_file.read_text(encoding="utf-8")
    assert "10 + 5" in content


def test_handle_find_occurrences(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify handle_find_occurrences locates occurrences of a symbol."""
    import argparse

    from hexaqual.adapters.code_analysis.rope import handle_find_occurrences

    monkeypatch.chdir(tmp_path)
    occ_file = tmp_path / "sample_occ.py"
    occ_file.write_text("val = 42\nprint(val)\n", encoding="utf-8")

    args = argparse.Namespace(
        root=str(tmp_path),
        file="sample_occ.py",
        line=1,
        col=1,
    )
    handle_find_occurrences(args)


def test_handle_change_signature(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify handle_change_signature reorders function parameters."""
    import argparse

    from hexaqual.adapters.code_analysis.rope import handle_change_signature

    monkeypatch.chdir(tmp_path)
    sig_file = tmp_path / "sample_sig.py"
    sig_file.write_text("def func(a, b):\n    return a + b\n", encoding="utf-8")

    args = argparse.Namespace(
        root=str(tmp_path),
        file="sample_sig.py",
        line=1,
        col=5,
        order="1,0",
        removals=None,
        additions=None,
        dry_run=False,
    )
    handle_change_signature(args)
    content = sig_file.read_text(encoding="utf-8")
    assert "def func(b, a):" in content
