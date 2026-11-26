"""Integration tests for .github/scripts/aggregate_mutation_summary.py.

Notes/Architectural Intent:
    Verifies multi-slice gremlins.json aggregation, graceful handling of missing
    or malformed slice reports, and CLI output / $GITHUB_STEP_SUMMARY generation
    without depending on third-party packages.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "scripts" / "aggregate_mutation_summary.py"
)


def _load_module() -> ModuleType:
    """Dynamically load aggregate_mutation_summary module from .github/scripts."""
    spec = importlib.util.spec_from_file_location("aggregate_mutation_summary", _SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aggregate_mutation_summary"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.integration
def test_aggregate_reports_multi_slice_and_top_survivors(tmp_path: Path) -> None:
    """Verify multi-slice totals, relative path normalization, and top-15 survivor ordering."""
    mod = _load_module()

    slice1_dir = tmp_path / "mutation-audit-report-slice-01"
    slice1_dir.mkdir(parents=True)
    slice1_files = {
        f"/home/runner/work/hexaqual/hexaqual/src/hexaqual/mod_{idx:02d}.py": {
            "total": 10,
            "zapped": 10 - idx,
            "survived": idx,
        }
        for idx in range(1, 10)
    }
    (slice1_dir / "gremlins.json").write_text(
        json.dumps(
            {
                "summary": {
                    "total": 90,
                    "zapped": 45,
                    "survived": 45,
                    "timeout": 1,
                    "error": 2,
                    "pardoned": 3,
                },
                "files": slice1_files,
            }
        ),
        encoding="utf-8",
    )

    slice2_dir = tmp_path / "mutation-audit-report-slice-02"
    slice2_dir.mkdir(parents=True)
    slice2_files = {
        f"/home/runner/work/hexaqual/hexaqual/src/hexaqual/mod_{idx:02d}.py": {
            "total": 20,
            "zapped": 20 - idx,
            "survived": idx,
        }
        for idx in range(10, 19)
    }
    # Overlapping file from slice 1 to confirm per-file accumulation across slices
    slice2_files["/runner/repo/src/hexaqual/mod_01.py"] = {
        "total": 10,
        "zapped": 8,
        "survived": 2,
    }
    (slice2_dir / "gremlins.json").write_text(
        json.dumps(
            {
                "summary": {
                    "total": 190,
                    "zapped": 62,
                    "survived": 128,
                    "timeout": 0,
                    "error": 1,
                    "pardoned": 0,
                },
                "files": slice2_files,
            }
        ),
        encoding="utf-8",
    )

    report = mod.aggregate_reports(tmp_path)
    assert "- **Slices Aggregated**: 2" in report
    assert "- **Total Gremlins**: 280" in report
    assert "- **Zapped**: 107 (38.2%)" in report
    assert "- **Survived**: 173" in report
    assert "- **Timeout / Error / Pardoned**: 1 / 3 / 3" in report
    assert "`src/hexaqual/mod_18.py`" in report
    # Only top 15 surviving files are displayed (18 files have survived > 0)
    table_rows = [line for line in report.splitlines() if line.startswith("| `src/")]
    row_count = len(table_rows)
    assert row_count == 15


@pytest.mark.integration
def test_aggregate_reports_missing_and_corrupt_slices(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify missing artifacts dir and corrupt JSON reports degrade gracefully."""
    mod = _load_module()

    missing_dir = tmp_path / "does-not-exist"
    missing_report = mod.aggregate_reports(missing_dir)
    assert "- **Slices Aggregated**: 0" in missing_report
    assert "does not exist" in missing_report

    good_dir = tmp_path / "artifacts" / "slice-01"
    bad_dir = tmp_path / "artifacts" / "slice-02"
    good_dir.mkdir(parents=True)
    bad_dir.mkdir(parents=True)
    (good_dir / "gremlins.json").write_text(
        json.dumps(
            {
                "summary": {
                    "total": 10,
                    "zapped": 9,
                    "survived": 1,
                    "timeout": 0,
                    "error": 0,
                    "pardoned": 0,
                },
                "files": {"/repo/src/hexaqual/ok.py": {"total": 10, "zapped": 9, "survived": 1}},
            }
        ),
        encoding="utf-8",
    )
    (bad_dir / "gremlins.json").write_text("{not valid json", encoding="utf-8")

    partial_report = mod.aggregate_reports(tmp_path / "artifacts")
    captured = capsys.readouterr()
    assert "- **Slices Aggregated**: 1" in partial_report
    assert "- **Total Gremlins**: 10" in partial_report
    assert "Skipped 1 malformed report(s)" in partial_report
    assert "skipping malformed mutation report" in captured.err


@pytest.mark.integration
def test_main_writes_stdout_output_file_and_step_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify CLI main emits status header, output file, stdout, and GITHUB_STEP_SUMMARY."""
    mod = _load_module()

    artifacts_dir = tmp_path / "artifacts"
    slice_dir = artifacts_dir / "slice-01"
    slice_dir.mkdir(parents=True)
    (slice_dir / "gremlins.json").write_text(
        json.dumps(
            {
                "summary": {
                    "total": 4,
                    "zapped": 4,
                    "survived": 0,
                    "timeout": 0,
                    "error": 0,
                    "pardoned": 0,
                },
                "files": {},
            }
        ),
        encoding="utf-8",
    )

    output_file = tmp_path / "out" / "mutation-summary.md"
    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    exit_code = mod.main(
        [
            str(artifacts_dir),
            "--status-discover",
            "success",
            "--status-audit",
            "success",
            "--output",
            str(output_file),
            "--step-summary",
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "### Scheduled Mutation Audit Status" in captured.out
    assert "- **Discover Slices**: success" in captured.out
    assert "- **Mutation Audit**: success" in captured.out
    assert "- **Slices Aggregated**: 1" in captured.out
    assert "Appended" in captured.err

    output_text = output_file.read_text(encoding="utf-8")
    summary_text = summary_file.read_text(encoding="utf-8")
    assert output_text == captured.out
    assert output_text in summary_text
