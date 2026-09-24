"""Unit tests for sanity target resolution adapter."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.adapters.code_analysis.sanity import (
    _create_example_target,
    _create_package_target,
    _detect_git_targets,
    resolve_targets,
)


def test_create_targets(tmp_path: Path) -> None:
    """Verify target factory helpers."""
    pkg_dir = tmp_path / "pkg"
    (pkg_dir / "src").mkdir(parents=True)
    (pkg_dir / "tests").mkdir(parents=True)
    pkg_target = _create_package_target("pkg", pkg_dir)
    assert pkg_target.name == "pkg"
    assert pkg_target.kind == "package"
    assert len(pkg_target.src_paths) == 1

    ex_dir = tmp_path / "ex"
    ex_target = _create_example_target("ex", ex_dir)
    assert ex_target.name == "ex"
    assert ex_target.kind == "example"


def test_resolve_targets_package(tmp_path: Path) -> None:
    """Verify CLI argument resolution for explicit packages."""
    args = argparse.Namespace(
        packages=["cqrs"],
        examples=None,
        files=None,
        all_targets=False,
    )
    with patch(
        "hexaqual.adapters.code_analysis.sanity.get_package_directory",
        return_value=tmp_path / "packages" / "cqrs",
    ):
        targets = resolve_targets(args, tmp_path)
        assert len(targets) == 1
        assert targets[0].name == "cqrs"


def test_detect_git_targets(tmp_path: Path) -> None:
    """Verify git status detection parses changed packages and examples."""
    git_status = " M packages/core/src/foo.py\n?? examples/financial-ledger/src/bar.py\n"
    with (
        patch("subprocess.run") as mock_run,
        patch(
            "hexaqual.adapters.code_analysis.sanity.get_package_directory",
            return_value=tmp_path / "packages" / "core",
        ),
        patch(
            "hexaqual.adapters.code_analysis.sanity.get_example_directory",
            return_value=tmp_path / "examples" / "financial-ledger",
        ),
    ):
        mock_proc = MagicMock()
        mock_proc.stdout = git_status
        mock_run.return_value = mock_proc

        (tmp_path / "packages" / "core").mkdir(parents=True)
        (tmp_path / "examples" / "financial-ledger").mkdir(parents=True)

        targets = _detect_git_targets(tmp_path)
        assert len(targets) == 2
        names = {t.name for t in targets}
        assert "core" in names
        assert "financial-ledger" in names


def test_detect_git_targets_exceptions_and_edge_cases(tmp_path: Path) -> None:
    """Verify git status error handling and invalid line parsing."""
    with patch("subprocess.run", side_effect=OSError("git not found")):
        assert _detect_git_targets(tmp_path) == []

    # Short line and unknown targets
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.stdout = " \n M \n M packages/unknown/mod.py\n M examples/unknown/app.py\n"
        mock_run.return_value = mock_proc
        targets = _detect_git_targets(tmp_path)
        assert targets == []


def test_resolve_targets_all_and_fallback(tmp_path: Path) -> None:
    """Verify resolve_targets with 'all', examples, files, and fallback in multi/single pkg."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "src").mkdir()

    # 1. packages=["all"]
    with patch(
        "hexaqual.adapters.code_analysis.sanity.get_package_directories",
        return_value=[pkg_dir],
    ):
        t1 = resolve_targets(packages=["all"], repo_root=tmp_path)
        assert len(t1) == 1
        assert t1[0].name == "hexastack_core"

    # 2. examples
    ex_dir = tmp_path / "examples" / "sample"
    ex_dir.mkdir(parents=True)
    with patch(
        "hexaqual.adapters.code_analysis.sanity.get_example_directory",
        return_value=ex_dir,
    ):
        t2 = resolve_targets(examples=["sample"], repo_root=tmp_path)
        assert len(t2) == 1
        assert t2[0].name == "sample"
        assert t2[0].kind == "example"

    # 3. files
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("x = 1\n", encoding="utf-8")
    t3 = resolve_targets(files=[str(sample_file)], repo_root=tmp_path)
    assert len(t3) == 1
    assert t3[0].kind == "file"
    assert t3[0].name == "sample.py"

    # 4. all_targets in multipackage workspace
    with (
        patch(
            "hexaqual.adapters.code_analysis.sanity.is_multipackage_workspace", return_value=True
        ),
        patch(
            "hexaqual.adapters.code_analysis.sanity.get_package_directories",
            return_value=[pkg_dir],
        ),
    ):
        t4 = resolve_targets(all_targets=True, repo_root=tmp_path)
        assert len(t4) == 1
        assert t4[0].name == "hexastack_core"

    # 5. all_targets in single package repository
    with patch(
        "hexaqual.adapters.code_analysis.sanity.is_multipackage_workspace", return_value=False
    ):
        t5 = resolve_targets(all_targets=True, repo_root=tmp_path)
        assert len(t5) == 1
        assert t5[0].name == tmp_path.name

    # 6. Fallback in multipackage workspace when git detection is empty
    with (
        patch(
            "hexaqual.adapters.code_analysis.sanity.is_multipackage_workspace", return_value=True
        ),
        patch("hexaqual.adapters.code_analysis.sanity._detect_git_targets", return_value=[]),
        patch(
            "hexaqual.adapters.code_analysis.sanity.get_package_directories",
            return_value=[pkg_dir],
        ),
    ):
        t6 = resolve_targets(repo_root=tmp_path)
        assert len(t6) == 1
        assert t6[0].name == "hexastack_core"

    # 7. Fallback in single package workspace
    with (
        patch(
            "hexaqual.adapters.code_analysis.sanity.is_multipackage_workspace", return_value=False
        ),
    ):
        t7 = resolve_targets(repo_root=tmp_path)
        assert len(t7) == 1
        assert t7[0].name == tmp_path.name
