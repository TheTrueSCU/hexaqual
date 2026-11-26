"""Unit tests for IaC CQRS command handlers.

Notes/Architectural Intent:
    Verifies that DiscoverIacAssetsHandler and RunIacAuditHandler delegate to
    IacAuditorPort, preserve canonical tool ordering, deduplicate security scan
    paths, honor tool/skip filters, and compute aggregated exit codes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from hexaqual.domain.iac import (
    DiscoverIacAssetsCommand,
    IacAssetInventory,
    IacCategory,
    IacCheckStatus,
    IacToolAvailability,
    IacToolName,
    IacToolResult,
    RunIacAuditCommand,
)
from hexaqual.infra.handlers.iac import (
    DiscoverIacAssetsHandler,
    RunIacAuditHandler,
)
from hexaqual.ports.iac import IacAuditorPort


def _make_mock_auditor(inventory: IacAssetInventory) -> MagicMock:
    """Create a MagicMock(spec=IacAuditorPort) with default PASS results."""
    mock = MagicMock(spec=IacAuditorPort)
    mock.discover_assets.return_value = inventory
    mock.check_tool_availability.return_value = (
        IacToolAvailability(IacToolName.TOFU_FMT, "tofu", True, "/usr/bin/tofu"),
    )
    mock.run_tofu_fmt.return_value = IacToolResult(
        IacToolName.TOFU_FMT, IacCategory.OPENTOFU, IacCheckStatus.PASS
    )
    mock.run_tofu_validate.return_value = IacToolResult(
        IacToolName.TOFU_VALIDATE, IacCategory.OPENTOFU, IacCheckStatus.PASS
    )
    mock.run_tflint.return_value = IacToolResult(
        IacToolName.TFLINT, IacCategory.OPENTOFU, IacCheckStatus.PASS
    )
    mock.run_trivy.return_value = IacToolResult(
        IacToolName.TRIVY, IacCategory.OPENTOFU, IacCheckStatus.PASS
    )
    mock.run_checkov.return_value = IacToolResult(
        IacToolName.CHECKOV, IacCategory.OPENTOFU, IacCheckStatus.PASS
    )
    mock.run_hadolint.return_value = IacToolResult(
        IacToolName.HADOLINT, IacCategory.DOCKER, IacCheckStatus.PASS
    )
    mock.run_shellcheck.return_value = IacToolResult(
        IacToolName.SHELLCHECK, IacCategory.SHELL, IacCheckStatus.PASS
    )
    return mock


def test_discover_iac_assets_handler(tmp_path: Path) -> None:
    """Verify DiscoverIacAssetsHandler returns inventory and tool readiness."""
    inv = IacAssetInventory(dockerfiles=(tmp_path / "Dockerfile",))
    auditor = _make_mock_auditor(inv)
    handler = DiscoverIacAssetsHandler(auditor)

    report = handler.handle(DiscoverIacAssetsCommand(repo_root=tmp_path, paths=(Path("."),)))
    assert report.inventory == inv
    assert len(report.tools) == 1
    auditor.discover_assets.assert_called_once_with(tmp_path, (Path("."),))
    auditor.check_tool_availability.assert_called_once()


def test_run_iac_audit_handler_canonical_and_filtered(tmp_path: Path) -> None:
    """Verify RunIacAuditHandler runs all 7 tools by default and respects tool/skip filters."""
    tofu_dir = tmp_path / "deploy" / "tofu"
    dockerfile = tmp_path / "Dockerfile"
    k8s = tmp_path / "k8s.yaml"
    sh = tmp_path / "boot.sh"
    inv = IacAssetInventory(
        tofu_dirs=(tofu_dir,),
        tofu_files=(tofu_dir / "main.tf",),
        dockerfiles=(dockerfile,),
        k8s_paths=(k8s,),
        shell_scripts=(sh,),
    )
    auditor = _make_mock_auditor(inv)
    handler = RunIacAuditHandler(auditor)

    report = handler.handle(RunIacAuditCommand(repo_root=tmp_path))
    assert report.exit_code == 0
    executed_tools = [r.tool for r in report.results]
    assert executed_tools == [
        IacToolName.TOFU_FMT,
        IacToolName.TOFU_VALIDATE,
        IacToolName.TFLINT,
        IacToolName.TRIVY,
        IacToolName.CHECKOV,
        IacToolName.HADOLINT,
        IacToolName.SHELLCHECK,
    ]
    trivy_scan_paths = auditor.run_trivy.call_args[0][1]
    assert trivy_scan_paths == (tofu_dir.resolve(), dockerfile.resolve(), k8s.resolve())

    # Tool subset + skip + failure propagation
    auditor.run_hadolint.return_value = IacToolResult(
        IacToolName.HADOLINT, IacCategory.DOCKER, IacCheckStatus.FAIL
    )
    filtered_report = handler.handle(
        RunIacAuditCommand(
            repo_root=tmp_path,
            tools=(IacToolName.HADOLINT, IacToolName.HADOLINT, IacToolName.SHELLCHECK),
            skip_tools=(IacToolName.SHELLCHECK,),
        )
    )
    assert filtered_report.exit_code == 1
    assert [r.tool for r in filtered_report.results] == [IacToolName.HADOLINT]
