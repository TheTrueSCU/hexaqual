"""Unit tests for hexaqual_audit_docstrings skill.

Notes/Architectural Intent:
    Validates AST-based detection of missing docstrings, missing Args,
    and missing Notes/Architectural Intent sections.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.assets.agents.skills.hexaqual_audit_docstrings import (
    audit_file_docstrings,
)


def test_audit_file_docstrings_clean(tmp_path: Path) -> None:
    """Verify audit_file_docstrings reports zero violations for fully documented module.

    Notes/Architectural Intent:
        Validates clean pass when all Google-style sections are present.
    """
    clean_py = tmp_path / "clean.py"
    clean_py.write_text(
        '''"""Module docstring.

Notes/Architectural Intent:
    Module architectural design.
"""

def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Sum of a and b.

    Notes/Architectural Intent:
        Simple arithmetic addition.
    """
    return a + b
''',
        encoding="utf-8",
    )

    violations = audit_file_docstrings(clean_py)
    violations_count = len(violations)
    assert violations_count == 0


def test_audit_file_docstrings_flags_missing(tmp_path: Path) -> None:
    """Verify audit_file_docstrings flags missing docstrings and missing Architectural Intent.

    Notes/Architectural Intent:
        Asserts detection of incomplete docstrings across module and functions.
    """
    dirty_py = tmp_path / "dirty.py"
    dirty_py.write_text(
        """def undocumented_fn():
    pass

def lacking_intent_fn(x: int):
    \"\"\"Just a summary line.\"\"\"
    return x
""",
        encoding="utf-8",
    )

    violations = audit_file_docstrings(dirty_py)
    violations_count = len(violations)
    assert violations_count >= 2


def test_audit_docstrings_class_and_main(tmp_path: Path) -> None:
    """Verify audit_file_docstrings inspects classes and main executes."""
    from unittest.mock import patch

    from hexaqual.assets.agents.skills.hexaqual_audit_docstrings import main

    dirty_class_py = tmp_path / "dirty_class.py"
    dirty_class_py.write_text(
        '"""Module doc.\n\nNotes/Architectural Intent:\n    Intent.\n"""\n\n'
        "class UndocumentedClass:\n"
        "    def method(self):\n"
        "        pass\n",
        encoding="utf-8",
    )

    violations = audit_file_docstrings(dirty_class_py)
    assert len(violations) >= 1

    with (
        patch("sys.argv", ["skill", str(dirty_class_py)]),
        patch("sys.exit") as mock_exit,
    ):
        main()
        assert mock_exit.called
