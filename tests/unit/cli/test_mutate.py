"""Unit tests for Hexaqual mutation testing CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from hexaqual.cli.mutate import mutate_app
from hexaqual.domain.testing import MutationAuditReport

runner = CliRunner()


def test_mutate_help() -> None:
    """Test mutate help output."""
    res = runner.invoke(mutate_app, ["--help"])
    assert res.exit_code == 0
    assert "Mutation testing execution" in res.stdout


def test_mutate_run() -> None:
    """Test mutate run command dispatches RunMutationTestsCommand."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = 0
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed") as mock_ensure,
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(
            mutate_app,
            [
                "run",
                "-p",
                "core",
                "-e",
                "gremlins",
                "-w",
                "4",
                "-n",
                "2",
                "--operators",
                "boolean,comparison",
                "--mutant-timeout",
                "75",
                "--prescan-workers",
                "3",
                "--coverage-timeout",
                "420",
            ],
        )
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.package == "core"
        assert cmd.engine == "gremlins"
        assert cmd.workers == "4"
        assert cmd.numprocesses == "2"
        assert cmd.operators == ["boolean", "comparison"]
        assert cmd.mutant_timeout == 75
        assert cmd.prescan_workers == 3
        assert cmd.coverage_timeout == 420
        mock_ensure.assert_called_once_with("pytest_gremlins", extra_name="gremlins")


def test_mutate_run_mutmut() -> None:
    """Test mutate run command with mutmut engine."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = 0
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed") as mock_ensure,
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(mutate_app, ["run", "-p", "core", "-e", "mutmut", "-r"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.engine == "mutmut"
        assert cmd.reset_cache is True
        mock_ensure.assert_called_once_with("mutmut", cli_command="mutmut", extra_name="mutmut")


def test_mutate_run_affected() -> None:
    """Test mutate run command with affected flag."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = 0
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed") as mock_ensure,
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(mutate_app, ["run", "-A", "-e", "gremlins"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.affected is True
        assert cmd.engine == "gremlins"
        mock_ensure.assert_called_once_with("pytest_gremlins", extra_name="gremlins")


def test_mutate_inspect() -> None:
    """Test mutate inspect command dispatches InspectMutationCacheCommand."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = MutationAuditReport(
        summaries=(),
        actionable_mutants=(),
    )
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed"),
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(mutate_app, ["inspect", "--summary", "-e", "gremlins"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.engine == "gremlins"


def test_mutate_run_failure() -> None:
    """Test mutate run raises Exit when bus dispatch returns non-zero code."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = 1
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed"),
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(mutate_app, ["run", "-p", "core"])
        assert res.exit_code == 1


def test_mutate_inspect_mutmut() -> None:
    """Test mutate inspect with mutmut engine ensures tool and creates command."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = MutationAuditReport(summaries=(), actionable_mutants=())
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed") as mock_ensure,
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(mutate_app, ["inspect", "-e", "mutmut", "-act"])
        assert res.exit_code == 0
        mock_ensure.assert_called_once_with("mutmut", cli_command="mutmut", extra_name="mutmut")
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.engine == "mutmut"
        assert cmd.actionable_only is True


def test_mutate_inspect_failure() -> None:
    """Test mutate inspect raises Exit when presenter returns non-zero code."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = MutationAuditReport(summaries=(), actionable_mutants=())
    mock_presenter = MagicMock()
    mock_presenter.present_mutation_summary.return_value = 1
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed"),
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.cli.mutate.create_testing_presenter", return_value=mock_presenter),
    ):
        res = runner.invoke(mutate_app, ["inspect", "-s"])
        assert res.exit_code == 1


def test_mutate_inspect_step_summary_summary() -> None:
    """Verify mutate inspect with --step-summary appends summary markdown."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = MutationAuditReport(summaries=(), actionable_mutants=())
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed"),
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.cli.mutate.append_step_summary") as mock_append,
    ):
        res = runner.invoke(mutate_app, ["inspect", "-s", "--step-summary"])
        assert res.exit_code == 0
        mock_append.assert_called_once()
        args = mock_append.call_args[0]
        assert "Mutation Testing Triage Summary" in args[0]


def test_mutate_inspect_step_summary_actionable() -> None:
    """Verify mutate inspect with --step-summary and -act appends actionable markdown."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = MutationAuditReport(summaries=(), actionable_mutants=())
    with (
        patch("hexaqual.cli.mutate.ensure_tool_installed"),
        patch("hexaqual.cli.mutate.create_governance_bus", return_value=mock_bus),
        patch("hexaqual.cli.mutate.append_step_summary") as mock_append,
    ):
        res = runner.invoke(mutate_app, ["inspect", "-act", "--step-summary"])
        assert res.exit_code == 0
        mock_append.assert_called_once()
        args = mock_append.call_args[0]
        assert "Actionable Surviving Mutants" in args[0]


def test_mutate_plan_writes_github_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify mutate plan writes matrix and has_affected to GITHUB_OUTPUT."""
    import json

    out_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
    packages = tmp_path / "packages"
    src_dir = packages / "core" / "src" / "core"
    src_dir.mkdir(parents=True)
    (packages / "core" / "pyproject.toml").write_text(
        '[project]\nname = "core"\n', encoding="utf-8"
    )
    (src_dir / "app.py").write_text("x = 1 + 2\n", encoding="utf-8")

    res = runner.invoke(
        mutate_app,
        ["plan", "--mode", "all", "--packages-root", str(packages), "--github-output"],
    )
    assert res.exit_code == 0
    content = out_file.read_text(encoding="utf-8")
    assert f"matrix={json.dumps({'package': ['core']})}" in content
    assert "has_affected=true" in content


def test_mutate_plan_invalid_mode() -> None:
    """Verify mutate plan rejects unsupported planning modes."""
    res = runner.invoke(mutate_app, ["plan", "--mode", "bogus"])
    assert res.exit_code != 0


def test_mutate_plan_stdout(tmp_path: Path) -> None:
    """Verify mutate plan writes to stdout when --github-output is not set."""
    packages = tmp_path / "packages"
    src_dir = packages / "core" / "src" / "core"
    src_dir.mkdir(parents=True)
    (packages / "core" / "pyproject.toml").write_text(
        '[project]\nname = "core"\n', encoding="utf-8"
    )
    (src_dir / "app.py").write_text("x = 1 + 2\n", encoding="utf-8")

    res = runner.invoke(mutate_app, ["plan", "--mode", "all", "--packages-root", str(packages)])
    assert res.exit_code == 0
    assert "has_affected=true" in res.stdout
