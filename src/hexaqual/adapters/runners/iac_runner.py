"""Subprocess and filesystem runner adapter implementing IacAuditorPort.

Notes/Architectural Intent:
    Discovers OpenTofu/Terraform modules, Dockerfiles, Kubernetes/Helm manifests,
    and shell scripts while skipping build/VCS/virtualenv directories. Executes
    ``tofu``/``terraform``, ``tflint``, ``trivy``, ``checkov``, ``hadolint``, and
    ``shellcheck`` strictly via argument lists (never ``shell=True``) and normalizes
    JSON diagnostics into domain ``IacToolResult`` and ``IacFinding`` objects.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from hexaqual.domain.iac import (
    IacAssetInventory,
    IacCategory,
    IacCheckStatus,
    IacFinding,
    IacSeverity,
    IacToolAvailability,
    IacToolName,
    IacToolResult,
    normalize_severity,
)
from hexaqual.ports.iac import IacAuditorPort

__all__ = [
    "IGNORED_IAC_DIRS",
    "SubprocessIacAuditorAdapter",
]

IGNORED_IAC_DIRS: frozenset[str] = frozenset(
    {
        ".benchmarks",
        ".cache",
        ".complexipy_cache",
        ".git",
        ".hexaflow",
        ".hg",
        ".hypothesis",
        ".import_linter_cache",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".terraform",
        ".terragrunt-cache",
        ".tox",
        ".venv",
        "build",
        "coverage",
        "dist",
        "graphify-out",
        "node_modules",
        "site",
        "venv",
    }
)

_K8S_API_VERSION_RE = re.compile(r"^apiVersion:\s+\S+", re.MULTILINE)
_K8S_KIND_RE = re.compile(r"^kind:\s+\S+", re.MULTILINE)


def _format_rel_path(path: Path, repo_root: Path) -> str:
    """Format a path relative to ``repo_root`` when possible."""
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _execute_subprocess(
    cmd: list[str],
    cwd: Path | None = None,
) -> tuple[int, str, str, float]:
    """Execute a subprocess safely without a shell and measure wall-clock duration.

    Args:
        cmd: Argument vector with binary at index 0.
        cwd: Optional working directory.

    Returns:
        Tuple of ``(returncode, stdout, stderr, duration_seconds)``.
    """
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr, time.perf_counter() - start
    except OSError as exc:
        return 1, "", str(exc), time.perf_counter() - start


def _resolve_tofu_binary() -> tuple[str, str | None]:
    """Resolve OpenTofu (``tofu``) or fallback Terraform (``terraform``) binary."""
    tofu_path = shutil.which("tofu")
    if tofu_path:
        return "tofu", tofu_path
    tf_path = shutil.which("terraform")
    if tf_path:
        return "terraform", tf_path
    return "tofu", None


def _resolve_tool_binary(tool: IacToolName) -> tuple[str, str | None]:
    """Resolve binary name and path for a given ``IacToolName``."""
    if tool in (IacToolName.TOFU_FMT, IacToolName.TOFU_VALIDATE):
        return _resolve_tofu_binary()
    if tool == IacToolName.CHECKOV:
        venv_bin = Path(sys.executable).parent / "checkov"
        if venv_bin.is_file():
            return "checkov", str(venv_bin)
        return "checkov", shutil.which("checkov")

    binary_map = {
        IacToolName.TFLINT: "tflint",
        IacToolName.TRIVY: "trivy",
        IacToolName.HADOLINT: "hadolint",
        IacToolName.SHELLCHECK: "shellcheck",
    }
    binary = binary_map[tool]
    return binary, shutil.which(binary)


def _missing_binary_result(
    tool: IacToolName,
    category: IacCategory,
    binary: str,
    strict: bool,
) -> IacToolResult:
    """Construct a SKIP or FAIL result when an external IaC tool binary is unavailable."""
    msg = f"'{binary}' binary not found on PATH"
    if strict:
        return IacToolResult(
            tool=tool,
            category=category,
            status=IacCheckStatus.FAIL,
            details=msg,
            error_output=f"{msg}; strict mode requires all active IaC tools to be installed.",
        )
    return IacToolResult(
        tool=tool,
        category=category,
        status=IacCheckStatus.SKIP,
        details=msg,
    )


def _no_assets_result(tool: IacToolName, category: IacCategory, label: str) -> IacToolResult:
    """Construct a SKIP result when no matching IaC artifacts were discovered."""
    return IacToolResult(
        tool=tool,
        category=category,
        status=IacCheckStatus.SKIP,
        details=f"No {label} discovered",
    )


def _deduplicate_ancestor_dirs(dirs: tuple[Path, ...]) -> tuple[Path, ...]:
    """Remove directories that are already nested under another directory in ``dirs``."""
    ordered = sorted({d.resolve() for d in dirs}, key=lambda p: (len(p.parts), str(p)))
    kept: list[Path] = []
    for candidate in ordered:
        if any(parent == candidate or parent in candidate.parents for parent in kept):
            continue
        kept.append(candidate)
    return tuple(sorted(kept))


def _resolve_scan_roots(repo_root: Path, paths: tuple[Path, ...]) -> list[Path]:
    """Resolve discovery roots relative to ``repo_root`` while preserving order."""
    if not paths:
        return [repo_root.resolve()]
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        resolved = raw.resolve() if raw.is_absolute() else (repo_root / raw).resolve()
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            roots.append(resolved)
    return roots


def _iter_candidate_files(scan_roots: list[Path]) -> list[Path]:
    """Collect candidate files across ``scan_roots`` skipping ``IGNORED_IAC_DIRS``."""
    collected: list[Path] = []
    seen: set[Path] = set()
    for root in scan_roots:
        if root.is_file():
            if not any(part in IGNORED_IAC_DIRS for part in root.parts) and root not in seen:
                seen.add(root)
                collected.append(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in IGNORED_IAC_DIRS)
            base = Path(dirpath)
            for fname in sorted(filenames):
                candidate = base / fname
                if candidate not in seen:
                    seen.add(candidate)
                    collected.append(candidate)
    return sorted(collected)


def _is_k8s_manifest(path: Path, repo_root: Path) -> bool:
    """Heuristically identify Kubernetes YAML manifests without scanning workflows."""
    try:
        rel_parts = path.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        rel_parts = path.parts
    if ".github" in rel_parts or path.name.startswith(".pre-commit"):
        return False

    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            head_lines = [handle.readline() for _ in range(64)]
    except OSError:
        return False

    snippet = "".join(head_lines)
    return bool(_K8S_API_VERSION_RE.search(snippet) and _K8S_KIND_RE.search(snippet))


def _is_dockerfile(name: str) -> bool:
    """Return True when filename matches standard Dockerfile naming conventions."""
    return (
        name == "Dockerfile"
        or name.startswith("Dockerfile.")
        or name.lower().endswith(".dockerfile")
    )


def _parse_tofu_fmt_paths(stdout: str, scan_dir: Path, repo_root: Path) -> list[str]:
    """Extract repo-relative unformatted file paths from ``tofu fmt`` output."""
    paths: list[str] = []
    seen: set[str] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("---", "+++", "@@", "+", "-", "diff ", "\\")):
            continue
        if line.endswith((".tf", ".tfvars", ".tf.json")):
            candidate = Path(line) if Path(line).is_absolute() else (scan_dir / line)
            rel = _format_rel_path(candidate, repo_root)
            if rel not in seen:
                seen.add(rel)
                paths.append(rel)
    return paths


def _parse_tofu_validate_json(
    stdout: str,
    tf_dir: Path,
    repo_root: Path,
) -> list[IacFinding]:
    """Parse ``tofu validate -json`` diagnostics into normalized ``IacFinding`` objects."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []

    findings: list[IacFinding] = []
    for diag in payload.get("diagnostics", []) or []:
        if not isinstance(diag, dict):
            continue
        rng = diag.get("range") or {}
        filename = rng.get("filename")
        start = rng.get("start") or {}
        line = start.get("line") if isinstance(start.get("line"), int) else None
        target = (tf_dir / str(filename)) if filename else tf_dir
        summary = str(diag.get("summary", "")).strip()
        detail = str(diag.get("detail", "")).strip()
        msg = f"{summary}: {detail}".strip(": ") if detail else summary
        findings.append(
            IacFinding(
                tool=IacToolName.TOFU_VALIDATE,
                category=IacCategory.OPENTOFU,
                file_path=_format_rel_path(target, repo_root),
                line=line,
                rule_id="tofu-validate",
                severity=normalize_severity(str(diag.get("severity", "error"))),
                message=msg or "OpenTofu validation diagnostic",
            )
        )
    return findings


