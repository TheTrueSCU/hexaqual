"""Unit tests for multi-format IaC presenters.

Notes/Architectural Intent:
    Verifies Rich, JSON, and Markdown rendering of IacAuditReport and
    IacInventoryReport across pass, fail, skip, and finding-truncation branches.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from hexaqual.adapters.presenters.iac import (
    JsonIacPresenterAdapter,
    MarkdownIacPresenterAdapter,
    RichIacPresenterAdapter,
    create_iac_presenter,
)
from hexaqual.domain.iac import (
    IacAssetInventory,
    IacAuditReport,
    IacCategory,
    IacCheckStatus,
    IacFinding,
    IacInventoryReport,
    IacSeverity,
    IacToolAvailability,
    IacToolName,
    IacToolResult,
)


def _sample_reports(tmp_path: Path) -> tuple[IacAuditReport, IacAuditReport, IacAuditReport]:
    """Construct clean, skipped, and failing IaC audit reports for presenter tests."""
    inv = IacAssetInventory(
        tofu_dirs=(tmp_path / "tofu",),
        tofu_files=(tmp_path / "tofu" / "main.tf",),
        dockerfiles=(tmp_path / "Dockerfile",),
        shell_scripts=(tmp_path / "boot.sh",),
    )
    finding = IacFinding(
        tool=IacToolName.SHELLCHECK,
        category=IacCategory.SHELL,
        file_path="boot.sh",
        line=10,
        rule_id="SC2154",
        severity=IacSeverity.MEDIUM,
        message="var is referenced | check pipe escaping",
    )
    clean_res = IacToolResult(
        tool=IacToolName.TOFU_FMT,
        category=IacCategory.OPENTOFU,
        status=IacCheckStatus.PASS,
        duration=0.05,
        targets_checked=1,
        details="Formatting clean",
    )
    fail_res = IacToolResult(
        tool=IacToolName.SHELLCHECK,
        category=IacCategory.SHELL,
        status=IacCheckStatus.FAIL,
        duration=0.08,
        targets_checked=1,
        findings=(finding,),
        details="1 shell issue",
    )
    err_only_res = IacToolResult(
        tool=IacToolName.TFLINT,
        category=IacCategory.OPENTOFU,
        status=IacCheckStatus.FAIL,
        duration=0.01,
        targets_checked=0,
        details="tflint missing",
        error_output="tflint binary missing in strict mode",
    )
    clean_report = IacAuditReport(
        repo_root=tmp_path,
        inventory=inv,
        results=(clean_res,),
        total_duration=0.05,
        exit_code=0,
    )
    fail_report = IacAuditReport(
        repo_root=tmp_path,
        inventory=inv,
        results=(clean_res, fail_res, err_only_res),
        total_duration=0.14,
        exit_code=1,
    )
    empty_report = IacAuditReport(
        repo_root=tmp_path,
        inventory=IacAssetInventory(),
        results=(
            IacToolResult(
                tool=IacToolName.TOFU_FMT,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.SKIP,
                details="No OpenTofu files",
            ),
        ),
        total_duration=0.01,
        exit_code=0,
    )
    return clean_report, fail_report, empty_report


def test_rich_iac_presenter_audit_and_inventory(tmp_path: Path) -> None:
    """Verify Rich presenter renders audit dashboards, truncates >50 findings, and renders inventory."""
    clean_report, fail_report, empty_report = _sample_reports(tmp_path)
    buf = StringIO()
    presenter = RichIacPresenterAdapter(console=Console(file=buf, force_terminal=False, width=120))

    code_clean = presenter.present_iac_audit(clean_report)
    assert code_clean == 0
    assert "All IaC gates completed cleanly" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    code_empty = presenter.present_iac_audit(empty_report)
    assert code_empty == 0
    assert "No IaC assets discovered" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    code_fail = presenter.present_iac_audit(fail_report)
    assert code_fail == 1
    out_fail = buf.getvalue()
    assert "SC2154" in out_fail
    assert "tflint binary missing in strict mode" in out_fail

    # Truncation note when > 50 findings
    many_findings = tuple(
        IacFinding(
            tool=IacToolName.TRIVY,
            category=IacCategory.OPENTOFU,
            file_path="main.tf",
            line=idx,
            rule_id=f"AVD-{idx}",
            severity=IacSeverity.HIGH,
            message="issue",
        )
        for idx in range(55)
    )
    large_report = IacAuditReport(
        repo_root=tmp_path,
        inventory=clean_report.inventory,
        results=(
            IacToolResult(
                tool=IacToolName.TRIVY,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.FAIL,
                targets_checked=1,
                findings=many_findings,
            ),
        ),
        exit_code=1,
    )
    buf.truncate(0)
    buf.seek(0)
    code_large = presenter.present_iac_audit(large_report)
    assert code_large == 1
    assert "5 additional finding(s) omitted" in buf.getvalue()

    # Inventory with >5 files preview
    inv_report = IacInventoryReport(
        repo_root=tmp_path,
        inventory=IacAssetInventory(
            tofu_files=tuple(tmp_path / f"f{i}.tf" for i in range(7)),
        ),
        tools=(
            IacToolAvailability(IacToolName.TOFU_FMT, "tofu", True, "/usr/bin/tofu"),
            IacToolAvailability(IacToolName.TRIVY, "trivy", False, ""),
        ),
    )
    buf.truncate(0)
    buf.seek(0)
    code_inv = presenter.present_iac_inventory(inv_report)
    assert code_inv == 0
    out_inv = buf.getvalue()
    assert "(+2 more)" in out_inv
    assert "INSTALLED" in out_inv
    assert "MISSING" in out_inv


def test_json_iac_presenter_audit_and_inventory(tmp_path: Path) -> None:
    """Verify JSON presenter serializes audit and inventory reports cleanly."""
    clean_report, fail_report, _ = _sample_reports(tmp_path)
    buf = StringIO()
    presenter = JsonIacPresenterAdapter(console=Console(file=buf, force_terminal=False, width=120))

    code_fail = presenter.present_iac_audit(fail_report)
    assert code_fail == 1
    payload = json.loads(buf.getvalue())
    assert payload["status"] == "FAIL"
    assert payload["total_findings"] == 1
    assert payload["findings"][0]["rule_id"] == "SC2154"

    buf.truncate(0)
    buf.seek(0)
    inv_report = IacInventoryReport(
        repo_root=tmp_path,
        inventory=clean_report.inventory,
        tools=(IacToolAvailability(IacToolName.TOFU_FMT, "tofu", True, "/usr/bin/tofu"),),
    )
    code_inv = presenter.present_iac_inventory(inv_report)
    assert code_inv == 0
    inv_payload = json.loads(buf.getvalue())
    assert isinstance(inv_payload["has_any"], bool)
    assert inv_payload["has_any"] is True
    assert inv_payload["tools"][0]["installed"] is True

    # Narrow 40-column console must NOT soft-wrap long strings inside JSON
    narrow_buf = StringIO()
    narrow_presenter = JsonIacPresenterAdapter(
        console=Console(file=narrow_buf, force_terminal=False, width=40)
    )
    long_inv = IacInventoryReport(
        repo_root=tmp_path,
        inventory=clean_report.inventory,
        tools=(
            IacToolAvailability(
                IacToolName.SHELLCHECK,
                "shellcheck",
                True,
                "/very/long/installation/path/exceeding/forty/columns/bin/shellcheck",
            ),
        ),
    )
    narrow_code = narrow_presenter.present_iac_inventory(long_inv)
    assert narrow_code == 0
    narrow_parsed = json.loads(narrow_buf.getvalue())
    assert (
        narrow_parsed["tools"][0]["resolved_path"]
        == "/very/long/installation/path/exceeding/forty/columns/bin/shellcheck"
    )


def test_markdown_iac_presenter_and_factory(tmp_path: Path) -> None:
    """Verify Markdown presenter output and create_iac_presenter factory."""
    clean_report, fail_report, empty_report = _sample_reports(tmp_path)
    buf = StringIO()
    presenter = MarkdownIacPresenterAdapter(
        console=Console(file=buf, force_terminal=False, width=120)
    )

    code_clean = presenter.present_iac_audit(clean_report)
    assert code_clean == 0
    assert "All IaC gates completed cleanly" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    code_empty = presenter.present_iac_audit(empty_report)
    assert code_empty == 0
    assert "No IaC assets discovered" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    code_fail = presenter.present_iac_audit(fail_report)
    assert code_fail == 1
    md_out = buf.getvalue()
    assert "| `shellcheck` |" in md_out
    assert "check pipe escaping" in md_out

    buf.truncate(0)
    buf.seek(0)
    inv_report = IacInventoryReport(
        repo_root=tmp_path,
        inventory=clean_report.inventory,
        tools=(IacToolAvailability(IacToolName.HADOLINT, "hadolint", True, "/usr/bin/hadolint"),),
    )
    code_inv = presenter.present_iac_inventory(inv_report)
    assert code_inv == 0
    assert "Discovered IaC Assets & Tool Readiness" in buf.getvalue()

    assert isinstance(create_iac_presenter("table"), RichIacPresenterAdapter)
    assert isinstance(create_iac_presenter("rich"), RichIacPresenterAdapter)
    assert isinstance(create_iac_presenter("json"), JsonIacPresenterAdapter)
    assert isinstance(create_iac_presenter("markdown"), MarkdownIacPresenterAdapter)
    assert isinstance(create_iac_presenter("md"), MarkdownIacPresenterAdapter)

    with pytest.raises(ValueError, match="Unsupported IaC presenter format"):
        create_iac_presenter("yaml")
