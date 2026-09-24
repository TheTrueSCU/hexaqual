"""Integration tests for hexaqual deps CLI subcommands.

Notes/Architectural Intent:
    Exercises import-linter boundary checking, deptry dependency analysis,
    and pydeps architecture diagram generation in a synthetic workspace.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hexaqual.cli.deps import deps_app


@pytest.mark.integration
def test_deps_help(runner: CliRunner) -> None:
    """Verify deps CLI root command displays help and options."""
    res = runner.invoke(deps_app, ["--help"])
    assert res.exit_code == 0
    assert "Audit dependencies" in res.stdout


@pytest.mark.integration
def test_deps_linter_generate_and_check(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify generating import-linter configuration and executing boundary check.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # 1. Create hexagonal layers in pkg_core
    pkg_core_src = synthetic_workspace / "packages" / "pkg_core" / "src" / "pkg_core"
    domain_dir = pkg_core_src / "domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    (domain_dir / "__init__.py").write_text('"""Domain."""\n', encoding="utf-8")
    (domain_dir / "user.py").write_text("class User: pass\n", encoding="utf-8")

    adapters_dir = pkg_core_src / "adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    (adapters_dir / "__init__.py").write_text('"""Adapters."""\n', encoding="utf-8")

    monkeypatch.syspath_prepend(str(pkg_core_src.parent))
    monkeypatch.setenv("PYTHONPATH", str(pkg_core_src.parent))

    # 2. Generate contracts in pyproject.toml
    gen_res = runner.invoke(deps_app, ["linter-generate"])
    assert gen_res.exit_code == 0

    # 2. Verify pyproject.toml has tool.importlinter added
    core_toml = synthetic_workspace / "packages" / "pkg_core" / "pyproject.toml"
    content = core_toml.read_text(encoding="utf-8")
    assert "tool.importlinter" in content

    # 3. Run import linter across pkg_core
    lint_res = runner.invoke(deps_app, ["linter", "-p", "pkg_core"])
    assert lint_res.exit_code == 0


@pytest.mark.integration
def test_deps_linter_detects_violation(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify import-linter detects and fails when an adapter imports infra.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # Create hexagonal layers in pkg_core: adapters and infra
    pkg_core_src = synthetic_workspace / "packages" / "pkg_core" / "src" / "pkg_core"
    domain_dir = pkg_core_src / "domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    (domain_dir / "__init__.py").write_text('"""Domain."""\n', encoding="utf-8")

    adapters_dir = pkg_core_src / "adapters"
    infra_dir = pkg_core_src / "infra"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    infra_dir.mkdir(parents=True, exist_ok=True)

    (infra_dir / "__init__.py").write_text('"""Infra package."""\n', encoding="utf-8")
    (infra_dir / "bus.py").write_text("class InfraBus: pass\n", encoding="utf-8")

    # Adapter violates boundary by importing infra
    (adapters_dir / "__init__.py").write_text(
        "from pkg_core.infra.bus import InfraBus\n", encoding="utf-8"
    )

    monkeypatch.syspath_prepend(str(pkg_core_src.parent))
    monkeypatch.setenv("PYTHONPATH", str(pkg_core_src.parent))

    # Generate contracts
    gen_res = runner.invoke(deps_app, ["linter-generate"])
    assert gen_res.exit_code == 0

    lint_res = runner.invoke(deps_app, ["linter", "-p", "pkg_core"])
    assert lint_res.exit_code != 0


@pytest.mark.integration
def test_deps_audit_command(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify deps audit command executes across dependencies and extras.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)
    res = runner.invoke(deps_app, ["audit", "--extras-only"])
    assert res.exit_code == 0