def _parse_tflint_json(stdout: str, tf_dir: Path, repo_root: Path) -> list[IacFinding]:
    """Parse ``tflint --format json`` issues and errors into ``IacFinding`` objects."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []

    findings: list[IacFinding] = []
    for issue in payload.get("issues", []) or []:
        if not isinstance(issue, dict):
            continue
        rule = issue.get("rule") or {}
        rng = issue.get("range") or {}
        start = rng.get("start") or {}
        filename = rng.get("filename")
        target = (tf_dir / str(filename)) if filename else tf_dir
        line = start.get("line") if isinstance(start.get("line"), int) else None
        findings.append(
            IacFinding(
                tool=IacToolName.TFLINT,
                category=IacCategory.OPENTOFU,
                file_path=_format_rel_path(target, repo_root),
                line=line,
                rule_id=str(rule.get("name", "tflint")),
                severity=normalize_severity(str(rule.get("severity", "warning"))),
                message=str(issue.get("message", "")),
            )
        )
    for err in payload.get("errors", []) or []:
        if not isinstance(err, dict):
            continue
        findings.append(
            IacFinding(
                tool=IacToolName.TFLINT,
                category=IacCategory.OPENTOFU,
                file_path=_format_rel_path(tf_dir, repo_root),
                rule_id="tflint-error",
                severity=normalize_severity(str(err.get("severity", "error"))),
                message=str(err.get("message", "TFLint execution error")),
            )
        )
    return findings


def _infer_category_from_path(file_path: str) -> IacCategory:
    """Infer ``IacCategory`` from a target path string."""
    lower = file_path.lower()
    if lower.endswith("dockerfile") or ".dockerfile" in lower or "dockerfile." in lower:
        return IacCategory.DOCKER
    if lower.endswith((".yaml", ".yml")):
        return IacCategory.KUBERNETES
    if lower.endswith((".sh", ".bash")):
        return IacCategory.SHELL
    return IacCategory.OPENTOFU


def _extract_trivy_result_findings(
    result: dict[str, Any],
    base_dir: Path,
    scan_target: Path,
    repo_root: Path,
) -> list[IacFinding]:
    """Extract normalized misconfiguration findings from a single Trivy Result entry."""
    raw_target = str(result.get("Target", "")).strip()
    resolved_target = (
        (base_dir / raw_target)
        if raw_target and not Path(raw_target).is_absolute()
        else Path(raw_target or scan_target)
    )
    rel_path = _format_rel_path(resolved_target, repo_root)
    category = _infer_category_from_path(rel_path)

    findings: list[IacFinding] = []
    for misconf in result.get("Misconfigurations", []) or []:
        if not isinstance(misconf, dict):
            continue
        status = str(misconf.get("Status", "FAIL")).upper()
        if status not in ("", "FAIL"):
            continue
        cause = misconf.get("CauseMetadata") or {}
        start_line = cause.get("StartLine")
        findings.append(
            IacFinding(
                tool=IacToolName.TRIVY,
                category=category,
                file_path=rel_path,
                line=start_line if isinstance(start_line, int) else None,
                rule_id=str(misconf.get("ID") or misconf.get("AVDID") or "trivy-misconfig"),
                severity=normalize_severity(str(misconf.get("Severity", "MEDIUM"))),
                message=str(misconf.get("Message") or misconf.get("Title") or ""),
                remediation=str(misconf.get("Resolution", "")),
            )
        )
    return findings


def _parse_trivy_json(stdout: str, scan_target: Path, repo_root: Path) -> list[IacFinding]:
    """Parse ``trivy config --format json`` misconfigurations into ``IacFinding`` objects."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []

    findings: list[IacFinding] = []
    base_dir = scan_target if scan_target.is_dir() else scan_target.parent
    for result in payload.get("Results", []) or []:
        if isinstance(result, dict):
            findings.extend(
                _extract_trivy_result_findings(result, base_dir, scan_target, repo_root)
            )
    return findings


