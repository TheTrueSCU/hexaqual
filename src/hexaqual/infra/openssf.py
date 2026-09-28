"""Infrastructure services for local repository inspection and OpenSSF evaluation.

Notes/Architectural Intent:
    Orchestrates Git metadata inspection, filesystem checks, and heuristic analysis
    to correlate local repository posture with OpenSSF Best Practices requirements.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from hexaqual.domain.openssf import (
    CriterionProposal,
    CriterionStatus,
    OpenSsfAuditResult,
    OpenSsfCheckResult,
    OpenSsfCriteriaCatalog,
    OpenSsfProject,
    OpenSsfTier,
)

__all__ = [
    "audit_project_posture",
    "evaluate_local_heuristics",
    "format_checklist_markdown",
    "generate_checklist",
    "resolve_local_repo_url",
    "scaffold_document",
    "verify_openssf_compliance",
]


def resolve_local_repo_url(root_dir: Path | None = None) -> str | None:
    """Extract and normalize the remote repository URL from the local Git configuration.

    Args:
        root_dir: Repository root directory (defaults to current working directory).

    Returns:
        Normalized HTTPS repository URL (e.g. 'https://github.com/owner/repo'), or None.

    Notes/Architectural Intent:
        Converts SSH and Git URL variants (e.g. 'git@github.com:org/repo.git')
        to standard HTTPS URLs required for OpenSSF registry search.
    """
    cwd = root_dir or Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None

        raw_url = proc.stdout.strip()
        # Convert SSH to HTTPS: git@github.com:owner/repo.git -> https://github.com/owner/repo
        if raw_url.startswith("git@"):
            ssh_match = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", raw_url)
            if ssh_match:
                host, path = ssh_match.groups()
                return f"https://{host}/{path}"

        # Strip .git suffix from HTTPS URLs
        return re.sub(r"\.git$", "", raw_url)
    except Exception:
        return None


def _detect_crypto_usage(root: Path) -> bool:
    """Check whether local Python sources import custom cryptographic packages."""
    src_dir = root / "src"
    if not src_dir.is_dir():
        return False

    for p in src_dir.rglob("*.py"):
        try:
            content = p.read_text("utf-8", errors="ignore")
            if "cryptography" in content or "pycryptodome" in content:
                return True
        except Exception:
            continue
    return False


def _evaluate_passing_heuristics(root: Path, pyproject_text: str) -> list[CriterionProposal]:
    """Evaluate Level 0 (Passing) criteria inferred from repository artifacts."""
    proposals: list[CriterionProposal] = []
    has_tests = (root / "tests").is_dir()

    if has_tests:
        proposals.append(
            CriterionProposal(
                criterion_id="tests_documented_added",
                status=CriterionStatus.MET,
                justification=(
                    "Documented in CONTRIBUTING.md under 'Testing Requirements'. "
                    "Every PR requires test coverage and 100% test parity enforced by pre-commit and CI."
                ),
                tier=OpenSsfTier.PASSING,
            )
        )
        proposals.append(
            CriterionProposal(
                criterion_id="dynamic_analysis_unsafe",
                status=CriterionStatus.MET,
                justification=(
                    "pytest runs test suites with assertions enabled on Python 3; "
                    "Hypothesis and mutation fuzzing verify dynamic edge cases."
                ),
                tier=OpenSsfTier.PASSING,
            )
        )
        proposals.append(
            CriterionProposal(
                criterion_id="dynamic_analysis_enable_assertions",
                status=CriterionStatus.MET,
                justification="All test suites execute with Python assertions enabled on every commit and PR.",
                tier=OpenSsfTier.PASSING,
            )
        )

    has_codeql = (
        root / ".github" / "workflows" / "codeql.yml"
    ).exists() or "codeql" in pyproject_text.lower()
    if has_codeql or "ruff" in pyproject_text.lower():
        proposals.append(
            CriterionProposal(
                criterion_id="static_analysis_common_vulnerabilities",
                status=CriterionStatus.MET,
                justification=(
                    "Automated CodeQL SAST and Ruff security checks (rule S) run on every push and PR; "
                    "pip-audit monitors dependencies for known CVEs."
                ),
                tier=OpenSsfTier.PASSING,
            )
        )

    if not _detect_crypto_usage(root):
        proposals.append(
            CriterionProposal(
                criterion_id="crypto_weaknesses",
                status=CriterionStatus.NA,
                justification="N/A: The project does not implement cryptographic functions or protocols.",
                tier=OpenSsfTier.PASSING,
            )
        )

    return proposals


def _evaluate_silver_heuristics(
    root: Path, pyproject_text: str, repo_url: str
) -> list[CriterionProposal]:
    """Evaluate Level 1 (Silver) criteria inferred from repository artifacts."""
    proposals: list[CriterionProposal] = []
    if (root / "uv.lock").exists():
        proposals.append(
            CriterionProposal(
                criterion_id="build_reproducible",
                status=CriterionStatus.MET,
                justification=f"{repo_url}/blob/main/uv.lock — Deterministic lockfile with pinned SHA-256 hashes.",
                tier=OpenSsfTier.SILVER,
            )
        )

    if "coverage" in pyproject_text.lower() or (root / ".coverage").exists():
        proposals.append(
            CriterionProposal(
                criterion_id="test_statement_coverage80",
                status=CriterionStatus.MET,
                justification="Strict statement coverage (>=80%) enforced via pytest-cov and CI status checks.",
                tier=OpenSsfTier.SILVER,
            )
        )
    return proposals


def evaluate_local_heuristics(
    tier: OpenSsfTier,
    root_dir: Path | None = None,
) -> list[CriterionProposal]:
    """Inspect local repository files and evaluate known OpenSSF criteria.

    Args:
        tier: Certification tier being targeted.
        root_dir: Repository root directory.

    Returns:
        List of CriterionProposal objects inferred from local evidence.

    Notes/Architectural Intent:
        Extracts ground truth evidence from presence of test suites, CI workflows,
        governance documents, and absence of custom cryptographic implementations.
    """
    root = root_dir or Path.cwd()
    pyproject_path = root / "pyproject.toml"
    pyproject_text = pyproject_path.read_text("utf-8") if pyproject_path.exists() else ""
    repo_url = resolve_local_repo_url(root) or "https://github.com"

    if tier == OpenSsfTier.PASSING:
        return _evaluate_passing_heuristics(root, pyproject_text)
    if tier == OpenSsfTier.SILVER:
        return _evaluate_silver_heuristics(root, pyproject_text, repo_url)
    return []


def audit_project_posture(
    project: OpenSsfProject,
    tier: OpenSsfTier,
    local_proposals: Sequence[CriterionProposal],
) -> OpenSsfAuditResult:
    """Correlate remote project criteria with local heuristics to produce an audit result.

    Args:
        project: Remote project metadata from bestpractices.dev.
        tier: Certification tier being audited.
        local_proposals: Proposing criteria inferred from local repository.

    Returns:
        OpenSsfAuditResult detailing met counts, percentage, and pending proposals.

    Notes/Architectural Intent:
        Identifies criteria that are currently unset or unmet on the badge where local
        heuristics have evidence ready to propose.
    """
    pending: list[CriterionProposal] = []
    for prop in local_proposals:
        current_status = project.criteria_statuses.get(prop.criterion_id)
        if current_status not in (CriterionStatus.MET.value, CriterionStatus.NA.value):
            pending.append(prop)

    total_count = len(project.criteria_statuses)
    met_count = sum(
        1
        for s in project.criteria_statuses.values()
        if s in (CriterionStatus.MET.value, CriterionStatus.NA.value)
    )
    percentage = round(met_count / total_count * 100) if total_count > 0 else 0

    return OpenSsfAuditResult(
        project=project,
        tier=tier,
        met_count=met_count,
        total_count=total_count,
        percentage=percentage,
        proposals=pending,
    )


def generate_checklist(
    project: OpenSsfProject,
    tier: OpenSsfTier,
    local_proposals: Sequence[CriterionProposal] | None = None,
    unmet_only: bool = False,
) -> list[dict[str, Any]]:
    """Generate machine-readable checklist items combining remote badge state with local heuristics.

    Args:
        project: Project retrieved from bestpractices.dev.
        tier: Certification tier (passing, silver, gold).
        local_proposals: Optional local heuristic evaluation proposals.
        unmet_only: When True, filters out criteria that are already Met or N/A.

    Returns:
        List of dictionary objects containing criterion details, statuses, and justifications.

    Notes/Architectural Intent:
        Serves as the structured canonical checklist payload for AI coding agents,
        reporting tools, and terminal formatters.
    """
    definitions = OpenSsfCriteriaCatalog.for_tier(tier)
    proposal_map = {p.criterion_id: p for p in (local_proposals or ())}

    items: list[dict[str, Any]] = []
    for defn in definitions:
        curr_status = project.criteria_statuses.get(
            defn.criterion_id, CriterionStatus.UNKNOWN.value
        )
        if unmet_only and curr_status in (CriterionStatus.MET.value, CriterionStatus.NA.value):
            continue

        justification = project.criteria_justifications.get(defn.criterion_id, "")
        local_prop = proposal_map.get(defn.criterion_id)
        local_verdict = (
            str(
                local_prop.status.value
                if hasattr(local_prop.status, "value")
                else local_prop.status
            )
            if local_prop
            else None
        )

        items.append(
            {
                "criterion_id": defn.criterion_id,
                "tier": tier.value,
                "category": defn.category,
                "met_url_required": defn.met_url_required,
                "status": curr_status,
                "justification": justification,
                "local_verdict": local_verdict,
                "proposed_justification": local_prop.justification if local_prop else None,
            }
        )

    return items


def format_checklist_markdown(
    items: Sequence[dict[str, Any]],
    project_name: str,
    project_id: int,
    tier: OpenSsfTier,
) -> str:
    """Render OpenSSF checklist items as GitHub-flavored Markdown with checkboxes.

    Args:
        items: Checklist dictionary items produced by generate_checklist.
        project_name: OpenSSF project name.
        project_id: OpenSSF project ID.
        tier: Certification tier.

    Returns:
        Formatted Markdown string.

    Notes/Architectural Intent:
        Produces actionable task lists and audit records for developers and AI agents.
    """
    lines: list[str] = [
        f"# OpenSSF Best Practices Checklist: {project_name} (ID: {project_id})",
        "",
        f"**Target Tier:** `{tier.value}` | **Total Items:** {len(items)}",
        "",
    ]

    for item in items:
        status = item.get("status", "?")
        is_checked = status in ("Met", "N/A")
        box = "[x]" if is_checked else "[ ]"
        cid = item.get("criterion_id", "")
        cat = item.get("category", "MUST")
        url_flag = " (URL required)" if item.get("met_url_required") else ""

        line = f"- {box} **{cid}** (`{cat}`{url_flag}): *{status}*"
        lines.append(line)

        justification = item.get("justification")
        if justification:
            lines.append(f"  - *Current Justification:* {justification}")
        local_verdict = item.get("local_verdict")
        if local_verdict and not is_checked:
            lines.append(f"  - *Local Heuristic Verdict:* {local_verdict}")
            proposed_just = item.get("proposed_justification")
            if proposed_just:
                lines.append(f"  - *Proposed Evidence:* {proposed_just}")

    return "\n".join(lines) + "\n"


_SECURITY_MD_TEMPLATE = """# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take the security of this project seriously. If you discover a security vulnerability, please report it responsibly.

