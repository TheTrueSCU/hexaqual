"""GitHub Actions CI run duration analyzer and Mermaid trend visualizer.

Notes/Architectural Intent:
    Queries GitHub CLI (`gh`) for real-time workflow job durations and historical
    wall-clock run times on the primary branch. Generates Markdown summary tables
    and Mermaid `xychart-beta` line charts for CI step summaries and regression alerts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "CiJobMetric",
    "CiRunMetric",
    "fetch_ci_history",
    "fetch_current_run_jobs",
    "format_duration",
    "generate_ci_duration_markdown",
]


@dataclass(frozen=True)
class CiJobMetric:
    """Parsed GitHub Actions job execution record."""

    name: str
    duration_seconds: int
    status: str
    conclusion: str


@dataclass(frozen=True)
class CiRunMetric:
    """Historical CI workflow run execution record."""

    run_id: str
    label: str
    duration_seconds: int
    conclusion: str
    created_at: str


def format_duration(seconds: float) -> str:
    """Format duration in seconds into human-readable minutes and seconds.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string (e.g. '45s', '3m 12s').
    """
    total_secs = max(0, int(seconds))
    mins = total_secs // 60
    secs = total_secs % 60
    if mins > 0:
        return f"{mins}m {secs:02d}s"
    return f"{secs}s"


def _parse_iso(timestamp_str: str) -> datetime:
    """Parse ISO 8601 UTC timestamp string."""
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


def fetch_current_run_jobs(run_id: str | None = None) -> dict[str, Any] | None:
    """Query GitHub CLI for current workflow execution details.

    Args:
        run_id: Optional GitHub Actions run databaseId. Defaults to GITHUB_RUN_ID env var.

    Returns:
        Dictionary containing run status, createdAt, updatedAt, and job details, or None on failure.
    """
    if not shutil.which("gh"):
        return None

    target_id = run_id or os.environ.get("GITHUB_RUN_ID")
    if not target_id:
        return None

    cmd = [
        "gh",
        "run",
        "view",
        str(target_id),
        "--json",
        "jobs,createdAt,updatedAt,status,conclusion",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def fetch_ci_history(
    workflow: str = "CI",
    branch: str = "main",
    limit: int = 10,
) -> list[CiRunMetric]:
    """Query GitHub CLI for recent completed CI runs on target branch.

    Args:
        workflow: Workflow name or filename.
        branch: Git branch name.
        limit: Maximum number of recent runs to query.

    Returns:
        List of CiRunMetric instances ordered chronologically (oldest to newest).
    """
    if not shutil.which("gh"):
        return []

    cmd = [
        "gh",
        "run",
        "list",
        f"--workflow={workflow}",
        f"--branch={branch}",
        f"--limit={limit}",
        "--json",
        "databaseId,createdAt,updatedAt,conclusion",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_runs = json.loads(res.stdout)
        if not isinstance(raw_runs, list):
            return []

        runs: list[CiRunMetric] = []
        for r in raw_runs:
            created = r.get("createdAt")
            updated = r.get("updatedAt")
            db_id = str(r.get("databaseId", ""))
            concl = r.get("conclusion") or "unknown"
            if created and updated and db_id:
                try:
                    c_dt = _parse_iso(created)
                    u_dt = _parse_iso(updated)
                    sec = max(0, int((u_dt - c_dt).total_seconds()))
                    runs.append(
                        CiRunMetric(
                            run_id=db_id,
                            label=f"#{db_id[-5:]}",
                            duration_seconds=sec,
                            conclusion=concl,
                            created_at=created,
                        )
                    )
                except Exception:
                    continue

        # gh run list returns newest first; reverse for chronological order
        runs.reverse()
        return runs
    except Exception:
        return []


def _format_job_status_badge(conclusion: str, status: str) -> str:
    """Format job status badge icon and label."""
    if conclusion == "success":
        return "✅ Passed"
    if conclusion in ("failure", "timed_out"):
        return "❌ Failed"
    if conclusion == "skipped":
        return "⏭️ Skipped"
    if conclusion == "cancelled":
        return "🛑 Cancelled"
    return f"⏳ {status.capitalize()}"


def _format_job_duration(started_at: str | None, completed_at: str | None) -> str:
    """Calculate formatted duration string between two ISO timestamps.

    If completed_at is missing or identical to started_at for an in-progress job,
    computes elapsed duration against current UTC timestamp.
    """
    if not started_at:
        return "—"
    try:
        s_dt = _parse_iso(started_at)
        if completed_at:
            c_dt = _parse_iso(completed_at)
            sec = (c_dt - s_dt).total_seconds()
            if sec > 0:
                return format_duration(sec)
        now_dt = datetime.now(UTC)
        elapsed = max(1, int((now_dt - s_dt).total_seconds()))
        return format_duration(elapsed)
    except Exception:
        return "—"


def _calculate_wall_clock(current_run_data: dict[str, Any] | None) -> str | None:
    """Extract total pipeline wall-clock time from workflow run timestamps."""
    if not current_run_data:
        return None
    c_at = current_run_data.get("createdAt")
    u_at = current_run_data.get("updatedAt")
    if not c_at:
        return None
    try:
        status = current_run_data.get("status")
        if status == "in_progress" or not u_at:
            now_dt = datetime.now(UTC)
            sec = max(0, int((now_dt - _parse_iso(c_at)).total_seconds()))
            return format_duration(sec)
        sec = (_parse_iso(u_at) - _parse_iso(c_at)).total_seconds()
        return format_duration(sec)
    except Exception:
        return None


def _extract_workflow_jobs(workflow_path: str) -> dict[str, Any]:
    """Parse workflow YAML definition to retrieve job dependency specifications."""
    if not os.path.isfile(workflow_path):
        return {}
    try:
        import yaml

        with open(workflow_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            raw_jobs = data.get("jobs", {})
            return raw_jobs if isinstance(raw_jobs, dict) else {}
        return {}
    except Exception:
        return {}


def _resolve_job_node_class(conclusion: str, status: str) -> str:
    """Determine Mermaid style class based on job execution outcome."""
    if conclusion == "success":
        return "passed"
    if conclusion in ("failure", "timed_out"):
        return "failed"
    if conclusion == "skipped":
        return "skipped"
    if conclusion == "cancelled":
        return "cancelled"
    return "running"


def _normalize_name(name: str) -> str:
    """Normalize workflow job name for case and matrix key lookups."""
    return re.sub(r"\s+", " ", name.split("(")[0].strip().lower())


def _build_job_key_mapping(jobs_def: dict[str, Any]) -> dict[str, str]:
    """Map normalized job names and IDs to their workflow definition keys."""
    key_by_norm: dict[str, str] = {}
    for k, v in jobs_def.items():
        if isinstance(v, dict):
            key_by_norm[_normalize_name(v.get("name", k))] = k
            key_by_norm[k.lower()] = k
    return key_by_norm


def _render_graph_nodes(
    processed_jobs: list[dict[str, str]],
) -> tuple[list[str], dict[str, str]]:
    """Render Mermaid nodes and record node IDs by job name."""
    node_lines: list[str] = []
    job_node_ids: dict[str, str] = {}
    for j in processed_jobs:
        name = j["name"]
        nid = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_").lower()
        job_node_ids[name] = nid
        cls_name = _resolve_job_node_class(j.get("conclusion", ""), j.get("status", ""))
        dur = j.get("duration", "—")
        node_lines.append(f'    {nid}["{name}<br/><b>{dur}</b>"]:::{cls_name}')
    return node_lines, job_node_ids


def _render_job_edges(
    child_job: dict[str, str],
    processed_jobs: list[dict[str, str]],
    jobs_def: dict[str, Any],
    key_by_norm: dict[str, str],
    job_node_ids: dict[str, str],
    rendered_edges: set[str],
) -> list[str]:
    """Render incoming dependency edges for a specific child job."""
    child_name = child_job["name"]
    child_id = job_node_ids.get(child_name)
    j_key = key_by_norm.get(_normalize_name(child_name))
    if not child_id or not j_key or j_key not in jobs_def:
        return []

    needs = jobs_def[j_key].get("needs", [])
    needs_list = [needs] if isinstance(needs, str) else (needs if isinstance(needs, list) else [])
    edge_lines: list[str] = []
    for p_key in needs_list:
        for pj in processed_jobs:
            if key_by_norm.get(_normalize_name(pj["name"])) == p_key:
                p_id = job_node_ids.get(pj["name"])
                edge_str = f"    {p_id} --> {child_id}"
                if edge_str not in rendered_edges:
                    rendered_edges.add(edge_str)
                    edge_lines.append(edge_str)
    return edge_lines


def _render_execution_graph(
    processed_jobs: list[dict[str, str]],
    workflow_path: str = ".github/workflows/ci.yml",
) -> list[str]:
    """Generate Mermaid flowchart visualizing actual execution outcomes and durations."""
    if not processed_jobs:
        return []

    jobs_def = _extract_workflow_jobs(workflow_path)
    key_by_norm = _build_job_key_mapping(jobs_def)
    node_lines, job_node_ids = _render_graph_nodes(processed_jobs)

    lines = [
        "#### 🗺️ Executed CI Workflow Graph",
        "",
        "```mermaid",
        "flowchart TD",
        *node_lines,
        "",
    ]

    rendered_edges: set[str] = set()
    for j in processed_jobs:
        edges = _render_job_edges(
            j, processed_jobs, jobs_def, key_by_norm, job_node_ids, rendered_edges
        )
        lines.extend(edges)

    lines.extend(
        [
            "",
            "    classDef passed fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724;",
            "    classDef failed fill:#f8d7da,stroke:#dc3545,stroke-width:2px,color:#721c24;",
            "    classDef skipped fill:#e2e3e5,stroke:#6c757d,stroke-width:1px,color:#383d41;",
            "    classDef running fill:#fff3cd,stroke:#ffc107,stroke-width:2px,color:#856404;",
            "    classDef cancelled fill:#f8d7da,stroke:#6c757d,stroke-width:2px,color:#721c24;",
            "```",
            "",
        ]
    )
    return lines


def _render_duration_chart(history_runs: list[CiRunMetric] | None) -> list[str]:
    """Generate Mermaid line chart block for historical CI runs."""
    if not history_runs:
        return []
    successful_runs = [r for r in history_runs if r.conclusion == "success"]
    if len(successful_runs) < 2:
        return []

    x_labels = [r.label for r in successful_runs]
    y_durations = [r.duration_seconds for r in successful_runs]

    min_y = max(0, int(min(y_durations) * 0.8))
    max_y = int(max(y_durations) * 1.2) + 1

    return [
        "#### 📈 CI Duration Trend Over Time (Main Branch)",
        "",
        "```mermaid",
        "xychart-beta",
        '    title "CI Wall-Clock Duration Trend (Seconds)"',
        f"    x-axis {json.dumps(x_labels)}",
        f'    y-axis "Duration (seconds)" {min_y} --> {max_y}',
        f"    line {y_durations}",
        "```",
        "",
    ]


def generate_ci_duration_markdown(
    current_run_data: dict[str, Any] | None,
    history_runs: list[CiRunMetric] | None = None,
    workflow_path: str = ".github/workflows/ci.yml",
) -> str:
    """Generate GitHub Flavored Markdown summary report for CI durations.

    Args:
        current_run_data: Execution data for the current run.
        history_runs: List of historical CI runs for trend line charting.
        workflow_path: Optional path to the workflow YAML file.

    Returns:
        Markdown string suitable for $GITHUB_STEP_SUMMARY.
    """
    lines: list[str] = [
        "### ⏱️ CI Pipeline Execution & Duration Breakdown",
        "",
    ]

    jobs = current_run_data.get("jobs", []) if current_run_data else []
    processed_jobs: list[dict[str, str]] = []
    if jobs:
        lines.extend(["| Job / Stage | Duration | Status |", "|---|---|---|"])
        for j in jobs:
            j_name = j.get("name", "Unknown Job")
            j_status = j.get("status", "unknown")
            j_concl = j.get("conclusion") or j_status
            if j_status == "in_progress" and ("CI Success" in j_name or not j.get("conclusion")):
                j_concl = "success"
                j_status = "completed"
            dur_str = _format_job_duration(j.get("startedAt"), j.get("completedAt"))
            icon = _format_job_status_badge(j_concl, j_status)
            lines.append(f"| `{j_name}` | {dur_str} | {icon} |")
            processed_jobs.append(
                {
                    "name": j_name,
                    "duration": dur_str,
                    "status": j_status,
                    "conclusion": j_concl,
                }
            )
        lines.append("")

    total_wall_clock = _calculate_wall_clock(current_run_data)
    if total_wall_clock:
        lines.extend([f"**Total Pipeline Wall-Clock Duration:** `{total_wall_clock}`", ""])

    graph_lines = _render_execution_graph(processed_jobs, workflow_path=workflow_path)
    if graph_lines:
        lines.extend(graph_lines)

    chart_lines = _render_duration_chart(history_runs)
    if chart_lines:
        lines.extend(chart_lines)

    return "\n".join(lines)
