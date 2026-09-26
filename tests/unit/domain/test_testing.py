"""Unit tests for testing domain models and commands.

Notes/Architectural Intent:
    Verifies that domain models, categories, and commands are immutable,
    instantiate with correct defaults, and calculate derived properties properly.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.domain.testing import (
    AuditTestBoundariesCommand,
    AuditTestRedundancyCommand,
    BoundaryAuditItem,
    BoundaryAuditReport,
    ImpactedTestsReport,
    InspectMutationCacheCommand,
    MutantCategory,
    MutantRecord,
    MutationAuditReport,
    MutationEngine,
    MutationPackageSummary,
    RedundancyAuditReport,
    RedundantTestItem,
    RunImpactedTestsCommand,
    RunMutationTestsCommand,
)


def test_mutation_models():
    """Verify MutationAuditReport and MutantRecord models."""
    summary = MutationPackageSummary(
        package_name="hexastack_core",
        total=10,
        critical=2,
        equivalent=3,
        ignorable=5,
    )
    mutant = MutantRecord(
        id="1",
        filename="packages/hexastack_core/src/model.py",
        line_number=42,
        line_content="if status == 1:",
        category=MutantCategory.CRITICAL,
        rationale="Control flow",
    )
    report = MutationAuditReport(
        summaries=(summary,),
        actionable_mutants=(mutant,),
    )
    assert report.total_critical == 2
    assert len(report.actionable_mutants) == 1
    assert report.actionable_mutants[0].category == MutantCategory.CRITICAL


def test_boundary_audit_report():
    """Verify BoundaryAuditReport properties."""
    clean_report = BoundaryAuditReport(leaks=())
    assert clean_report.is_healthy is True

    leaky_report = BoundaryAuditReport(
        leaks=(BoundaryAuditItem("tests.unit.test_domain", "packages/core/infra/db.py"),)
    )
    assert leaky_report.is_healthy is False


def test_redundancy_and_impact_models():
    """Verify RedundancyAuditReport and ImpactedTestsReport models."""
    red_report = RedundancyAuditReport(redundant_tests=("test_foo",))
    assert len(red_report.redundant_tests) == 1

    item = RedundantTestItem(test_context="test_bar")
    assert item.test_context == "test_bar"

    impact = ImpactedTestsReport(
        changed_files=("foo.py",),
        impacted_tests=("test_foo",),
        dry_run=True,
    )
    assert impact.dry_run is True


def test_commands_instantiation(tmp_path: Path):
    """Verify all domain commands instantiate properly."""
    c1 = RunMutationTestsCommand(
        package="core",
        reset_cache=True,
        engine=MutationEngine.GREMLINS,
        workers="auto",
        numprocesses=2,
        batch_size=10,
    )
    res_pkg = c1.package
    assert res_pkg == "core"
    res_engine = c1.engine
    assert res_engine == MutationEngine.GREMLINS
    res_workers = c1.workers
    assert res_workers == "auto"

    c2 = InspectMutationCacheCommand(
        cache_file=tmp_path / ".mutmut-cache",
        engine=MutationEngine.GREMLINS,
        report_file=tmp_path / "gremlins.json",
    )
    res_actionable = c2.actionable_only
    assert res_actionable is False
    res_c2_engine = c2.engine
    assert res_c2_engine == MutationEngine.GREMLINS
    res_c2_report = c2.report_file
    assert res_c2_report == tmp_path / "gremlins.json"

    c3 = AuditTestBoundariesCommand(coverage_file=tmp_path / ".coverage")
    assert c3.coverage_file == tmp_path / ".coverage"

    c4 = AuditTestRedundancyCommand(coverage_file=tmp_path / ".coverage")
    assert c4.coverage_file == tmp_path / ".coverage"

    c5 = RunImpactedTestsCommand(repo_root=tmp_path, dry_run=True)
    assert c5.dry_run is True
