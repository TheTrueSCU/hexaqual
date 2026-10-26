"""Unit tests for microbenchmark reporting and Mermaid chart generation.

Notes/Architectural Intent:
    Verifies parser extraction, human-readable latency formatting, historical baseline
    comparisons, delta thresholding, and Mermaid `xychart-beta` line chart synthesis.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hexaqual.adapters.code_analysis.benchmark_report import (
    BenchmarkMetric,
    format_latency,
    generate_benchmark_markdown,
    load_benchmark_results,
    load_or_update_history,
)


def test_format_latency() -> None:
    """Verify latency formatting across engineering time orders of magnitude."""
    ns_res = format_latency(0.00000045)
    assert ns_res == "450.00 ns"

    us_res = format_latency(0.000125)
    assert us_res == "125.00 µs"

    ms_res = format_latency(0.0123)
    assert ms_res == "12.30 ms"

    s_res = format_latency(2.54)
    assert s_res == "2.54 s"


def test_load_benchmark_results(tmp_path: Path) -> None:
    """Verify loading and parsing of pytest-benchmark JSON output."""
    sample_json = {
        "benchmarks": [
            {
                "name": "test_perf_fast_op",
                "stats": {
                    "median": 0.00012,
                    "mean": 0.000125,
                    "min": 0.00011,
                    "max": 0.00015,
                    "stddev": 0.000005,
                    "ops": 8000.0,
                    "rounds": 500,
                },
            }
        ]
    }
    bench_file = tmp_path / "bench.json"
    bench_file.write_text(json.dumps(sample_json), encoding="utf-8")

    metrics = load_benchmark_results(bench_file)
    assert len(metrics) == 1

    first = metrics[0]
    assert first.name == "test_perf_fast_op"
    assert first.median == 0.00012
    assert first.rounds == 500
    assert first.ops == 8000.0


def test_load_benchmark_results_errors(tmp_path: Path) -> None:
    """Verify error conditions on non-existent or invalid JSON."""
    missing_file = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        load_benchmark_results(missing_file)

    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text(json.dumps({"benchmarks": "not-a-list"}), encoding="utf-8")
    with pytest.raises(ValueError, match="'benchmarks' key must be a list"):
        load_benchmark_results(invalid_file)


def test_load_or_update_history(tmp_path: Path) -> None:
    """Verify baseline establishment, subsequent delta tracking, and max history limit."""
    hist_file = tmp_path / "history.json"
    metric1 = BenchmarkMetric(
        name="test_op",
        median=0.00020,
        mean=0.00021,
        min=0.00019,
        max=0.00025,
        stddev=0.00001,
        ops=5000.0,
        rounds=100,
    )

    # First run establishes baseline
    hist_data1, comps1 = load_or_update_history(
        history_path=hist_file,
        current_metrics=[metric1],
        commit_sha="abcdef123456",
        max_history=3,
    )
    assert len(hist_data1["runs"]) == 1
    assert comps1[0].status == "🟢 Baseline"
    assert comps1[0].delta_percent is None

    # Second run with 15% speed improvement
    metric2 = BenchmarkMetric(
        name="test_op",
        median=0.00017,
        mean=0.00018,
        min=0.00016,
        max=0.00020,
        stddev=0.00001,
        ops=5882.0,
        rounds=100,
    )
    hist_data2, comps2 = load_or_update_history(
        history_path=hist_file,
        current_metrics=[metric2],
        commit_sha="bcdefa123456",
        max_history=3,
    )
    assert len(hist_data2["runs"]) == 2
    assert "🟢 Faster" in comps2[0].status
    assert comps2[0].delta_percent is not None
    assert comps2[0].delta_percent < -5.0

    # Third run with 20% slowdown
    metric3 = BenchmarkMetric(
        name="test_op",
        median=0.00021,
        mean=0.00022,
        min=0.00019,
        max=0.00025,
        stddev=0.00001,
        ops=4700.0,
        rounds=100,
    )
    hist_data3, comps3 = load_or_update_history(
        history_path=hist_file,
        current_metrics=[metric3],
        commit_sha="cdefab123456",
        max_history=3,
    )
    assert len(hist_data3["runs"]) == 3
    assert "🔴 Slower" in comps3[0].status

    # Fourth run overflows max_history=3
    metric4 = BenchmarkMetric(
        name="test_op",
        median=0.00021,
        mean=0.00022,
        min=0.00019,
        max=0.00025,
        stddev=0.00001,
        ops=4700.0,
        rounds=100,
    )
    hist_data4, comps4 = load_or_update_history(
        history_path=hist_file,
        current_metrics=[metric4],
        commit_sha="defabc123456",
        max_history=3,
    )
    assert len(hist_data4["runs"]) == 3
    assert "🟡 Steady" in comps4[0].status


def test_generate_benchmark_markdown_with_charts() -> None:
    """Verify markdown report rendering including Mermaid xychart-beta diagrams."""
    metric = BenchmarkMetric(
        name="test_fast_call",
        median=0.00015,
        mean=0.00016,
        min=0.00014,
        max=0.00018,
        stddev=0.00001,
        ops=6666.0,
        rounds=200,
    )
    comps = [
        load_or_update_history(
            history_path=Path("/tmp/non_existent_test_hist.json"),
            current_metrics=[metric],
        )[1][0]
    ]

    history_runs = [
        {"label": "#11111", "benchmarks": {"test_fast_call": 0.00018}},
        {"label": "#22222", "benchmarks": {"test_fast_call": 0.00015}},
    ]

    markdown = generate_benchmark_markdown(comparisons=comps, history_runs=history_runs)
    assert "### ⏱️ Performance Microbenchmark Report" in markdown
    assert "`test_fast_call`" in markdown
    assert "xychart-beta" in markdown
    assert 'title "test_fast_call Median Latency (µs)"' in markdown
    assert "line [180.0, 150.0]" in markdown
