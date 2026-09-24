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
