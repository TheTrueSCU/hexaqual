"""Performance microbenchmarks for Hexaqual quality and governance components.

Notes/Architectural Intent:
    Measures sub-millisecond execution latency of sanity template binding and gate audits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hexaqual.adapters.code_analysis.gate_inventory import audit_gate_inventory
from hexaqual.adapters.workspace import get_repo_root
from hexaqual.cli.check import _build_sanity_template_workflow

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


def test_perf_sanity_template_construction(benchmark: BenchmarkFixture) -> None:
    """Benchmark sanity pipeline template DAG construction latency.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies workflow instantiation and stage registration latency.
    """
    wf = benchmark(_build_sanity_template_workflow)
    assert wf.name == "sanity_template"


def test_perf_gate_inventory_audit(benchmark: BenchmarkFixture) -> None:
    """Benchmark canonical gate inventory reflection and verification.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies quality gate inventory verification overhead across the workflow.
    """
    root = get_repo_root()
    report = benchmark(audit_gate_inventory, root)
    assert report.exit_code == 0
