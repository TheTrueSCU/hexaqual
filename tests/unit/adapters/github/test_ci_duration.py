"""Unit tests for GitHub CI duration tracking and Mermaid line chart visualization.

Notes/Architectural Intent:
    Verifies GitHub Actions job wall-clock computation, historical trend extraction,
    and Mermaid `xychart-beta` syntax validation with side-effect free assertions.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from hexaqual.adapters.github.ci_duration import (
    CiRunMetric,
    fetch_ci_history,
    fetch_current_run_jobs,
    format_duration,
    generate_ci_duration_markdown,
)


def test_format_duration() -> None:
    """Verify conversion of seconds to human-readable time strings."""
    s1 = format_duration(45)
    assert s1 == "45s"

    s2 = format_duration(125)
    assert s2 == "2m 05s"

    s3 = format_duration(3600)
    assert s3 == "60m 00s"

    s4 = format_duration(0)
    assert s4 == "0s"


def test_generate_ci_duration_markdown() -> None:
    """Verify markdown breakdown and Mermaid chart generation."""
    current_data = {
        "createdAt": "2026-10-26T12:00:00Z",
        "updatedAt": "2026-10-26T12:05:30Z",
        "jobs": [
            {
                "name": "Pre-Commit Quality Gate",
                "status": "completed",
                "conclusion": "success",
                "startedAt": "2026-10-26T12:00:10Z",
                "completedAt": "2026-10-26T12:00:40Z",
            },
            {
                "name": "Unit & Integration Tests",
                "status": "completed",
                "conclusion": "success",
                "startedAt": "2026-10-26T12:00:45Z",
                "completedAt": "2026-10-26T12:04:15Z",
            },
        ],
    }

    history = [
        CiRunMetric(
            run_id="10001",
            label="#10001",
            duration_seconds=360,
            conclusion="success",
            created_at="2026-10-24T12:00:00Z",
        ),
        CiRunMetric(
            run_id="10002",
            label="#10002",
            duration_seconds=330,
            conclusion="success",
            created_at="2026-10-25T12:00:00Z",
        ),
    ]

    md = generate_ci_duration_markdown(current_data, history)
    assert "### ⏱️ CI Pipeline Execution & Duration Breakdown" in md
    assert "`Pre-Commit Quality Gate`" in md
    assert "`Unit & Integration Tests`" in md
    assert "**Total Pipeline Wall-Clock Duration:** `5m 30s`" in md
    assert "xychart-beta" in md
    assert 'title "CI Wall-Clock Duration Trend (Seconds)"' in md
    assert "line [360, 330]" in md


def test_fetch_current_run_jobs_mocked() -> None:
    """Verify querying current run details when gh CLI succeeds."""
    mock_payload = {
        "jobs": [{"name": "Test Job", "status": "completed"}],
        "createdAt": "2026-10-26T10:00:00Z",
        "updatedAt": "2026-10-26T10:02:00Z",
    }
    with patch("shutil.which", return_value="/usr/bin/gh"), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=json.dumps(mock_payload))
        res = fetch_current_run_jobs(run_id="99999")
        assert res is not None
        assert "jobs" in res
        assert len(res["jobs"]) == 1


def test_fetch_ci_history_mocked() -> None:
    """Verify querying CI history and chronological ordering."""
    mock_payload = [
        {
            "databaseId": 20002,
            "createdAt": "2026-10-26T10:00:00Z",
            "updatedAt": "2026-10-26T10:05:00Z",
            "conclusion": "success",
        },
        {
            "databaseId": 20001,
            "createdAt": "2026-10-25T10:00:00Z",
            "updatedAt": "2026-10-25T10:06:00Z",
            "conclusion": "success",
        },
    ]
    with patch("shutil.which", return_value="/usr/bin/gh"), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=json.dumps(mock_payload))
        runs = fetch_ci_history(workflow="CI", branch="main", limit=5)
        # Oldest should be first after chronological reverse
        assert len(runs) == 2
        assert runs[0].run_id == "20001"
        assert runs[0].duration_seconds == 360
        assert runs[1].run_id == "20002"
        assert runs[1].duration_seconds == 300


def test_gh_cli_unavailable() -> None:
    """Verify graceful fallback when gh CLI is missing from PATH."""
    with patch("shutil.which", return_value=None):
        run_res = fetch_current_run_jobs(run_id="12345")
        assert run_res is None

        hist_res = fetch_ci_history()
        assert hist_res == []


def test_in_progress_ci_success_resolution() -> None:
    """Verify in-progress CI Success job resolves to passed status with non-zero duration."""
    current_data = {
        "createdAt": "2026-10-26T12:00:00Z",
        "updatedAt": "2026-10-26T12:02:00Z",
        "status": "in_progress",
        "jobs": [
            {
                "name": "Pre-Commit Quality Gate",
                "status": "completed",
                "conclusion": "success",
                "startedAt": "2026-10-26T12:00:05Z",
                "completedAt": "2026-10-26T12:00:35Z",
            },
            {
                "name": "CI Success (All Required Checks)",
                "status": "in_progress",
                "conclusion": None,
                "startedAt": "2026-10-26T12:01:40Z",
                "completedAt": None,
            },
        ],
    }

    md = generate_ci_duration_markdown(current_data)
    assert "`CI Success (All Required Checks)`" in md
    assert "✅ Passed" in md
    assert "⏳ In_progress" not in md
    assert "#### 🗺️ Executed CI Workflow Graph" in md
    assert "ci_success__all_required_checks" in md
    assert ":::passed" in md
