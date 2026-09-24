"""Unit tests for multi-format dependency presenters.

Notes/Architectural Intent:
    Verifies that Rich, JSON, and Markdown presenters format extras parity,
    deptry, import-linter, and unified dependency audits correctly.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from rich.console import Console

from hexaqual.adapters.presenters.dependency import (
    JsonDependencyPresenterAdapter,
    MarkdownDependencyPresenterAdapter,
    RichDependencyPresenterAdapter,
    create_dependency_presenter,
)
from hexaqual.domain.dependencies import (
    DependencyAuditItem,
    DeptryAuditReport,
    DeptryPackageResult,
    ExtraParityViolation,
    ExtrasAuditResult,
    ImportLinterPackageResult,
    ImportLinterReport,
    UnifiedDependencyAuditReport,
)


def test_rich_dependency_presenter_all():
    """Verify Rich presenter outputs."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = RichDependencyPresenterAdapter(console=console)

    # 1. Extras parity clean & violation
    v = ExtraParityViolation("db", "sqlite", ("aiosqlite",), "Fix me")
    assert (
        presenter.present_extras_parity(ExtrasAuditResult(violations=(), total_packages_checked=5))
        == 0
    )
    assert "properly forwarded" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    assert (
        presenter.present_extras_parity(
            ExtrasAuditResult(violations=(v,), total_packages_checked=5)
        )
        == 1
    )
    assert "Optional Extras Parity Violations" in buf.getvalue()

    # 2. Deptry
    d_ok = DeptryAuditReport(results=(DeptryPackageResult("core", True),), exit_code=0)
    assert presenter.present_deptry_audit(d_ok) == 0

    # 3. Import linter
    il = ImportLinterReport(results=(ImportLinterPackageResult("cqrs", True),), exit_code=0)
    assert presenter.present_import_linter(il) == 0

    # 4. Unified audit
    item = DependencyAuditItem("Tools", True)
    u_ok = UnifiedDependencyAuditReport(items=(item,), errors=(), is_healthy=True)
    assert presenter.present_unified_deps_audit(u_ok) == 0


def test_json_dependency_presenter_all():
    """Verify JSON presenter serializes valid JSON."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = JsonDependencyPresenterAdapter(console=console)

    v = ExtraParityViolation("db", "sqlite", ("aiosqlite",), "Fix me")
    res = ExtrasAuditResult(violations=(v,), total_packages_checked=5)
    assert presenter.present_extras_parity(res) == 1
    data = json.loads(buf.getvalue())
    assert data["status"] == "FAIL"
    assert data["violations"][0]["subpackage"] == "db"

    buf.truncate(0)
    buf.seek(0)
    d = DeptryAuditReport(results=(DeptryPackageResult("core", True),), exit_code=0)
    assert presenter.present_deptry_audit(d) == 0
    assert json.loads(buf.getvalue())["status"] == "PASS"

    buf.truncate(0)
    buf.seek(0)
    il = ImportLinterReport(
        results=(ImportLinterPackageResult("cqrs", False, error_output="contract broken"),),
        exit_code=1,
    )
    res_il = presenter.present_import_linter(il)
    assert res_il == 1
    il_data = json.loads(buf.getvalue())
    assert il_data["status"] == "FAIL"
    assert il_data["results"][0]["error_output"] == "contract broken"

    buf.truncate(0)
    buf.seek(0)
    u_bad = UnifiedDependencyAuditReport(
        items=(DependencyAuditItem("Extras", False, details="mismatch"),),
        errors=("Error found",),
        is_healthy=False,
    )
    res_u = presenter.present_unified_deps_audit(u_bad)
    assert res_u == 1
    u_data = json.loads(buf.getvalue())
    assert u_data["status"] == "FAIL"
    assert "Error found" in u_data["errors"]


def test_markdown_dependency_presenter_all():
    """Verify Markdown presenter outputs formatted markdown."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = MarkdownDependencyPresenterAdapter(console=console)

    v = ExtraParityViolation("db", "sqlite", ("aiosqlite", "sqlite3", "extra_pkg"), "Fix me")
    res = ExtrasAuditResult(violations=(v,), total_packages_checked=5)
    res_code = presenter.present_extras_parity(res)
    assert res_code == 1
    assert "| Subpackage | Extra |" in buf.getvalue()
    assert "(+1 more)" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    res_diag = presenter.present_extras_parity(res, diagram="```mermaid\n```")
    assert res_diag == 0
    assert "mermaid" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    res_clean = ExtrasAuditResult(violations=(), total_packages_checked=5)
    res_clean_code = presenter.present_extras_parity(res_clean)
    assert res_clean_code == 0
    assert "properly forwarded" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    d = DeptryAuditReport(
        results=(
            DeptryPackageResult("core", True),
            DeptryPackageResult("api", False, error_output="DEP001 missing"),
        ),
        exit_code=1,
    )
    res_deptry = presenter.present_deptry_audit(d)
    assert res_deptry == 1
    assert "Deptry Workspace Dependency Auditor" in buf.getvalue()
    assert "DEP001 missing" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    il = ImportLinterReport(
        results=(
            ImportLinterPackageResult("core", True),
            ImportLinterPackageResult("api", False, error_output="layer violation"),
        ),
        exit_code=1,
    )
    res_il = presenter.present_import_linter(il)
    assert res_il == 1
    assert "Hexagonal Architecture Layer Contracts" in buf.getvalue()
    assert "layer violation" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    u_ok = UnifiedDependencyAuditReport(
        items=(DependencyAuditItem("Extras", True),), errors=(), is_healthy=True
    )
    res_u_ok = presenter.present_unified_deps_audit(u_ok)
    assert res_u_ok == 0
    assert "100% healthy" in buf.getvalue()

    buf.truncate(0)
    buf.seek(0)
    u_fail = UnifiedDependencyAuditReport(
        items=(DependencyAuditItem("Extras", False),),
        errors=("Parity violation detected",),
        is_healthy=False,
    )
    res_u_fail = presenter.present_unified_deps_audit(u_fail)
    assert res_u_fail == 1
    assert "Dependency Issues Found" in buf.getvalue()
    assert "Parity violation detected" in buf.getvalue()


def test_rich_dependency_presenter_extras():
    """Verify Rich presenter diagram and violation branches."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = RichDependencyPresenterAdapter(console=console)

    res = ExtrasAuditResult(violations=(), total_packages_checked=5)
    res_diag = presenter.present_extras_parity(res, diagram="```mermaid\n```")
    assert res_diag == 0
    assert "mermaid" in buf.getvalue()

    u_bad = UnifiedDependencyAuditReport(
        items=(DependencyAuditItem("Extras", False, details="error"),),
        errors=("Critical failure",),
        is_healthy=False,
    )
    res_u_bad = presenter.present_unified_deps_audit(u_bad)
    assert res_u_bad == 1


def test_create_dependency_presenter_factory():
    """Verify create_dependency_presenter factory."""
    assert isinstance(create_dependency_presenter("table"), RichDependencyPresenterAdapter)
    assert isinstance(create_dependency_presenter("json"), JsonDependencyPresenterAdapter)
    assert isinstance(create_dependency_presenter("markdown"), MarkdownDependencyPresenterAdapter)
    assert isinstance(create_dependency_presenter("md"), MarkdownDependencyPresenterAdapter)

    with pytest.raises(ValueError, match="Unsupported dependency presenter format"):
        create_dependency_presenter("invalid")
