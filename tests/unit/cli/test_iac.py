"""Unit tests for ``hexaqual iac`` CLI driving adapter."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.main import app
from hexaqual.domain.iac import (
    DiscoverIacAssetsCommand,
    IacAssetInventory,
    IacAuditReport,
    IacCategory,
    IacCheckStatus,
    IacInventoryReport,
    IacToolAvailability,
    IacToolName,
    IacToolResult,
    RunIacAuditCommand,
)

runner = CliRunner()


def test_iac_discover_cli_json_and_invalid_format(tmp_path: Path) -> None:
    """Verify ``hexaqual iac discover`` dispatches command and handles invalid format."""
    inv_report = IacInventoryReport(
        repo_root=tmp_path,
        inventory=IacAssetInventory(dockerfiles=(tmp_path / "Dockerfile",)),
        tools=(IacToolAvailability(IacToolName.HADOLINT, "hadolint", True, "/usr/bin/hadolint"),),
    )
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = inv_report

    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        res = runner.invoke(app, ["iac", "discover", "--root", str(tmp_path), "--format", "json"])
        assert res.exit_code == 0
        payload = json.loads(res.stdout)
        assert payload["has_any"] is True
        cmd = mock_bus.dispatch.call_args[0][0]
        assert isinstance(cmd, DiscoverIacAssetsCommand)

        bad_res = runner.invoke(
            app, ["iac", "discover", "--root", str(tmp_path), "--format", "xml"]
        )
        assert bad_res.exit_code == 2


def test_iac_check_cli_options_summary_and_failures(tmp_path: Path, monkeypatch) -> None:
    """Verify ``hexaqual iac check`` parses tool options, writes step summary, and propagates failure."""
    summary_file = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))

    pass_report = IacAuditReport(
        repo_root=tmp_path,
        inventory=IacAssetInventory(dockerfiles=(tmp_path / "Dockerfile",)),
        results=(
            IacToolResult(
                IacToolName.HADOLINT,
                IacCategory.DOCKER,
                IacCheckStatus.PASS,
                targets_checked=1,
            ),
        ),
        exit_code=0,
    )
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = pass_report

    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        res = runner.invoke(
            app,
            [
                "iac",
                "check",
                "--root",
                str(tmp_path),
                "--tool",
                "hadolint,shellcheck",
                "--skip",
                "shellcheck",
                "--fix",
                "--init",
                "--strict",
                "--summary",
                "--format",
                "markdown",
            ],
        )
        assert res.exit_code == 0
        cmd: RunIacAuditCommand = mock_bus.dispatch.call_args[0][0]
        assert isinstance(cmd, RunIacAuditCommand)
        assert cmd.tools == (IacToolName.HADOLINT, IacToolName.SHELLCHECK)
        assert cmd.skip_tools == (IacToolName.SHELLCHECK,)
        assert cmd.fix is True
        assert cmd.init_tofu is True
        assert cmd.strict is True
        summary_text = summary_file.read_text(encoding="utf-8")
        assert "Hexaqual IaC Quality & Security Dashboard" in summary_text

    # Failure propagation
    mock_bus.dispatch.return_value = IacAuditReport(
        repo_root=tmp_path,
        inventory=IacAssetInventory(dockerfiles=(tmp_path / "Dockerfile",)),
        results=(IacToolResult(IacToolName.HADOLINT, IacCategory.DOCKER, IacCheckStatus.FAIL),),
        exit_code=1,
    )
    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        fail_res = runner.invoke(app, ["iac", "check", "--root", str(tmp_path)])
        assert fail_res.exit_code == 1

    # Invalid --tool / --format
    bad_tool = runner.invoke(app, ["iac", "check", "--tool", "nonexistent"])
    assert bad_tool.exit_code == 2
    bad_fmt = runner.invoke(app, ["iac", "check", "--root", str(tmp_path), "--format", "bad"])
    assert bad_fmt.exit_code == 2


def test_iac_fmt_cli_modes(tmp_path: Path) -> None:
    """Verify ``hexaqual iac fmt`` dispatches TOFU_FMT and rejects --check with --fix."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = IacAuditReport(
        repo_root=tmp_path,
        inventory=IacAssetInventory(),
        results=(IacToolResult(IacToolName.TOFU_FMT, IacCategory.OPENTOFU, IacCheckStatus.SKIP),),
        exit_code=0,
    )
    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        res_fix = runner.invoke(app, ["iac", "fmt", "--root", str(tmp_path), "--fix", "--strict"])
        assert res_fix.exit_code == 0
        cmd: RunIacAuditCommand = mock_bus.dispatch.call_args[0][0]
        assert cmd.tools == (IacToolName.TOFU_FMT,)
        assert cmd.fix is True
        assert cmd.strict is True

    res_conflict = runner.invoke(app, ["iac", "fmt", "--root", str(tmp_path), "--check", "--fix"])
    assert res_conflict.exit_code == 2

    mock_bus.dispatch.return_value = IacAuditReport(
        repo_root=tmp_path,
        inventory=IacAssetInventory(tofu_dirs=(tmp_path,)),
        results=(IacToolResult(IacToolName.TOFU_FMT, IacCategory.OPENTOFU, IacCheckStatus.FAIL),),
        exit_code=1,
    )
    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        res_fail = runner.invoke(app, ["iac", "fmt", "--root", str(tmp_path)])
        assert res_fail.exit_code == 1
