"""CQRS command handlers for auto-detecting Infrastructure-as-Code audits.

Notes/Architectural Intent:
    Orchestrates IaC artifact discovery and tool execution across the IacAuditorPort
    boundary, producing immutable IacInventoryReport and IacAuditReport domain models.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from hexaqual.domain.iac import (
    DiscoverIacAssetsCommand,
    IacAssetInventory,
    IacAuditReport,
    IacCheckStatus,
    IacInventoryReport,
    IacToolName,
    IacToolResult,
    RunIacAuditCommand,
)
from hexaqual.ports.iac import IacAuditorPort

__all__ = [
    "DiscoverIacAssetsHandler",
    "RunIacAuditHandler",
]

_CANONICAL_TOOL_ORDER: tuple[IacToolName, ...] = (
    IacToolName.TOFU_FMT,
    IacToolName.TOFU_VALIDATE,
    IacToolName.TFLINT,
    IacToolName.TRIVY,
    IacToolName.CHECKOV,
    IacToolName.HADOLINT,
    IacToolName.SHELLCHECK,
)


def _compute_security_scan_paths(inventory: IacAssetInventory) -> tuple[Path, ...]:
    """Deduplicate discovery targets suitable for Trivy/Checkov config scanning."""
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in (*inventory.tofu_dirs, *inventory.dockerfiles, *inventory.k8s_paths):
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            ordered.append(resolved)
    return tuple(ordered)


class DiscoverIacAssetsHandler:
    """Handler discovering IaC assets and external tool readiness."""

    def __init__(self, auditor: IacAuditorPort) -> None:
        """Initialize handler with concrete ``IacAuditorPort`` adapter.

        Args:
            auditor: Concrete ``IacAuditorPort`` implementation.
        """
        self._auditor = auditor

    def handle(self, command: DiscoverIacAssetsCommand) -> IacInventoryReport:
        """Execute IaC asset discovery and binary availability inspection.

        Args:
            command: ``DiscoverIacAssetsCommand`` specifying repo root and optional paths.

        Returns:
            Populated ``IacInventoryReport`` domain aggregate.
        """
        inventory = self._auditor.discover_assets(command.repo_root, command.paths)
        tools = self._auditor.check_tool_availability()
        return IacInventoryReport(
            repo_root=command.repo_root,
            inventory=inventory,
            tools=tools,
        )


class RunIacAuditHandler:
    """Handler orchestrating selected IaC linters, validators, and security scanners."""

    def __init__(self, auditor: IacAuditorPort) -> None:
        """Initialize handler with concrete ``IacAuditorPort`` adapter.

        Args:
            auditor: Concrete ``IacAuditorPort`` implementation.
        """
        self._auditor = auditor

    @staticmethod
    def _select_tools(command: RunIacAuditCommand) -> tuple[IacToolName, ...]:
        """Determine ordered list of active IaC tools honoring explicit includes/skips."""
        base = command.tools if command.tools else _CANONICAL_TOOL_ORDER
        skip_set = set(command.skip_tools)
        selected: list[IacToolName] = []
        seen: set[IacToolName] = set()
        for tool in base:
            if tool in skip_set or tool in seen:
                continue
            seen.add(tool)
            selected.append(tool)
        return tuple(selected)

    def _build_dispatch_table(
        self,
        command: RunIacAuditCommand,
        inventory: IacAssetInventory,
        scan_paths: tuple[Path, ...],
    ) -> dict[IacToolName, Callable[[], IacToolResult]]:
        """Map each ``IacToolName`` to its bound ``IacAuditorPort`` invocation."""
        return {
            IacToolName.TOFU_FMT: lambda: self._auditor.run_tofu_fmt(
                command.repo_root,
                inventory.tofu_dirs,
                fix=command.fix,
                strict=command.strict,
            ),
            IacToolName.TOFU_VALIDATE: lambda: self._auditor.run_tofu_validate(
                command.repo_root,
                inventory.tofu_dirs,
                init_tofu=command.init_tofu,
                strict=command.strict,
            ),
            IacToolName.TFLINT: lambda: self._auditor.run_tflint(
                command.repo_root,
                inventory.tofu_dirs,
                strict=command.strict,
            ),
            IacToolName.TRIVY: lambda: self._auditor.run_trivy(
                command.repo_root,
                scan_paths,
                severity=command.severity,
                strict=command.strict,
            ),
            IacToolName.CHECKOV: lambda: self._auditor.run_checkov(
                command.repo_root,
                scan_paths,
                strict=command.strict,
            ),
            IacToolName.HADOLINT: lambda: self._auditor.run_hadolint(
                command.repo_root,
                inventory.dockerfiles,
                failure_threshold=command.hadolint_threshold,
                strict=command.strict,
            ),
            IacToolName.SHELLCHECK: lambda: self._auditor.run_shellcheck(
                command.repo_root,
                inventory.shell_scripts,
                severity=command.shellcheck_severity,
                strict=command.strict,
            ),
        }

    def handle(self, command: RunIacAuditCommand) -> IacAuditReport:
        """Execute auto-detecting IaC quality and misconfiguration gates.

        Args:
            command: ``RunIacAuditCommand`` specifying scope, tools, and policy flags.

        Returns:
            Aggregated ``IacAuditReport`` with per-tool outcomes and exit status.
        """
        start = time.perf_counter()
        inventory = self._auditor.discover_assets(command.repo_root, command.paths)
        scan_paths = _compute_security_scan_paths(inventory)
        dispatch = self._build_dispatch_table(command, inventory, scan_paths)
        active_tools = self._select_tools(command)

        results = tuple(dispatch[tool]() for tool in active_tools)
        total_duration = time.perf_counter() - start
        exit_code = 1 if any(r.status == IacCheckStatus.FAIL for r in results) else 0

        return IacAuditReport(
            repo_root=command.repo_root,
            inventory=inventory,
            results=results,
            total_duration=total_duration,
            exit_code=exit_code,
        )
