"""Unit tests for hexaqual_audit_complexity skill.

Notes/Architectural Intent:
    Validates check_complexity function and error handling for missing paths.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hexaqual.assets.agents.skills.hexaqual_audit_complexity import check_complexity


def test_check_complexity_non_existent_path_raises() -> None:
    """Verify check_complexity raises FileNotFoundError for non-existent path.

    Notes/Architectural Intent:
        Guarantees clear error reporting on invalid paths.
    """
    with pytest.raises(FileNotFoundError):
        check_complexity("/non/existent/path/for/sure")


def test_check_complexity_clean(tmp_path: Path) -> None:
    """Verify check_complexity returns 0 when complexipy succeeds.

    Notes/Architectural Intent:
        Asserts return code 0 on successful complexity audit.
    """
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("def hello(): pass\n", encoding="utf-8")

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "All functions <= 25"

    with patch("subprocess.run", return_value=mock_res):
        res = check_complexity(str(sample_file))
        assert res == 0
