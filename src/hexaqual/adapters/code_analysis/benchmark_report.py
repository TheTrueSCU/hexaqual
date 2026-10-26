"""Microbenchmark results parser, historical delta tracking, and Mermaid chart generator.

Notes/Architectural Intent:
    Provides adapter logic for transforming pytest-benchmark JSON outputs into
    rich Markdown summary tables and Mermaid `xychart-beta` line charts for CI
    and GitHub Actions step summaries. Tracks historical medians to surface regressions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "BenchmarkComparison",
    "BenchmarkHistoryEntry",
    "BenchmarkMetric",
    "format_latency",
    "generate_benchmark_markdown",
    "load_benchmark_results",
    "load_or_update_history",
]


@dataclass(frozen=True)
class BenchmarkMetric:
    """Parsed microbenchmark measurement record."""

    name: str
    median: float
    mean: float
    min: float
    max: float
    stddev: float
    ops: float
    rounds: int


@dataclass(frozen=True)
class BenchmarkComparison:
    """Comparison between current benchmark metric and baseline."""

    metric: BenchmarkMetric
    baseline_median: float | None
    delta_percent: float | None
    status: str


@dataclass(frozen=True)
class BenchmarkHistoryEntry:
    """Historical benchmark run record."""

    timestamp: str
    label: str
    commit: str | None
    run_id: str | None
    benchmarks: dict[str, float]


def format_latency(seconds: float) -> str:
    """Format latency in seconds into human-readable engineering units (ns, µs, ms, s).

    Args:
        seconds: Duration in fractional seconds.

    Returns:
        Formatted latency string with unit suffix.
    """
    if seconds < 1e-6:
        return f"{seconds * 1e9:.2f} ns"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.2f} µs"
    if seconds < 1.0:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds:.2f} s"


def load_benchmark_results(json_path: Path) -> list[BenchmarkMetric]:
    """Parse pytest-benchmark JSON output file.

    Args:
        json_path: Path to pytest-benchmark JSON output.

    Returns:
        List of parsed BenchmarkMetric instances.

    Raises:
        FileNotFoundError: If benchmark results file does not exist.
        ValueError: If JSON structure is missing benchmark data.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"Benchmark results file not found at: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    benchmarks_data = data.get("benchmarks", [])
    if not isinstance(benchmarks_data, list):
        raise ValueError("Invalid benchmark JSON: 'benchmarks' key must be a list.")

    metrics: list[BenchmarkMetric] = []
    for item in benchmarks_data:
        stats = item.get("stats", {})
        metrics.append(
            BenchmarkMetric(
                name=item.get("name", "unknown"),
                median=float(stats.get("median", 0.0)),
                mean=float(stats.get("mean", 0.0)),
                min=float(stats.get("min", 0.0)),
                max=float(stats.get("max", 0.0)),
                stddev=float(stats.get("stddev", 0.0)),
                ops=float(stats.get("ops", 0.0)),
                rounds=int(stats.get("rounds", 0)),
            )
        )
    return metrics


def _evaluate_benchmark_delta(
    metric: BenchmarkMetric,
    baseline_median: float | None,
) -> BenchmarkComparison:
    """Evaluate delta percentage and status badge against baseline."""
    if baseline_median is None or baseline_median <= 0:
        return BenchmarkComparison(
            metric=metric,
            baseline_median=None,
            delta_percent=None,
            status="🟢 Baseline",
        )

    delta_pct = ((metric.median - baseline_median) / baseline_median) * 100.0
    if delta_pct < -5.0:
        status = f"🟢 Faster ({delta_pct:.1f}%)"
    elif delta_pct > 5.0:
        status = f"🔴 Slower (+{delta_pct:.1f}%)"
    else:
        prefix = "+" if delta_pct > 0 else ""
        status = f"🟡 Steady ({prefix}{delta_pct:.1f}%)"

    return BenchmarkComparison(
        metric=metric,
        baseline_median=baseline_median,
        delta_percent=delta_pct,
        status=status,
    )


def _resolve_run_label(
    commit_sha: str | None,
    run_id: str | None,
    run_index: int,
) -> str:
    """Format human-readable label for historical benchmark run."""
    if commit_sha:
        return f"#{commit_sha[:7]}"
    if run_id:
        return f"#{run_id[-5:]}"
    return f"Run {run_index}"


