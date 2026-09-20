"""Unit tests for hexaqual_scaffold_test_parity skill.

Notes/Architectural Intent:
    Validates generation of test stub code and automatic scaffolding of directories
    and __init__.py markers.
"""

from __future__ import annotations

from pathlib import Path

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
