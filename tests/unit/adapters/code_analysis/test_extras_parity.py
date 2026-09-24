"""Unit tests for extras parity code analysis adapter."""

from __future__ import annotations

from pathlib import Path

from hexaqual.adapters.code_analysis.extras_parity import (
    ExtrasParityAnalyzer,
    audit_extras_parity,
    generate_extras_mermaid_diagram,
)


def test_audit_extras_parity_missing_umbrella_toml(tmp_path: Path) -> None:
    """Verify handling when umbrella pyproject.toml is missing."""
    (tmp_path / "packages").mkdir()
    violations = audit_extras_parity(tmp_path)
    assert len(violations) == 1
    assert violations[0].extra_name == "<root>"


def test_audit_extras_parity_and_diagram_generation(tmp_path: Path) -> None:
    """Verify auditing and Mermaid generation with configured workspace."""
    umbrella_dir = tmp_path / "packages" / "hexastack"
    umbrella_dir.mkdir(parents=True)
    (umbrella_dir / "pyproject.toml").write_text(
        """
[project]
name = "hexastack"

[project.optional-dependencies]
sqlite = ["hexastack-db[sqlite]"]
all = ["hexastack-db[sqlite]"]
""",
        encoding="utf-8",
    )

    db_dir = tmp_path / "packages" / "hexastack_db"
    db_dir.mkdir(parents=True)
    (db_dir / "pyproject.toml").write_text(
        """
[project]
name = "hexastack-db"

[project.optional-dependencies]
sqlite = ["aiosqlite>=0.20"]
unforwarded = ["some-pkg>=1.0"]
""",
        encoding="utf-8",
    )

    violations = audit_extras_parity(tmp_path)
    assert len(violations) == 1
    assert violations[0].subpackage == "hexastack-db"
    assert violations[0].extra_name == "unforwarded"

    diagram = generate_extras_mermaid_diagram(tmp_path)
    assert "graph LR" in diagram


def test_extras_parity_analyzer_class(tmp_path: Path) -> None:
    """Verify ExtrasParityAnalyzer delegation methods."""
    analyzer = ExtrasParityAnalyzer()
    (tmp_path / "packages").mkdir()
    violations = analyzer.audit(tmp_path)
    assert len(violations) == 1
    diagram = analyzer.generate_diagram(tmp_path)
    assert diagram == ""