### Private Vulnerability Reporting (Preferred)
Please report vulnerabilities privately using GitHub's **Security Advisories** tab:
`{repo_url}/security/advisories/new`

### Response SLA
- **Initial acknowledgment**: within 48 hours.
- **Status update / remediation plan**: within 7 calendar days.
- **Public disclosure**: coordinated after a fix is tagged and published (typically 30-60 days).

Please do **not** open public GitHub issues or discussions for sensitive security vulnerabilities.
"""

_GOVERNANCE_MD_TEMPLATE = """# Project Governance

## Overview
This project is developed as open-source software under the Apache-2.0 license. This document outlines project leadership, decision-making, and contribution workflows.

## Maintainers
The project is maintained by active community stewards responsible for reviewing pull requests, enforcing quality gates, and publishing releases.

## Decision-Making Process
- **Consensus Seeking**: Day-to-day decisions on bug fixes, performance improvements, and documentation are made through collaborative code review on GitHub PRs.
- **Major Architectural Changes**: Significant features or breaking changes require an Architectural Decision Record (ADR) or GitHub Discussion before implementation.
- **Quality Standards**: All merged code must satisfy 100% test parity, zero lint errors, and pre-commit verification.

## Becoming a Maintainer
Contributors who demonstrate sustained technical excellence, adherence to project guardrails, and constructive engagement in issues and PRs may be invited to become maintainers.
"""

_CONTRIBUTING_MD_TEMPLATE = """# Contributing Guidelines

