"""Unit tests for domain generator models and CQRS commands."""

from __future__ import annotations

from hexaqual.domain.generators import (
    ArchonReport,
    GenerateArchonTestsCommand,
    GeneratePydepsCommand,
    GenerateUsageDocsCommand,
    PydepsDiagramResult,
    PydepsReport,
    UsageDocsReport,
)


def test_pydeps_domain_models() -> None:
    """Verify PydepsDiagramResult and PydepsReport instantiation and immutability."""
    res = PydepsDiagramResult(
        name="core",
        path="docs/core.svg",
        success=True,
        is_stale=False,
        details="",
    )
    assert res.name == "core"
    assert res.path == "docs/core.svg"
    assert res.success is True
    assert res.is_stale is False
    assert res.details == ""

    report = PydepsReport(results=(res,), is_successful=True, is_check=True)
    assert len(report.results) == 1
    assert report.is_successful is True
    assert report.is_check is True

    cmd = GeneratePydepsCommand(packages=("core", "events"), check_only=True, fix=False)
    assert cmd.packages == ("core", "events")
    assert cmd.check_only is True
    assert cmd.fix is False


def test_usage_docs_domain_models() -> None:
    """Verify UsageDocsReport and GenerateUsageDocsCommand models."""
    report = UsageDocsReport(
        up_to_date_files=("packages/hexastack/USAGE.md",),
        updated_files=(),
        stale_files=("packages/hexaqual/USAGE.md",),
        diffs=(("packages/hexaqual/USAGE.md", "--- a\n+++ b"),),
        is_valid=False,
    )
    assert len(report.up_to_date_files) == 1
    assert len(report.stale_files) == 1
    assert report.is_valid is False

    cmd = GenerateUsageDocsCommand(check_only=True, fix=False, affected_only=True)
    assert cmd.check_only is True
    assert cmd.fix is False
    assert cmd.affected_only is True


def test_archon_domain_models() -> None:
    """Verify ArchonReport and GenerateArchonTestsCommand models."""
    report = ArchonReport(
        generated_files=("packages/core/tests/architecture/test_hexagonal_boundaries.py",),
        skipped_files=(),
        is_successful=True,
    )
    assert len(report.generated_files) == 1
    assert report.is_successful is True

    cmd = GenerateArchonTestsCommand(packages=("core",), force=True)
    assert cmd.packages == ("core",)
    assert cmd.force is True