def load_or_update_history(
    history_path: Path,
    current_metrics: list[BenchmarkMetric],
    commit_sha: str | None = None,
    run_id: str | None = None,
    max_history: int = 10,
) -> tuple[dict[str, Any], list[BenchmarkComparison]]:
    """Load historical benchmark records, append current run, and compute comparisons.

    Args:
        history_path: Path to JSON history file.
        current_metrics: List of current benchmark metrics.
        commit_sha: Optional Git commit hash.
        run_id: Optional CI run identifier.
        max_history: Maximum historical records to retain.

    Returns:
        Tuple of (updated history dict, list of BenchmarkComparison instances).
    """
    history_data: dict[str, Any] = {"runs": []}
    if history_path.exists():
        try:
            with history_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "runs" in loaded:
                    history_data = loaded
        except Exception:
            history_data = {"runs": []}

    runs: list[dict[str, Any]] = history_data.get("runs", [])

    baseline_run: dict[str, Any] | None = runs[-1] if runs else None
    baseline_benchmarks: dict[str, float] = (
        baseline_run.get("benchmarks", {}) if baseline_run else {}
    )

    comparisons: list[BenchmarkComparison] = []
    current_benchmarks_map: dict[str, float] = {}

    for m in current_metrics:
        current_benchmarks_map[m.name] = m.median
        base_median = baseline_benchmarks.get(m.name)
        comp = _evaluate_benchmark_delta(metric=m, baseline_median=base_median)
        comparisons.append(comp)

    now_iso = datetime.now(UTC).isoformat()
    label = _resolve_run_label(commit_sha=commit_sha, run_id=run_id, run_index=len(runs) + 1)

    new_run = {
        "timestamp": now_iso,
        "label": label,
        "commit": commit_sha,
        "run_id": run_id,
        "benchmarks": current_benchmarks_map,
    }
    runs.append(new_run)
    if len(runs) > max_history:
        runs = runs[-max_history:]
    history_data["runs"] = runs

    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2)

    return history_data, comparisons


def _build_mermaid_line_chart(
    benchmark_name: str,
    runs: list[dict[str, Any]],
) -> str:
    """Generate a Mermaid `xychart-beta` line chart for a single benchmark over time.

    Args:
        benchmark_name: Name of the microbenchmark.
        runs: List of historical run dictionaries.

    Returns:
        Formatted Mermaid diagram wrapped in a <details> toggle, or empty string if < 2 points.
    """
    points: list[float] = []
    labels: list[str] = []

    for i, r in enumerate(runs):
        val = r.get("benchmarks", {}).get(benchmark_name)
        if val is not None and isinstance(val, (int, float)):
            points.append(float(val))
            labels.append(r.get("label", f"Run {i + 1}"))

    if len(points) < 2:
        return ""

    max_val = max(points)
    if max_val < 1e-6:
        unit = "ns"
        scale = 1e9
    elif max_val < 1e-3:
        unit = "µs"
        scale = 1e6
    elif max_val < 1.0:
        unit = "ms"
        scale = 1e3
    else:
        unit = "s"
        scale = 1.0

    scaled_points = [round(p * scale, 2) for p in points]
    min_y = max(0, int(min(scaled_points) * 0.8))
    max_y = int(max(scaled_points) * 1.2) + 1

    chart = (
        f"<details>\n"
        f"<summary>📈 Latency Trend: <code>{benchmark_name}</code></summary>\n\n"
        f"```mermaid\n"
        f"xychart-beta\n"
        f'    title "{benchmark_name} Median Latency ({unit})"\n'
        f"    x-axis {json.dumps(labels)}\n"
        f'    y-axis "Latency ({unit})" {min_y} --> {max_y}\n'
        f"    line {scaled_points}\n"
        f"```\n\n"
        f"</details>"
    )
    return chart


def generate_benchmark_markdown(
    comparisons: list[BenchmarkComparison],
    history_runs: list[dict[str, Any]] | None = None,
) -> str:
    """Generate GitHub Flavored Markdown summary report for microbenchmarks.

    Args:
        comparisons: List of benchmark comparison records.
        history_runs: Optional list of historical runs for trend charting.

    Returns:
        Markdown string suitable for $GITHUB_STEP_SUMMARY.
    """
    lines: list[str] = []
    lines.append("### ⏱️ Performance Microbenchmark Report")
    lines.append("")
    lines.append(
        "| Benchmark | Median Latency | Baseline | Δ Shift | Status | Ops / Sec | Rounds |"
    )
    lines.append("|---|---|---|---|---|---|---|")

    for comp in comparisons:
        m = comp.metric
        med_str = f"**{format_latency(m.median)}**"
        base_str = format_latency(comp.baseline_median) if comp.baseline_median else "—"
        if comp.delta_percent is not None:
            prefix = "+" if comp.delta_percent > 0 else ""
            delta_str = f"{prefix}{comp.delta_percent:.1f}%"
        else:
            delta_str = "—"

        ops_str = f"{m.ops:,.1f}"
        lines.append(
            f"| `{m.name}` | {med_str} | {base_str} | {delta_str} | {comp.status} | {ops_str} ops/s | {m.rounds} |"
        )

    lines.append("")

    if history_runs and len(history_runs) >= 2:
        lines.append("#### 📈 Microbenchmark Latency Trends Over Time")
        lines.append("")
        charts: list[str] = []
        for comp in comparisons:
            chart = _build_mermaid_line_chart(comp.metric.name, history_runs)
            if chart:
                charts.append(chart)

        if charts:
            lines.extend(charts)
            lines.append("")

    return "\n".join(lines)
