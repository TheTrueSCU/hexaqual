"""Unit tests for IaC domain models, enums, severity mapping, and CQRS commands.

Notes/Architectural Intent:
    Validates pure domain invariants in ``hexaqual.domain.iac`` with zero
    filesystem or subprocess coupling.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from hexaqual.domain.iac import (
    DiscoverIacAssetsCommand,
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
    RunIacAuditCommand,
    normalize_severity,
)


def test_normalize_severity_mappings() -> None:
    """Verify heterogeneous severity aliases map to canonical IacSeverity values."""
    assert normalize_severity("CRITICAL") == IacSeverity.CRITICAL
    assert normalize_severity("crit") == IacSeverity.CRITICAL
    assert normalize_severity("HIGH") == IacSeverity.HIGH
    assert normalize_severity("error") == IacSeverity.HIGH
    assert normalize_severity("err") == IacSeverity.HIGH
    assert normalize_severity("Medium") == IacSeverity.MEDIUM
    assert normalize_severity("warning") == IacSeverity.MEDIUM
    assert normalize_severity("warn") == IacSeverity.MEDIUM
    assert normalize_severity("low") == IacSeverity.LOW
    assert normalize_severity("INFO") == IacSeverity.INFO
    assert normalize_severity("style") == IacSeverity.INFO
    assert normalize_severity("notice") == IacSeverity.INFO
    assert normalize_severity("") == IacSeverity.UNKNOWN
    assert normalize_severity(None) == IacSeverity.UNKNOWN
    assert normalize_severity("custom-level") == IacSeverity.UNKNOWN


def test_iac_asset_inventory_properties() -> None:
    """Verify has_any and total_files properties across empty and populated inventories."""
    empty = IacAssetInventory()
    has_empty = empty.has_any
    total_empty = empty.total_files
    assert has_empty is False
    assert total_empty == 0

    populated = IacAssetInventory(
        tofu_dirs=(Path("deploy/tofu"),),
        tofu_files=(Path("deploy/tofu/main.tf"), Path("deploy/tofu/vars.tf")),
        dockerfiles=(Path("Dockerfile"),),
        k8s_paths=(Path("deploy/k8s/deploy.yaml"),),
        shell_scripts=(Path("scripts/boot.sh"),),
    )
    has_pop = populated.has_any
    total_pop = populated.total_files
    assert has_pop is True
    assert total_pop == 5


def test_iac_audit_report_findings_and_immutability() -> None:
    """Verify IacAuditReport flattens findings, computes is_clean, and enforces frozen models."""
    finding_a = IacFinding(
        tool=IacToolName.HADOLINT,
        category=IacCategory.DOCKER,
        file_path="Dockerfile",
        line=12,
        rule_id="DL3008",
        severity=IacSeverity.MEDIUM,
        message="Pin versions in apt get install",
    )
    finding_b = IacFinding(
        tool=IacToolName.SHELLCHECK,
        category=IacCategory.SHELL,
        file_path="boot.sh",
        line=5,
        rule_id="SC2154",
        severity=IacSeverity.MEDIUM,
        message="var is referenced but not assigned",
    )
    res_a = IacToolResult(
        tool=IacToolName.HADOLINT,
        category=IacCategory.DOCKER,
        status=IacCheckStatus.FAIL,
        targets_checked=1,
        findings=(finding_a,),
    )
    res_b = IacToolResult(
        tool=IacToolName.SHELLCHECK,
        category=IacCategory.SHELL,
        status=IacCheckStatus.PASS,
        targets_checked=1,
        findings=(finding_b,),
    )

    fail_report = IacAuditReport(
        repo_root=Path("/tmp/repo"),
        inventory=IacAssetInventory(dockerfiles=(Path("Dockerfile"),)),
        results=(res_a, res_b),
        total_duration=0.42,
        exit_code=1,
    )
    findings = fail_report.findings
    is_clean = fail_report.is_clean
    assert findings == (finding_a, finding_b)
    assert is_clean is False

    clean_report = IacAuditReport(
        repo_root=Path("/tmp/repo"),
        inventory=IacAssetInventory(),
        results=(),
        exit_code=0,
    )
    clean_flag = clean_report.is_clean
    assert clean_flag is True

    finding_mut: Any = finding_a
    with pytest.raises(FrozenInstanceError):
        finding_mut.line = 99


def test_iac_commands_and_inventory_report() -> None:
    """Verify DiscoverIacAssetsCommand, RunIacAuditCommand, and IacInventoryReport contracts."""
    disc = DiscoverIacAssetsCommand(repo_root=Path("/tmp/repo"))
    assert disc.paths == ()

    run_cmd = RunIacAuditCommand(
        repo_root=Path("/tmp/repo"),
        tools=(IacToolName.TOFU_FMT, IacToolName.TRIVY),
        fix=True,
        strict=True,
    )
    assert run_cmd.fix is True
    assert run_cmd.strict is True
    assert run_cmd.severity == "HIGH,CRITICAL"

    with pytest.raises(ValidationError):
        RunIacAuditCommand.model_validate({"repo_root": Path("/tmp/repo"), "unknown_field": True})

    inv_report = IacInventoryReport(
        repo_root=Path("/tmp/repo"),
        inventory=IacAssetInventory(),
        tools=(IacToolAvailability(IacToolName.TOFU_FMT, "tofu", True, "/usr/bin/tofu"),),
    )
    assert inv_report.tools[0].installed is True
