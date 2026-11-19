"""Unit tests for the standalone .github/actions/mutate-plan/plan.py script."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def _load_plan_module() -> ModuleType:
    """Load the standalone mutate-plan/plan.py script as a Python module."""
    repo_root = Path(__file__).resolve().parents[4]
    script_path = repo_root / ".github" / "actions" / "mutate-plan" / "plan.py"
    spec = importlib.util.spec_from_file_location("mutate_plan_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_file_slices_lpt_balancing_and_heavy_isolation(tmp_path: Path) -> None:
    """Verify build_file_slices isolates oversized files and balances the rest."""
    plan_mod = _load_plan_module()
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "huge.py").write_text(
        "\n".join(f"x_{i} = {i} + 1 if {i} > 0 else 0" for i in range(120)),
        encoding="utf-8",
    )
    (pkg / "med.py").write_text(
        "\n".join(f"y_{i} = {i} + 1" for i in range(30)),
        encoding="utf-8",
    )
    (pkg / "small.py").write_text("z = 1 + 2\n", encoding="utf-8")

    slices = plan_mod.build_file_slices(root=tmp_path / "src", num_slices=4, max_slice_weight=450)
    assert len(slices) == 2
    assert slices[0]["name"] == "slice-01"
    assert slices[0]["targets"].endswith("huge.py")
    assert "," not in slices[0]["targets"]
    assert "med.py" in slices[1]["targets"]
    assert "small.py" in slices[1]["targets"]


def test_discover_affected_and_all_packages_lpt_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify affected and all workspace packages are ordered heaviest-first."""
    plan_mod = _load_plan_module()
    packages = tmp_path / "packages"
    for name, count in (("pkg_small", 5), ("pkg_large", 60)):
        src_dir = packages / name / "src" / name
        src_dir.mkdir(parents=True)
        (packages / name / "pyproject.toml").write_text(
            f'[project]\nname = "{name.replace("_", "-")}"\n',
            encoding="utf-8",
        )
        (src_dir / "mod.py").write_text(
            "\n".join(f"a_{i} = {i} + 1" for i in range(count)),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        plan_mod,
        "_changed_files",
        lambda _base: [
            "packages/pkg_small/src/pkg_small/mod.py",
            "packages/pkg_large/src/pkg_large/mod.py",
        ],
    )

    affected = plan_mod.discover_affected_packages(base_ref="main", packages_root=packages)
    assert affected == ["pkg-large", "pkg-small"]

    all_pkgs = plan_mod.discover_all_packages(packages_root=packages)
    assert all_pkgs == ["pkg-large", "pkg-small"]


def test_main_writes_github_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify main writes matrix and has_affected to GITHUB_OUTPUT."""
    plan_mod = _load_plan_module()
    out_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
    packages = tmp_path / "packages"
    src_dir = packages / "core" / "src" / "core"
    src_dir.mkdir(parents=True)
    (packages / "core" / "pyproject.toml").write_text(
        '[project]\nname = "core"\n', encoding="utf-8"
    )
    (src_dir / "app.py").write_text("x = 1 + 2\n", encoding="utf-8")

    rc = plan_mod.main(["--mode", "all", "--packages-root", str(packages)])
    assert rc == 0
    content = out_file.read_text(encoding="utf-8")
    assert f"matrix={json.dumps({'package': ['core']})}" in content
    assert "has_affected=true" in content


def test_build_changed_slices_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify changed-slices mode partitions only changed files per package in LPT order."""
    plan_mod = _load_plan_module()
    packages = tmp_path / "packages"
    src_dir = packages / "srv" / "src" / "srv"
    src_dir.mkdir(parents=True)
    (packages / "srv" / "pyproject.toml").write_text('[project]\nname = "srv"\n', encoding="utf-8")
    (src_dir / "a.py").write_text(
        "\n".join(f"x_{i} = {i} + 1" for i in range(100)), encoding="utf-8"
    )
    (src_dir / "b.py").write_text("y = 1 + 2\n", encoding="utf-8")
    (src_dir / "untouched.py").write_text("\n".join(["z = 1"] * 500), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        plan_mod,
        "_changed_files",
        lambda _base: ["packages/srv/src/srv/a.py", "packages/srv/src/srv/b.py"],
    )

    matrix_obj, has_affected = plan_mod.plan_mutation_matrix(
        "changed-slices",
        base_ref="main",
        packages_root=Path("packages"),
        num_slices=4,
        max_slice_weight=450,
    )
    assert has_affected is True
    include = matrix_obj["include"]
    assert isinstance(include, list)
    assert len(include) == 2
    assert include[0]["package"] == "srv"
    assert include[0]["targets"] == "src/srv/a.py"
    assert "untouched.py" not in str(include)
