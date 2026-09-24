"""Unit tests for hexaqual_scaffold_test_parity skill.

Notes/Architectural Intent:
    Validates generation of test stub code and automatic scaffolding of directories
    and __init__.py markers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hexaqual.assets.agents.skills.hexaqual_scaffold_test_parity import (
    generate_test_stub_content,
    scaffold_test_file,
)


def test_generate_test_stub_content() -> None:
    """Verify test stub code template generation.

    Notes/Architectural Intent:
        Asserts presence of importability test and docstring in generated code.
    """
    content = generate_test_stub_content("my_pkg.domain.model", "model")
    assert "test_model_importable" in content
    assert "Notes/Architectural Intent:" in content
    assert "importlib.import_module" in content


def test_scaffold_test_file(tmp_path: Path) -> None:
    """Verify scaffolding creates parent directories, __init__.py files, and test stub.

    Notes/Architectural Intent:
        Validates complete directory and marker initialization.
    """
    src_file = tmp_path / "src" / "my_pkg" / "domain" / "model.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("class Model: pass\n", encoding="utf-8")

    test_file = tmp_path / "tests" / "unit" / "domain" / "test_model.py"

    scaffold_test_file(src_file, test_file)

    test_exists = test_file.exists()
    init_exists = (tmp_path / "tests" / "unit" / "domain" / "__init__.py").exists()

    assert test_exists is True
    assert init_exists is True


def test_find_source_files_needing_parity_and_main(tmp_path: Path) -> None:
    """Verify find_source_files_needing_parity detects unmirrored source files."""
    from unittest.mock import MagicMock, patch

    from hexaqual.assets.agents.skills.hexaqual_scaffold_test_parity import (
        find_source_files_needing_parity,
        main,
    )

    src_file = tmp_path / "src" / "my_pkg" / "untested.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("x = 1\n", encoding="utf-8")

    mock_git = MagicMock(
        stdout=(
            " \n"
            " M not_src.py\n"
            " M src/my_pkg/__init__.py\n"
            " M src/file_at_root_of_src.py\n"
            " M src/my_pkg/untested.py\n"
        ),
        returncode=0,
    )
    with patch("subprocess.run", return_value=mock_git):
        missing = find_source_files_needing_parity(tmp_path)
        assert len(missing) == 1
        assert missing[0][0] == src_file

        # When test file already exists
        test_path = tmp_path / "tests" / "unit" / "test_untested.py"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text("def test(): pass\n", encoding="utf-8")
        missing_none = find_source_files_needing_parity(tmp_path)
        assert len(missing_none) == 0

    # 1. main when no pairs
    with (
        patch("sys.argv", ["skill"]),
        patch(
            "hexaqual.assets.agents.skills.hexaqual_scaffold_test_parity.find_source_files_needing_parity",
            return_value=[],
        ),
        pytest.raises(SystemExit) as exc_info1,
    ):
        main()
    assert exc_info1.value.code == 0

    # 2. main when pairs exist
    fake_pair = (src_file, test_path)
    with (
        patch("sys.argv", ["skill"]),
        patch.object(Path, "cwd", return_value=tmp_path),
        patch(
            "hexaqual.assets.agents.skills.hexaqual_scaffold_test_parity.find_source_files_needing_parity",
            return_value=[fake_pair],
        ),
        patch(
            "hexaqual.assets.agents.skills.hexaqual_scaffold_test_parity.scaffold_test_file",
        ) as mock_scaffold,
        pytest.raises(SystemExit) as exc_info2,
    ):
        main()
    assert exc_info2.value.code == 0
    mock_scaffold.assert_called_once_with(src_file, test_path)