def _extract_checkov_block_findings(
    block: dict[str, Any],
    base_dir: Path,
    scan_target: Path,
    repo_root: Path,
) -> list[IacFinding]:
    """Extract normalized failed checks from a single Checkov result block."""
    results = block.get("results") or {}
    if not isinstance(results, dict):
        return []

    findings: list[IacFinding] = []
    for chk in results.get("failed_checks", []) or []:
        if not isinstance(chk, dict):
            continue
        raw_file = str(chk.get("repo_file_path") or chk.get("file_path") or "").lstrip("/")
        resolved_file = (base_dir / raw_file) if raw_file else scan_target
        rel_path = _format_rel_path(resolved_file, repo_root)
        line_range = chk.get("file_line_range") or []
        line = line_range[0] if line_range and isinstance(line_range[0], int) else None
        findings.append(
            IacFinding(
                tool=IacToolName.CHECKOV,
                category=_infer_category_from_path(rel_path),
                file_path=rel_path,
                line=line,
                rule_id=str(chk.get("check_id", "checkov")),
                severity=normalize_severity(str(chk.get("severity") or "MEDIUM")),
                message=str(chk.get("check_name", "")),
                remediation=str(chk.get("guideline") or ""),
            )
        )
    return findings


def _parse_checkov_json(stdout: str, scan_target: Path, repo_root: Path) -> list[IacFinding]:
    """Parse ``checkov -o json`` output supporting both single dict and list payloads."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        blocks = [payload]
    elif isinstance(payload, list):
        blocks = [b for b in payload if isinstance(b, dict)]
    else:
        return []

    findings: list[IacFinding] = []
    base_dir = scan_target if scan_target.is_dir() else scan_target.parent
    for block in blocks:
        findings.extend(_extract_checkov_block_findings(block, base_dir, scan_target, repo_root))
    return findings


def _parse_hadolint_json(stdout: str, repo_root: Path) -> list[IacFinding]:
    """Parse ``hadolint --format json`` array items into ``IacFinding`` objects."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []

    findings: list[IacFinding] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_file = str(item.get("file", "Dockerfile"))
        rel_path = _format_rel_path(
            Path(raw_file) if Path(raw_file).is_absolute() else (repo_root / raw_file), repo_root
        )
        line = item.get("line")
        findings.append(
            IacFinding(
                tool=IacToolName.HADOLINT,
                category=IacCategory.DOCKER,
                file_path=rel_path,
                line=line if isinstance(line, int) else None,
                rule_id=str(item.get("code", "")),
                severity=normalize_severity(str(item.get("level", "warning"))),
                message=str(item.get("message", "")),
            )
        )
    return findings


