"""Unit tests for LPT mutation matrix planner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hexaqual.domain import mutation_plan as plan_mod


def test_build_file_slices_lpt_balancing(tmp_path: Path) -> None:
    """Verify build_file_slices balances files into LPT buckets."""
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "big.py").write_text("\n".join(["x = 1"] * 100), encoding="utf-8")
    (pkg / "med.py").write_text("\n".join(["x = 1"] * 60), encoding="utf-8")
    (pkg / "small.py").write_text("\n".join(["x = 1"] * 20), encoding="utf-8")

    slices = plan_mod.build_file_slices(root=tmp_path / "src", num_slices=2)
    assert len(slices) == 2
    assert slices[0]["name"] == "slice-01"
    assert "big.py" in slices[0]["targets"]
    assert "med.py" in slices[1]["targets"]
    assert "small.py" in slices[1]["targets"]


def test_discover_affected_and_all_packages_lpt_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify affected and all workspace packages are ordered largest-first."""
    packages = tmp_path / "packages"
    for name, lines in (("pkg_small", 10), ("pkg_large", 80)):
        src_dir = packages / name / "src" / name
        src_dir.mkdir(parents=True)
        (packages / name / "pyproject.toml").write_text(
            f'[project]\nname = "{name.replace("_", "-")}"\n',
            encoding="utf-8",
        )
        (src_dir / "mod.py").write_text("\n".join(["a = 1"] * lines), encoding="utf-8")

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

    matrix_obj, has_affected = plan_mod.plan_mutation_matrix(
        "slices", root=packages / "pkg_large" / "src", num_slices=2
    )
    assert has_affected is True
    assert "include" in matrix_obj


def test_main_writes_github_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify main writes matrix and has_affected to GITHUB_OUTPUT."""
    out_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
    packages = tmp_path / "packages"
    src_dir = packages / "core" / "src" / "core"
    src_dir.mkdir(parents=True)
    (packages / "core" / "pyproject.toml").write_text(
        '[project]\nname = "core"\n', encoding="utf-8"
    )
    (src_dir / "app.py").write_text("x = 1\n", encoding="utf-8")

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
    packages = tmp_path / "packages"
    src_dir = packages / "srv" / "src" / "srv"
    src_dir.mkdir(parents=True)
    (packages / "srv" / "pyproject.toml").write_text('[project]\nname = "srv"\n', encoding="utf-8")
    f1 = src_dir / "a.py"
    f2 = src_dir / "b.py"
    f3 = src_dir / "untouched.py"
    f1.write_text("\n".join(["x = 1"] * 40), encoding="utf-8")
    f2.write_text("\n".join(["x = 1"] * 10), encoding="utf-8")
    f3.write_text("\n".join(["x = 1"] * 500), encoding="utf-8")

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
        num_slices=2,
    )
    assert has_affected is True
    include = matrix_obj["include"]
    assert isinstance(include, list)
    assert len(include) == 2
    assert include[0]["package"] == "srv"
    assert "untouched.py" not in str(include)
