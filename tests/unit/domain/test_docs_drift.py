"""Unit tests for documentation drift domain models.

Notes/Architectural Intent:
    Verifies immutability and contract validation for DocDriftFinding,
    DocDriftReport, and AuditDocsDriftCommand.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hexaqual.domain.docs_drift import (
    AuditDocsDriftCommand,
    DocDriftFinding,
    DocDriftReport,
)


def test_doc_drift_finding_creation() -> None:
    """Verify DocDriftFinding instantiation and attributes."""
    finding = DocDriftFinding(
        file_path="docs/README.md",
        line_number=10,
        drift_type="package_count_mismatch",
        matched_text="17 packages",
        expected_text="18 packages",
        snippet="all 17 packages",
        fixable=True,
    )
    assert finding.line_number == 10
    assert finding.drift_type == "package_count_mismatch"
    assert finding.matched_text == "17 packages"
    assert finding.expected_text == "18 packages"
    assert finding.fixable is True


def test_doc_drift_report_properties() -> None:
    """Verify DocDriftReport aggregation and status properties."""
    f1 = DocDriftFinding(
        file_path="README.md",
        line_number=1,
        drift_type="version_mismatch",
        matched_text="v0.8.0",
        expected_text="v0.9.0",
        snippet="https://img.shields.io/badge/version-v0.8.0-blue.svg",
        fixable=True,
    )
    report_clean = DocDriftReport(findings=(), is_successful=True)
    assert report_clean.is_successful is True
    assert len(report_clean.findings) == 0

    report_dirty = DocDriftReport(findings=(f1,), is_successful=False)
    assert report_dirty.is_successful is False
    assert len(report_dirty.findings) == 1


def test_audit_docs_drift_command_immutability() -> None:
    """Verify AuditDocsDriftCommand validation and immutability."""
    cmd = AuditDocsDriftCommand(repo_root="/workspace")
    root = cmd.repo_root
    assert root == "/workspace"

    with pytest.raises(ValidationError):
        setattr(cmd, "repo_root", "/other")  # noqa: B010