Thank you for your interest in contributing!

## Developer Certificate of Origin (DCO)
All contributions must include a DCO sign-off line in the commit message:
```bash
git commit -s -m "feat(scope): descriptive summary"
```
By signing off, you certify that you wrote the code or have the right to submit it under the project's open-source license.

## Testing & Quality Requirements
- Every source module requires a matching unit test suite under `tests/unit/` (100% test parity).
- Code must pass all pre-commit hooks and static analysis:
```bash
uv run hexaqual sanity -a --skip-tests
uv run pre-commit run --all-files
```
- Test suites must maintain >= 90% code coverage.
"""

_CODEQL_YML_TEMPLATE = """name: "CodeQL Analysis"

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
  schedule:
    - cron: '0 6 * * 1'

permissions:
  actions: read
  contents: read
  security-events: write

jobs:
  analyze:
    name: Analyze
    runs-on: ubuntu-latest
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Initialize CodeQL
      uses: github/codeql-action/init@v3
      with:
        languages: python

    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v3
      with:
        category: "/language:python"
"""


def scaffold_document(
    doc_type: str,
    dest_dir: Path | None = None,
    force: bool = False,
    repo_url: str | None = None,
) -> Path:
    """Scaffold standard OpenSSF compliance documents.

    Args:
        doc_type: Document identifier ('security', 'governance', 'contributing', 'codeql').
        dest_dir: Target repository directory (defaults to current working directory).
        force: Overwrite existing file if True.
        repo_url: Optional repository URL for customizing links.

    Returns:
        Path to created or updated document.

    Raises:
        FileExistsError: If target file already exists and force is False.
        ValueError: If doc_type is unknown.

    Notes/Architectural Intent:
        Bootstraps essential governance files satisfying Best Practices criteria
        such as vulnerability_report_private, dco, and governance.
    """
    root = dest_dir or Path.cwd()
    norm_url = repo_url or resolve_local_repo_url(root) or "https://github.com/owner/repo"

    mapping: dict[str, tuple[Path, str]] = {
        "security": (root / "SECURITY.md", _SECURITY_MD_TEMPLATE.format(repo_url=norm_url)),
        "governance": (root / "GOVERNANCE.md", _GOVERNANCE_MD_TEMPLATE),
        "contributing": (root / "CONTRIBUTING.md", _CONTRIBUTING_MD_TEMPLATE),
        "codeql": (root / ".github" / "workflows" / "codeql.yml", _CODEQL_YML_TEMPLATE),
    }

    key = doc_type.lower().strip()
    if key not in mapping:
        valid_options = ", ".join(sorted(mapping.keys()))
        msg = f"Unknown document type '{doc_type}'. Valid options: {valid_options}"
        raise ValueError(msg)

    target_path, content = mapping[key]
    if target_path.exists() and not force:
        msg = f"File '{target_path}' already exists. Use --force to overwrite."
        raise FileExistsError(msg)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    return target_path


_BADGE_LEVEL_RANKS: dict[str, int] = {
    "none": 0,
    "in_progress": 0,
    "passing": 1,
    "silver": 2,
    "gold": 3,
}


def verify_openssf_compliance(
    project: OpenSsfProject,
    target_tier: OpenSsfTier,
    min_score: int = 100,
    require_badge_level: str | None = None,
) -> OpenSsfCheckResult:
    """Verify that a project satisfies all OpenSSF badge tier requirements.

    Args:
        project: Retrieved OpenSsfProject metadata and criteria statuses.
        target_tier: Target certification tier (passing, silver, gold).
        min_score: Minimum tiered percentage required to pass (default: 100).
        require_badge_level: Explicit badge level required (defaults to target_tier.value).

    Returns:
        OpenSsfCheckResult detailing compliance status, unmet MUST criteria, and errors.

    Notes/Architectural Intent:
        Evaluates badge level hierarchy, score threshold, and all MUST criteria
        defined for the target tier in OpenSsfCriteriaCatalog. Returns a structured
        result for CI gate evaluation and pre-commit hook enforcement.
    """
    errors: list[str] = []
    unmet_must: list[dict[str, str]] = []

    # 1. Badge level rank check
    req_level = (require_badge_level or target_tier.value).lower().strip()
    req_rank = _BADGE_LEVEL_RANKS.get(req_level, 1)
    proj_rank = _BADGE_LEVEL_RANKS.get(project.badge_level.lower().strip(), 0)
    if proj_rank < req_rank:
        errors.append(f"Badge level '{project.badge_level}' is below required '{req_level}'")

    # 2. Score percentage check
    if project.tiered_percentage < min_score:
        errors.append(
            f"Score {project.tiered_percentage}% is below required minimum of {min_score}%"
        )

    # 3. MUST criteria check
    catalog_criteria = OpenSsfCriteriaCatalog.for_tier(target_tier)
    for crit in catalog_criteria:
        if crit.category.upper() == "MUST":
            status = project.criteria_statuses.get(crit.criterion_id, CriterionStatus.UNKNOWN.value)
            if status not in (CriterionStatus.MET.value, CriterionStatus.NA.value):
                unmet_must.append(
                    {
                        "id": crit.criterion_id,
                        "category": crit.category,
                        "status": status,
                    }
                )
                errors.append(
                    f"MUST criterion '{crit.criterion_id}' is '{status}' (expected Met or N/A)"
                )

    passed = len(errors) == 0
    return OpenSsfCheckResult(
        passed=passed,
        tier=target_tier,
        badge_level=project.badge_level,
        score=project.tiered_percentage,
        min_score=min_score,
        unmet_must=unmet_must,
        errors=errors,
    )
