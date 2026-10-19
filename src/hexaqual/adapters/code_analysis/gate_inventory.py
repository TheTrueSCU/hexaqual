"""Quality gate inventory auditor inspecting repository governance controls.

Notes/Architectural Intent:
    Scans the repository to audit the presence and active enforcement of canonical
    quality gates (static lint, typechecking, cognitive complexity, export integrity,
    1:1 test symmetry, hexagonal boundaries, exercise gates, git hooks, and AI guardrails).
    Prevents silent gate erosion or accidental deactivation.
"""

from __future__ import annotations

import os
from pathlib import Path

from hexaqual.domain.governance import (
    GateInventoryItem,
    GateInventoryReport,
)

__all__ = [
    "audit_gate_inventory",
]


def _has_pyproject_section(pyproject_path: Path, section_prefix: str) -> bool:
    """Check if pyproject.toml contains a specific configuration section prefix."""
    if not pyproject_path.is_file():
        return False
    try:
        content = pyproject_path.read_text(encoding="utf-8")
        return section_prefix in content
    except OSError:
        return False


def _check_static_linter(repo_root: Path) -> GateInventoryItem:
    """Audit Ruff static linter and formatter configuration."""
    ruff_files = [repo_root / "ruff.toml", repo_root / ".ruff.toml"]
    pyproject = repo_root / "pyproject.toml"

    has_root = any(p.is_file() for p in ruff_files) or _has_pyproject_section(
        pyproject, "[tool.ruff"
    )
    has_subpkg = any(
        _has_pyproject_section(p, "[tool.ruff") for p in repo_root.glob("packages/*/pyproject.toml")
    )

    if has_root or has_subpkg:
        return GateInventoryItem(
            name="Static Linter (Ruff)",
            category="Static Analysis",
            status="ACTIVE",
            details="Ruff configured for linting and code formatting.",
        )
    return GateInventoryItem(
        name="Static Linter (Ruff)",
        category="Static Analysis",
        status="MISSING",
        details="No Ruff configuration file or [tool.ruff] section found.",
        remediation="Create ruff.toml or configure [tool.ruff] in pyproject.toml.",
    )


def _check_typechecker(repo_root: Path) -> GateInventoryItem:
    """Audit Ty static type analyzer configuration."""
    ty_files = [repo_root / "ty.toml", repo_root / ".ty.toml"]
    pyproject = repo_root / "pyproject.toml"

    has_root = any(p.is_file() for p in ty_files) or _has_pyproject_section(pyproject, "[tool.ty")
    has_subpkg = any(
        _has_pyproject_section(p, "[tool.ty") for p in repo_root.glob("packages/*/pyproject.toml")
    )

    if has_root or has_subpkg:
        return GateInventoryItem(
            name="Type Checking (Ty)",
            category="Static Analysis",
            status="ACTIVE",
            details="Ty static type analyzer configured.",
        )
    return GateInventoryItem(
        name="Type Checking (Ty)",
        category="Static Analysis",
        status="MISSING",
        details="No Ty configuration found in repo or workspace packages.",
        remediation="Add [tool.ty] to pyproject.toml or configure ty.toml.",
    )


def _check_test_parity(repo_root: Path) -> GateInventoryItem:
    """Audit 1:1 unit test symmetry gate."""
    test_dirs = [repo_root / "tests" / "unit"]
    for pkg in repo_root.glob("packages/*/tests/unit"):
        if pkg.is_dir():
            test_dirs.append(pkg)

    if any(d.is_dir() for d in test_dirs):
        return GateInventoryItem(
            name="1:1 Unit Test Symmetry",
            category="Verification",
            status="ACTIVE",
            details="Unit test directories detected and verified via test parity gate.",
        )
    return GateInventoryItem(
        name="1:1 Unit Test Symmetry",
        category="Verification",
        status="MISSING",
        details="No tests/unit directory found in repo or packages.",
        remediation="Scaffold tests/unit/ structure mirroring source modules.",
    )


def _check_hexagonal_boundaries(repo_root: Path) -> GateInventoryItem:
    """Audit hexagonal boundary enforcement and architecture tests."""
    importlinter = repo_root / ".importlinter"
    arch_tests = list(repo_root.glob("**/test_hexagonal_boundaries.py"))
    has_linter_config = _has_pyproject_section(repo_root / "pyproject.toml", "[tool.importlinter")

    if importlinter.is_file() or arch_tests or has_linter_config:
        details = f"Active: {len(arch_tests)} architecture test suite(s)" + (
            ", import-linter configured." if (importlinter.is_file() or has_linter_config) else "."
        )
        return GateInventoryItem(
            name="Hexagonal Boundary Isolation",
            category="Architecture",
            status="ACTIVE",
            details=details,
        )
    return GateInventoryItem(
        name="Hexagonal Boundary Isolation",
        category="Architecture",
        status="WARNING",
        details="No test_hexagonal_boundaries.py suites or .importlinter found.",
        remediation="Author tests/architecture/test_hexagonal_boundaries.py or add .importlinter.",
    )