def _parse_shellcheck_json(stdout: str, repo_root: Path) -> list[IacFinding]:
    """Parse ``shellcheck -f json`` array items into ``IacFinding`` objects."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []

    findings: list[IacFinding] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_file = str(item.get("file", ""))
        rel_path = _format_rel_path(
            Path(raw_file) if Path(raw_file).is_absolute() else (repo_root / raw_file), repo_root
        )
        line = item.get("line")
        code = item.get("code")
        rule_id = f"SC{code}" if code is not None else "shellcheck"
        findings.append(
            IacFinding(
                tool=IacToolName.SHELLCHECK,
                category=IacCategory.SHELL,
                file_path=rel_path,
                line=line if isinstance(line, int) else None,
                rule_id=rule_id,
                severity=normalize_severity(str(item.get("level", "warning"))),
                message=str(item.get("message", "")),
            )
        )
    return findings


class SubprocessIacAuditorAdapter(IacAuditorPort):
    """Concrete ``IacAuditorPort`` adapter invoking external IaC tools safely."""

    def discover_assets(
        self,
        repo_root: Path,
        paths: tuple[Path, ...] = (),
    ) -> IacAssetInventory:
        """Discover OpenTofu/Terraform, Docker, Kubernetes/Helm, and shell assets.

        Args:
            repo_root: Repository root directory.
            paths: Optional explicit file or directory filters.

        Returns:
            Sorted ``IacAssetInventory`` of discovered artifacts.

        Notes/Architectural Intent:
            Excludes VCS, build, and virtual environment directories so discovery
            stays fast on large Python monorepos.
        """
        resolved_root = repo_root.resolve()
        scan_roots = _resolve_scan_roots(resolved_root, paths)
        candidates = _iter_candidate_files(scan_roots)

        tofu_dirs: set[Path] = set()
        tofu_files: list[Path] = []
        dockerfiles: list[Path] = []
        k8s_charts: set[Path] = set()
        k8s_files: list[Path] = []
        shell_scripts: list[Path] = []

        for file_path in candidates:
            name = file_path.name
            if name.endswith((".tf", ".tfvars", ".tf.json")):
                tofu_files.append(file_path)
                if name.endswith((".tf", ".tf.json")):
                    tofu_dirs.add(file_path.parent)
            elif _is_dockerfile(name):
                dockerfiles.append(file_path)
            elif name == "Chart.yaml":
                k8s_charts.add(file_path.parent)
            elif name.endswith((".yaml", ".yml")) and _is_k8s_manifest(file_path, resolved_root):
                k8s_files.append(file_path)
            elif name.endswith((".sh", ".bash")):
                shell_scripts.append(file_path)

        filtered_k8s_files = [
            f for f in k8s_files if not any(chart in f.parents for chart in k8s_charts)
        ]
        all_k8s = sorted([*k8s_charts, *filtered_k8s_files])

        return IacAssetInventory(
            tofu_dirs=tuple(sorted(tofu_dirs)),
            tofu_files=tuple(sorted(tofu_files)),
            dockerfiles=tuple(sorted(dockerfiles)),
            k8s_paths=tuple(all_k8s),
            shell_scripts=tuple(sorted(shell_scripts)),
        )

    def check_tool_availability(self) -> tuple[IacToolAvailability, ...]:
        """Inspect installation availability for all supported IaC tool binaries.

        Returns:
            Tuple of ``IacToolAvailability`` records across all 7 gate tools.
        """
        records: list[IacToolAvailability] = []
        for tool in (
            IacToolName.TOFU_FMT,
            IacToolName.TOFU_VALIDATE,
            IacToolName.TFLINT,
            IacToolName.TRIVY,
            IacToolName.CHECKOV,
            IacToolName.HADOLINT,
            IacToolName.SHELLCHECK,
        ):
            binary, resolved = _resolve_tool_binary(tool)
            records.append(
                IacToolAvailability(
                    tool=tool,
                    binary=binary,
                    installed=resolved is not None,
                    resolved_path=resolved or "",
                )
            )
        return tuple(records)

    def run_tofu_fmt(
        self,
        repo_root: Path,
        tofu_dirs: tuple[Path, ...],
        fix: bool = False,
        strict: bool = False,
    ) -> IacToolResult:
        """Check or apply OpenTofu/Terraform canonical HCL formatting.

        Args:
            repo_root: Repository root directory.
            tofu_dirs: Discovered OpenTofu/Terraform directories.
            fix: Whether to run ``fmt -recursive`` prior to verification.
            strict: Whether missing ``tofu``/``terraform`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` detailing formatting compliance and any unformatted files.
        """
        if not tofu_dirs:
            return _no_assets_result(
                IacToolName.TOFU_FMT, IacCategory.OPENTOFU, "OpenTofu/Terraform files"
            )

        binary, resolved = _resolve_tofu_binary()
        if resolved is None:
            return _missing_binary_result(
                IacToolName.TOFU_FMT, IacCategory.OPENTOFU, binary, strict
            )

        scan_dirs = _deduplicate_ancestor_dirs(tofu_dirs)
        total_duration = 0.0
        findings: list[IacFinding] = []
        err_chunks: list[str] = []

        for scan_dir in scan_dirs:
            if fix:
                _, _, _, fix_dur = _execute_subprocess(
                    [resolved, "fmt", "-recursive", str(scan_dir)]
                )
                total_duration += fix_dur
            code, out, err, dur = _execute_subprocess(
                [resolved, "fmt", "-check", "-list=true", "-diff", "-recursive", str(scan_dir)]
            )
            total_duration += dur
            if code != 0:
                unformatted = _parse_tofu_fmt_paths(out, scan_dir, repo_root)
                if not unformatted:
                    unformatted = [_format_rel_path(scan_dir, repo_root)]
                for rel_file in unformatted:
                    findings.append(
                        IacFinding(
                            tool=IacToolName.TOFU_FMT,
                            category=IacCategory.OPENTOFU,
                            file_path=rel_file,
                            rule_id="tofu-fmt",
                            severity=IacSeverity.LOW,
                            message=f"File is not formatted according to `{binary} fmt`",
                            remediation=f"Run `{binary} fmt -recursive` or `hexaqual iac fmt --fix`",
                        )
                    )
                combined = (out + "\n" + err).strip()
                if combined:
                    err_chunks.append(combined)

        if findings:
            return IacToolResult(
                tool=IacToolName.TOFU_FMT,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.FAIL,
                duration=total_duration,
                targets_checked=len(scan_dirs),
                findings=tuple(findings),
                details=f"{len(findings)} unformatted file(s)",
                error_output="\n\n".join(err_chunks),
            )
        return IacToolResult(
            tool=IacToolName.TOFU_FMT,
            category=IacCategory.OPENTOFU,
            status=IacCheckStatus.PASS,
            duration=total_duration,
            targets_checked=len(scan_dirs),
            details=f"Formatting clean ({len(scan_dirs)} root(s))",
        )

    @staticmethod
    def _validate_single_tofu_dir(
        resolved: str,
        binary: str,
        tf_dir: Path,
        repo_root: Path,
        init_tofu: bool,
    ) -> tuple[bool, bool, float, list[IacFinding], str]:
        """Validate one OpenTofu/Terraform module directory, optionally running offline init."""
        duration = 0.0
        if not (tf_dir / ".terraform").is_dir():
            if not init_tofu:
                return False, True, duration, [], ""
            init_code, init_out, init_err, init_dur = _execute_subprocess(
                [resolved, "init", "-backend=false", "-input=false", "-no-color"],
                cwd=tf_dir,
            )
            duration += init_dur
            if init_code != 0:
                msg = (init_err or init_out or f"{binary} init failed").strip()
                finding = IacFinding(
                    tool=IacToolName.TOFU_VALIDATE,
                    category=IacCategory.OPENTOFU,
                    file_path=_format_rel_path(tf_dir, repo_root),
                    rule_id="tofu-init",
                    severity=IacSeverity.HIGH,
                    message=msg,
                )
                return False, False, duration, [finding], msg

        code, out, err, dur = _execute_subprocess([resolved, "validate", "-json"], cwd=tf_dir)
        duration += dur
        parsed = _parse_tofu_validate_json(out, tf_dir, repo_root)
        if code != 0 and not parsed:
            msg = (err or out or f"{binary} validate failed").strip()
            parsed.append(
                IacFinding(
                    tool=IacToolName.TOFU_VALIDATE,
                    category=IacCategory.OPENTOFU,
                    file_path=_format_rel_path(tf_dir, repo_root),
                    rule_id="tofu-validate",
                    severity=IacSeverity.HIGH,
                    message=msg,
                )
            )
        err_text = err.strip() if (code != 0 or parsed) else ""
        return True, False, duration, (parsed if (code != 0 or parsed) else []), err_text

    def run_tofu_validate(
        self,
        repo_root: Path,
        tofu_dirs: tuple[Path, ...],
        init_tofu: bool = False,
        strict: bool = False,
    ) -> IacToolResult:
        """Validate OpenTofu/Terraform modules offline without accessing remote state.

        Args:
            repo_root: Repository root directory.
            tofu_dirs: Discovered OpenTofu/Terraform directories.
            init_tofu: Whether to run ``init -backend=false`` on uninitialized modules.
            strict: Whether missing binary or uninitialized modules fail instead of skip.

        Returns:
            ``IacToolResult`` with validation status and JSON diagnostic findings.
        """
        if not tofu_dirs:
            return _no_assets_result(
                IacToolName.TOFU_VALIDATE, IacCategory.OPENTOFU, "OpenTofu/Terraform modules"
            )

        binary, resolved = _resolve_tofu_binary()
        if resolved is None:
            return _missing_binary_result(
                IacToolName.TOFU_VALIDATE, IacCategory.OPENTOFU, binary, strict
            )

        unique_dirs = tuple(sorted({d.resolve() for d in tofu_dirs}))
        total_duration = 0.0
        findings: list[IacFinding] = []
        err_chunks: list[str] = []
        checked = 0
        uninitialized_count = 0

        for tf_dir in unique_dirs:
            was_checked, was_uninit, dur, dir_findings, err_txt = self._validate_single_tofu_dir(
                resolved, binary, tf_dir, repo_root, init_tofu
            )
            total_duration += dur
            if was_checked:
                checked += 1
            if was_uninit:
                uninitialized_count += 1
            findings.extend(dir_findings)
            if err_txt:
                err_chunks.append(err_txt)

        if findings:
            return IacToolResult(
                tool=IacToolName.TOFU_VALIDATE,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.FAIL,
                duration=total_duration,
                targets_checked=checked,
                findings=tuple(findings),
                details=f"{len(findings)} validation diagnostic(s)",
                error_output="\n\n".join(err_chunks),
            )

        if checked == 0 and uninitialized_count > 0:
            msg = "Uninitialized OpenTofu module(s); run 'tofu init -backend=false' or pass --init"
            return IacToolResult(
                tool=IacToolName.TOFU_VALIDATE,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.FAIL if strict else IacCheckStatus.SKIP,
                duration=total_duration,
                targets_checked=0,
                details=msg,
                error_output=msg if strict else "",
            )

        extra = f" ({uninitialized_count} uninitialized skipped)" if uninitialized_count else ""
        return IacToolResult(
            tool=IacToolName.TOFU_VALIDATE,
            category=IacCategory.OPENTOFU,
            status=IacCheckStatus.PASS,
            duration=total_duration,
            targets_checked=checked,
            details=f"Valid across {checked} module(s){extra}",
        )

    def run_tflint(
        self,
        repo_root: Path,
        tofu_dirs: tuple[Path, ...],
        strict: bool = False,
    ) -> IacToolResult:
        """Run TFLint across OpenTofu/Terraform module directories.

        Args:
            repo_root: Repository root directory.
            tofu_dirs: Discovered OpenTofu/Terraform directories.
            strict: Whether missing ``tflint`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing TFLint findings.
        """
        if not tofu_dirs:
            return _no_assets_result(
                IacToolName.TFLINT, IacCategory.OPENTOFU, "OpenTofu/Terraform modules"
            )

        binary, resolved = _resolve_tool_binary(IacToolName.TFLINT)
        if resolved is None:
            return _missing_binary_result(IacToolName.TFLINT, IacCategory.OPENTOFU, binary, strict)

        unique_dirs = tuple(sorted({d.resolve() for d in tofu_dirs}))
        total_duration = 0.0
        findings: list[IacFinding] = []
        err_chunks: list[str] = []

        for tf_dir in unique_dirs:
            code, out, err, dur = _execute_subprocess([resolved, "--format", "json"], cwd=tf_dir)
            total_duration += dur
            parsed = _parse_tflint_json(out, tf_dir, repo_root)
            if code != 0 and not parsed:
                msg = (err or out or "tflint failed").strip()
                parsed.append(
                    IacFinding(
                        tool=IacToolName.TFLINT,
                        category=IacCategory.OPENTOFU,
                        file_path=_format_rel_path(tf_dir, repo_root),
                        rule_id="tflint",
                        severity=IacSeverity.MEDIUM,
                        message=msg,
                    )
                )
            findings.extend(parsed)
            if err.strip():
                err_chunks.append(err.strip())

        if findings:
            return IacToolResult(
                tool=IacToolName.TFLINT,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.FAIL,
                duration=total_duration,
                targets_checked=len(unique_dirs),
                findings=tuple(findings),
                details=f"{len(findings)} TFLint issue(s)",
                error_output="\n\n".join(err_chunks),
            )
        return IacToolResult(
            tool=IacToolName.TFLINT,
            category=IacCategory.OPENTOFU,
            status=IacCheckStatus.PASS,
            duration=total_duration,
            targets_checked=len(unique_dirs),
            details=f"No TFLint issues ({len(unique_dirs)} module(s))",
        )

    def run_trivy(
        self,
        repo_root: Path,
        scan_paths: tuple[Path, ...],
        severity: str = "HIGH,CRITICAL",
        strict: bool = False,
    ) -> IacToolResult:
        """Execute Trivy misconfiguration scanning across discovered IaC paths.

        Args:
            repo_root: Repository root directory.
            scan_paths: Target files and directories to scan.
            severity: Comma-separated Trivy severity filter.
            strict: Whether missing ``trivy`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing Trivy misconfiguration findings.
        """
        if not scan_paths:
            return _no_assets_result(IacToolName.TRIVY, IacCategory.OPENTOFU, "IaC config targets")

        binary, resolved = _resolve_tool_binary(IacToolName.TRIVY)
        if resolved is None:
            return _missing_binary_result(IacToolName.TRIVY, IacCategory.OPENTOFU, binary, strict)

        targets = _deduplicate_ancestor_dirs(scan_paths)
        total_duration = 0.0
        findings: list[IacFinding] = []
        err_chunks: list[str] = []
        failed = False

        for target in targets:
            code, out, err, dur = _execute_subprocess(
                [
                    resolved,
                    "config",
                    "--format",
                    "json",
                    "--severity",
                    severity,
                    "--exit-code",
                    "1",
                    str(target),
                ]
            )
            total_duration += dur
            parsed = _parse_trivy_json(out, target, repo_root)
            findings.extend(parsed)
            if code != 0:
                failed = True
                if not parsed and err.strip():
                    err_chunks.append(err.strip())

        if failed or findings:
            return IacToolResult(
                tool=IacToolName.TRIVY,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.FAIL,
                duration=total_duration,
                targets_checked=len(targets),
                findings=tuple(findings),
                details=f"{len(findings)} misconfiguration(s) ({severity})",
                error_output="\n\n".join(err_chunks),
            )
        return IacToolResult(
            tool=IacToolName.TRIVY,
            category=IacCategory.OPENTOFU,
            status=IacCheckStatus.PASS,
            duration=total_duration,
            targets_checked=len(targets),
            details=f"No {severity} misconfigurations ({len(targets)} target(s))",
        )

    def run_checkov(
        self,
        repo_root: Path,
        scan_paths: tuple[Path, ...],
        strict: bool = False,
    ) -> IacToolResult:
        """Execute Checkov policy checks across discovered IaC paths.

        Args:
            repo_root: Repository root directory.
            scan_paths: Target files and directories to scan.
            strict: Whether missing ``checkov`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing failed Checkov policy checks.
        """
        if not scan_paths:
            return _no_assets_result(
                IacToolName.CHECKOV, IacCategory.OPENTOFU, "IaC config targets"
            )

        binary, resolved = _resolve_tool_binary(IacToolName.CHECKOV)
        if resolved is None:
            return _missing_binary_result(IacToolName.CHECKOV, IacCategory.OPENTOFU, binary, strict)

        targets = _deduplicate_ancestor_dirs(scan_paths)
        total_duration = 0.0
        findings: list[IacFinding] = []
        err_chunks: list[str] = []
        failed = False

        for target in targets:
            flag = "-d" if target.is_dir() else "-f"
            code, out, err, dur = _execute_subprocess(
                [resolved, flag, str(target), "-o", "json", "--quiet", "--compact"]
            )
            total_duration += dur
            parsed = _parse_checkov_json(out, target, repo_root)
            findings.extend(parsed)
            if code != 0:
                failed = True
                if not parsed and err.strip():
                    err_chunks.append(err.strip())

        if failed or findings:
            return IacToolResult(
                tool=IacToolName.CHECKOV,
                category=IacCategory.OPENTOFU,
                status=IacCheckStatus.FAIL,
                duration=total_duration,
                targets_checked=len(targets),
                findings=tuple(findings),
                details=f"{len(findings)} Checkov policy failure(s)",
                error_output="\n\n".join(err_chunks),
            )
        return IacToolResult(
            tool=IacToolName.CHECKOV,
            category=IacCategory.OPENTOFU,
            status=IacCheckStatus.PASS,
            duration=total_duration,
            targets_checked=len(targets),
            details=f"Checkov policies clean ({len(targets)} target(s))",
        )

    def run_hadolint(
        self,
        repo_root: Path,
        dockerfiles: tuple[Path, ...],
        failure_threshold: str = "warning",
        strict: bool = False,
    ) -> IacToolResult:
        """Lint discovered Dockerfiles via ``hadolint --format json``.

        Args:
            repo_root: Repository root directory.
            dockerfiles: Discovered Dockerfile paths.
            failure_threshold: Hadolint ``--failure-threshold`` floor.
            strict: Whether missing ``hadolint`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing Hadolint findings and pass/fail outcome.
        """
        if not dockerfiles:
            return _no_assets_result(IacToolName.HADOLINT, IacCategory.DOCKER, "Dockerfiles")

        binary, resolved = _resolve_tool_binary(IacToolName.HADOLINT)
        if resolved is None:
            return _missing_binary_result(IacToolName.HADOLINT, IacCategory.DOCKER, binary, strict)

        cmd = [
            resolved,
            "--format",
            "json",
            "--failure-threshold",
            failure_threshold,
            *(str(df) for df in dockerfiles),
        ]
        code, out, err, dur = _execute_subprocess(cmd, cwd=repo_root)
        findings = _parse_hadolint_json(out, repo_root)

        if code != 0:
            return IacToolResult(
                tool=IacToolName.HADOLINT,
                category=IacCategory.DOCKER,
                status=IacCheckStatus.FAIL,
                duration=dur,
                targets_checked=len(dockerfiles),
                findings=tuple(findings),
                details=f"{len(findings)} Dockerfile lint finding(s) (threshold: {failure_threshold})",
                error_output=err.strip() if not findings else "",
            )

        details = f"Dockerfiles clean ({len(dockerfiles)} file(s))"
        if findings:
            details += f" ({len(findings)} advisory notice(s) below {failure_threshold})"
        return IacToolResult(
            tool=IacToolName.HADOLINT,
            category=IacCategory.DOCKER,
            status=IacCheckStatus.PASS,
            duration=dur,
            targets_checked=len(dockerfiles),
            findings=tuple(findings),
            details=details,
        )

    def run_shellcheck(
        self,
        repo_root: Path,
        shell_scripts: tuple[Path, ...],
        severity: str = "warning",
        strict: bool = False,
    ) -> IacToolResult:
        """Lint discovered shell scripts via ``shellcheck -f json``.

        Args:
            repo_root: Repository root directory.
            shell_scripts: Discovered shell script paths.
            severity: Minimum ShellCheck severity threshold (``-S``).
            strict: Whether missing ``shellcheck`` binary fails instead of skip.

        Returns:
            ``IacToolResult`` containing ShellCheck diagnostics.
        """
        if not shell_scripts:
            return _no_assets_result(IacToolName.SHELLCHECK, IacCategory.SHELL, "shell scripts")

        binary, resolved = _resolve_tool_binary(IacToolName.SHELLCHECK)
        if resolved is None:
            return _missing_binary_result(IacToolName.SHELLCHECK, IacCategory.SHELL, binary, strict)

        cmd = [
            resolved,
            "-f",
            "json",
            "-S",
            severity,
            *(str(s) for s in shell_scripts),
        ]
        code, out, err, dur = _execute_subprocess(cmd, cwd=repo_root)
        findings = _parse_shellcheck_json(out, repo_root)

        if code != 0:
            return IacToolResult(
                tool=IacToolName.SHELLCHECK,
                category=IacCategory.SHELL,
                status=IacCheckStatus.FAIL,
                duration=dur,
                targets_checked=len(shell_scripts),
                findings=tuple(findings),
                details=f"{len(findings)} shell script issue(s) (severity >= {severity})",
                error_output=err.strip() if not findings else "",
            )

        return IacToolResult(
            tool=IacToolName.SHELLCHECK,
            category=IacCategory.SHELL,
            status=IacCheckStatus.PASS,
            duration=dur,
            targets_checked=len(shell_scripts),
            findings=tuple(findings),
            details=f"Shell scripts clean ({len(shell_scripts)} file(s))",
        )
