"""Unit tests for analysis CQRS command handlers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.domain.analysis import (
    FuzzRunCommand,
    ScanCodeQlCommand,
    UpdateInlineSnapshotsCommand,
)
from hexaqual.infra.handlers.analysis import (
    FuzzRunHandler,
    ScanCodeQlHandler,
    UpdateInlineSnapshotsHandler,
)


def test_scan_codeql_handler_cli_not_found(tmp_path: Path) -> None:
    """Verify ScanCodeQlHandler handles missing codeql CLI gracefully."""
    handler = ScanCodeQlHandler(root=tmp_path)
    with (
        patch("shutil.which", return_value=None),
        patch("pathlib.Path.is_file", return_value=False),
    ):
        report = handler.handle(ScanCodeQlCommand())
        assert report.is_successful is True
        assert "not found" in (report.error_message or "")


def test_scan_codeql_handler_success(tmp_path: Path) -> None:
    """Verify ScanCodeQlHandler executes database creation and analysis."""
    handler = ScanCodeQlHandler(root=tmp_path)
    sarif_data = {
        "runs": [
            {
                "results": [
                    {"level": "warning", "message": {"text": "warn"}},
                    {"level": "error", "message": {"text": "err"}},
                ]
            }
        ]
    }
    sarif_file = tmp_path / "out.sarif"
    sarif_file.write_text(json.dumps(sarif_data), encoding="utf-8")

    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stderr = ""

    with (
        patch("shutil.which", return_value="/bin/codeql"),
        patch("subprocess.run", return_value=mock_run),
    ):
        report = handler.handle(ScanCodeQlCommand(output_sarif=sarif_file))
        assert report.is_successful is True
        assert report.findings_count == 2
        assert report.critical_count == 1


def test_fuzz_run_handler(tmp_path: Path) -> None:
    """Verify FuzzRunHandler delegates to fuzz harness runner and aggregates results."""
    handler = FuzzRunHandler(root=tmp_path)
    mock_metrics = [
        {
            "target": "sanitizer",
            "engine": "atheris",
            "runs": 100,
            "duration_seconds": 0.5,
            "crashes": 0,
            "redos_violations": 0,
            "passed": True,
        }
    ]
    with patch(
        "hexaqual.infra.handlers.analysis.run_target_fuzz",
        return_value=mock_metrics,
    ):
        report = handler.handle(FuzzRunCommand(target="sanitizer", runs=100))
        assert report.all_passed is True
        assert len(report.results) == 1
        assert report.results[0].target == "sanitizer"


def test_update_inline_snapshots_handler(tmp_path: Path) -> None:
    """Verify UpdateInlineSnapshotsHandler invokes snapshot runner."""
    target = tmp_path / "packages" / "core"
    target.mkdir(parents=True)
    handler = UpdateInlineSnapshotsHandler(root=tmp_path)

    with patch(
        "hexaqual.infra.handlers.analysis.run_snapshot_update_for_dir",
        return_value=0,
    ):
        report = handler.handle(UpdateInlineSnapshotsCommand(mode="fix", targets=(target,)))
        assert report.exit_code == 0
        assert len(report.targets_updated) == 1


def test_load_fuzz_module_dynamic_discovery(tmp_path: Path) -> None:
    """Verify _load_fuzz_module discovers colocated fuzz harness in packages/*/tests/fuzz."""
    from hexaqual.infra.handlers.analysis import _load_fuzz_module

    fuzz_dir = tmp_path / "packages" / "pkg_a" / "tests" / "fuzz"
    fuzz_dir.mkdir(parents=True)
    harness_file = fuzz_dir / "test_fuzz_custom_sanitizer.py"
    harness_file.write_text(
        "def run_standalone(runs=5):\n    return {'runs': runs, 'target': 'custom', 'passed': True}\n",
        encoding="utf-8",
    )

    mod = _load_fuzz_module(
        name_hints=("custom_sanitizer", "sanitizer"),
        legacy_module="fuzz.non_existent",
        repo_root=tmp_path,
    )
    assert mod is not None
    res = mod.run_standalone(runs=20)
    assert res["target"] == "custom"
    assert res["runs"] == 20


def test_scan_codeql_handler_error_branches(tmp_path: Path) -> None:
    """Verify ScanCodeQlHandler handles create and analyze errors."""
    from hexaqual.infra.handlers.analysis import ScanCodeQlHandler

    handler = ScanCodeQlHandler(root=tmp_path)

    # 1. Database creation failure
    fail_create = MagicMock(returncode=1, stderr="Creation syntax error")
    with (
        patch("shutil.which", return_value="/bin/codeql"),
        patch("subprocess.run", return_value=fail_create),
    ):
        rep = handler.handle(ScanCodeQlCommand(threads=4))
        assert rep.is_successful is False
        assert "database creation failed" in (rep.error_message or "").lower()

    # 2. Query analysis failure
    ok_create = MagicMock(returncode=0, stderr="")
    fail_analyze = MagicMock(returncode=1, stderr="Query execution timeout")
    with (
        patch("shutil.which", return_value="/bin/codeql"),
        patch("subprocess.run", side_effect=[ok_create, fail_analyze]),
    ):
        rep = handler.handle(ScanCodeQlCommand(threads=2))
        assert rep.is_successful is False
        assert "query execution failed" in (rep.error_message or "").lower()


def test_run_snapshot_update_for_dir(tmp_path: Path) -> None:
    """Verify run_snapshot_update_for_dir verifies paths and executes pytest."""
    from hexaqual.infra.handlers.analysis import run_snapshot_update_for_dir

    # 1. Nonexistent directory returns 1
    assert run_snapshot_update_for_dir(tmp_path / "missing", mode="fix") == 1

    # 2. Existing directory runs pytest
    target = tmp_path / "tests"
    target.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        code = run_snapshot_update_for_dir(target, mode="fix", root_dir=tmp_path)
        assert code == 0
        assert mock_run.called


def test_run_target_fuzz_unknown_target() -> None:
    """Verify run_target_fuzz raises ValueError for unknown target."""
    import pytest

    from hexaqual.infra.handlers.analysis import run_target_fuzz

    with pytest.raises(ValueError, match="Unknown fuzz target"):
        run_target_fuzz(target="invalid_target_xyz", runs=10)


def test_run_target_fuzz_valid_targets() -> None:
    """Verify run_target_fuzz executes sanitizer, proto, and owasp targets."""
    from hexaqual.infra.handlers.analysis import run_target_fuzz

    mock_mod = MagicMock()
    mock_mod.run_standalone.return_value = {"runs": 10, "passed": True}

    with (
        patch("hexaqual.infra.handlers.analysis._load_fuzz_module", return_value=mock_mod),
        patch(
            "hexaqual.infra.handlers.analysis._run_owasp_target",
            return_value={"runs": 10, "passed": True},
        ),
    ):
        res_san = run_target_fuzz(target="sanitizer", runs=10, engine="standalone")
        assert len(res_san) == 1
        assert res_san[0]["passed"] is True

        res_proto = run_target_fuzz(target="proto", runs=10, engine="standalone")
        assert len(res_proto) == 1

        res_owasp = run_target_fuzz(target="owasp", runs=10)
        assert len(res_owasp) == 1