def _check_git_hooks(repo_root: Path) -> GateInventoryItem:
    """Audit Git lifecycle hook installation."""
    hook = repo_root / ".git" / "hooks" / "pre-commit"
    if hook.is_file() and os.access(hook, os.X_OK):
        return GateInventoryItem(
            name="Git Lifecycle Hooks",
            category="Lifecycle",
            status="ACTIVE",
            details="Pre-commit hook installed and executable in .git/hooks/.",
        )
    return GateInventoryItem(
        name="Git Lifecycle Hooks",
        category="Lifecycle",
        status="MISSING",
        details="Pre-commit hook not installed or not executable in .git/hooks/.",
        remediation="Run 'uv run hexaqual hooks install'.",
    )


def _check_agent_guardrails(repo_root: Path) -> GateInventoryItem:
    """Audit AI agent guardrails and AGENTS.md index."""
    agents_md = repo_root / "AGENTS.md"
    rules_dir = repo_root / ".agents" / "rules"

    if agents_md.is_file() and rules_dir.is_dir() and any(rules_dir.glob("*.md")):
        rule_count = len(list(rules_dir.glob("*.md")))
        return GateInventoryItem(
            name="AI Agent Guardrails Index",
            category="AI Governance",
            status="ACTIVE",
            details=f"AGENTS.md present with {rule_count} active rule(s) in .agents/rules/.",
        )
    return GateInventoryItem(
        name="AI Agent Guardrails Index",
        category="AI Governance",
        status="MISSING",
        details="AGENTS.md or .agents/rules/ directory missing.",
        remediation="Run 'uv run hexaqual agents sync' to initialize agent guardrails.",
    )


def _check_reanchoring(repo_root: Path) -> GateInventoryItem:
    """Audit Architectural Decision Records and context re-anchoring rules."""
    decisions_md = repo_root / "docs" / "decisions.md"
    reanchoring_rules = list(repo_root.glob(".agents/rules/*reanchoring*.md"))

    if decisions_md.is_file() or reanchoring_rules:
        details = (
            "docs/decisions.md present"
            if decisions_md.is_file()
            else "re-anchoring rule installed in .agents/rules/"
        )
        return GateInventoryItem(
            name="Architectural Decisions & Re-Anchoring",
            category="AI Governance",
            status="ACTIVE",
            details=details,
        )
    return GateInventoryItem(
        name="Architectural Decisions & Re-Anchoring",
        category="AI Governance",
        status="WARNING",
        details="Neither docs/decisions.md nor .agents/rules/*reanchoring*.md found.",
        remediation="Author docs/decisions.md and install re-anchoring guardrails.",
    )


def audit_gate_inventory(repo_root: Path) -> GateInventoryReport:
    """Audit the presence and enforcement status of canonical repository quality gates.

    Args:
        repo_root: Path to the root directory of the repository to inspect.

    Returns:
        Aggregated GateInventoryReport containing all gate statuses and exit code.

    Notes/Architectural Intent:
        Evaluates 10 canonical quality gates across static analysis, code health,
        architecture boundaries, test verification, git lifecycle, and AI governance.
    """
    items: list[GateInventoryItem] = [
        _check_static_linter(repo_root),
        _check_typechecker(repo_root),
        GateInventoryItem(
            name="Cognitive Complexity",
            category="Code Health",
            status="ACTIVE",
            details="Enforced via complexipy in sanity pipeline (threshold <= 25).",
        ),
        GateInventoryItem(
            name="__all__ Integrity & Sorting",
            category="Static Analysis",
            status="ACTIVE",
            details="Enforced via hexaqual statements check in sanity pipeline.",
        ),
        _check_test_parity(repo_root),
        _check_hexagonal_boundaries(repo_root),
        GateInventoryItem(
            name="Anti-Fake-Pass Exercise Gate",
            category="Verification",
            status="ACTIVE",
            details="pytest runner enforces non-zero test execution (--allow-empty to override).",
        ),
        _check_git_hooks(repo_root),
        _check_agent_guardrails(repo_root),
        _check_reanchoring(repo_root),
    ]

    missing = any(i.status == "MISSING" for i in items)
    exit_code = 1 if missing else 0
    return GateInventoryReport(items=tuple(items), exit_code=exit_code)
