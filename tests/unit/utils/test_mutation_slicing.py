"""Unit tests for AST-weighted, capacity-capped LPT mutation slicing and planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from hexaqual.utils import mutation_slicing as slicing_mod


def test_estimate_ast_mutation_weight_ignores_docstrings() -> None:
    """Verify AST weighting counts mutable operators and ignores docstrings."""
    doc_heavy = '"""' + ("long docstring line\n" * 100) + '"""\nx = 1\n'
    logic_heavy = "\n".join(f"if a_{i} > {i} and b_{i} + 1 == {i}: return {i}" for i in range(20))

    doc_weight = slicing_mod.estimate_ast_mutation_weight(doc_heavy)
    logic_weight = slicing_mod.estimate_ast_mutation_weight(logic_heavy)
    assert logic_weight > doc_weight * 10


def test_estimate_ast_mutation_weight_syntax_error_fallback() -> None:
    """Verify invalid Python source falls back to line count."""
    broken = "def broken(:\n    pass\n"
    weight = slicing_mod.estimate_ast_mutation_weight(broken)
    assert weight == 2


def test_estimate_file_mutation_weight_missing_file(tmp_path: Path) -> None:
    """Verify missing files return baseline per-file overhead."""
    missing = tmp_path / "does_not_exist.py"
    weight = slicing_mod.estimate_file_mutation_weight(missing)
    assert weight == 5


def test_partition_targets_lpt_isolates_heavy_files_and_expands_slices() -> None:
    """Verify oversized files run solo and remaining files expand under cap."""
    items = [
        (700, "adapters/local.py"),
        (320, "adapters/api/test_runs.py"),
        (280, "domain/lease_coordinator.py"),
        (260, "adapters/storage/oracle.py"),
        (200, "domain/config.py"),
        (150, "adapters/db/analytics.py"),
        (120, "domain/placement.py"),
    ]
    slices = slicing_mod.partition_targets_lpt(
        items, min_slices=1, max_slices=12, max_slice_weight=450
    )

    assert len(slices) >= 4
    first_weight, first_paths = slices[0]
    assert first_weight == 700
    assert first_paths == ["adapters/local.py"]
    weights = [w for w, _ in slices]
    assert weights == sorted(weights, reverse=True)
    all_paths = [p for _, paths in slices for p in paths]
    assert sorted(all_paths) == sorted(p for _, p in items)


def test_build_file_slices_lpt_balancing_and_heavy_isolation(tmp_path: Path) -> None:
    """Verify build_file_slices isolates oversized files and balances the rest."""
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

    slices = slicing_mod.build_file_slices(
        root=tmp_path / "src", num_slices=4, max_slice_weight=450
    )
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
        slicing_mod,
        "_changed_files",
        lambda _base: [
            "packages/pkg_small/src/pkg_small/mod.py",
            "packages/pkg_large/src/pkg_large/mod.py",
        ],
    )

    affected = slicing_mod.discover_affected_packages(base_ref="main", packages_root=packages)
    assert affected == ["pkg-large", "pkg-small"]

    all_pkgs = slicing_mod.discover_all_packages(packages_root=packages)
    assert all_pkgs == ["pkg-large", "pkg-small"]


def test_build_changed_slices_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify changed-slices mode partitions only changed files per package in LPT order."""
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
        slicing_mod,
        "_changed_files",
        lambda _base: ["packages/srv/src/srv/a.py", "packages/srv/src/srv/b.py"],
    )

    matrix_obj, has_affected = slicing_mod.plan_mutation_matrix(
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
