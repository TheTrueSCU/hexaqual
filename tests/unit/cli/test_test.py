"""Unit tests for Hexaqual test execution CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.test import test_app as cli_test_app

runner = CliRunner()


def test_test_help() -> None:
    """Test test help output."""
    res = runner.invoke(cli_test_app, ["--help"])
    assert res.exit_code == 0
    assert "Test execution, coverage audits" in res.stdout


def test_test_run() -> None:
    """Test test run command delegates to pytest runner."""
    with patch(
        "hexaqual.adapters.code_analysis.pytest_runner.run_main", return_value=0
    ) as mock_run:
        res = runner.invoke(
            cli_test_app,
            [
                "run",
                "-p",
                "core",
                "-e",
                "demo",
                "-a",
                "-A",
                "-U",
                "-P",
                "--with-context",
                "--",
                "--verbose",
            ],
        )
        assert res.exit_code == 0
        assert mock_run.called
        call_argv = mock_run.call_args[0][0]
        assert "-p" in call_argv
        assert "core" in call_argv
        assert "-e" in call_argv
        assert "demo" in call_argv
        assert "-a" in call_argv
        assert "-A" in call_argv
        assert "-U" in call_argv
        assert "-P" in call_argv
        assert "--with-context" in call_argv
        assert "--verbose" in call_argv


def test_test_boundary() -> None:
    """Test test boundary audit command."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_boundary_audit.return_value = 0
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.testing.create_testing_presenter", return_value=mock_pres
        ),
    ):
        res = runner.invoke(cli_test_app, ["boundary"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called


def test_test_impact() -> None:
    """Test test impact command."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_impact_analysis.return_value = 0
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.testing.create_testing_presenter", return_value=mock_pres
        ),
    ):
        res = runner.invoke(cli_test_app, ["impact"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called


def test_test_redundancy() -> None:
    """Test test redundancy audit command."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_redundancy_audit.return_value = 0
    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.testing.create_testing_presenter", return_value=mock_pres
        ),
    ):
        res = runner.invoke(cli_test_app, ["redundancy"])
        assert res.exit_code == 0
        assert mock_bus.dispatch.called


def test_test_fuzz() -> None:
    """Test test fuzz command dispatches FuzzRunCommand across governance bus."""
    mock_bus = MagicMock()
    mock_report = MagicMock()
    mock_bus.dispatch.return_value = mock_report
    mock_pres = MagicMock()
    mock_pres.present_fuzz.return_value = 0

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.analysis.create_analysis_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(
            cli_test_app,
            [
                "fuzz",
                "-t",
                "proto",
                "-n",
                "250",
                "-e",
                "standalone",
                "-f",
                "json",
            ],
        )
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.target == "proto"
        assert cmd.runs == 250
        assert cmd.engine == "standalone"
        assert mock_pres.present_fuzz.called


def test_test_fuzz_failure() -> None:
    """Test test fuzz command handles non-zero presenter exit code."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_fuzz.return_value = 1

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.analysis.create_analysis_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(cli_test_app, ["fuzz"])
        assert res.exit_code == 1


def test_test_snapshot() -> None:
    """Test test snapshot command dispatches UpdateInlineSnapshotsCommand across governance bus."""
    mock_bus = MagicMock()
    mock_report = MagicMock()
    mock_bus.dispatch.return_value = mock_report
    mock_pres = MagicMock()
    mock_pres.present_inline_snapshots.return_value = 0

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.analysis.create_analysis_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(
            cli_test_app,
            [
                "snapshot",
                "-m",
                "review",
                "-f",
                "markdown",
                "-p",
                "core",
            ],
        )
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.mode == "review"
        assert mock_pres.present_inline_snapshots.called


def test_test_snapshot_failure() -> None:
    """Test test snapshot command handles non-zero presenter exit code."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_inline_snapshots.return_value = 2

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.analysis.create_analysis_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(cli_test_app, ["snapshot"])
        assert res.exit_code == 2


def test_test_archon() -> None:
    """Test test archon command dispatches GenerateArchonTestsCommand across governance bus."""
    mock_bus = MagicMock()
    mock_report = MagicMock()
    mock_bus.dispatch.return_value = mock_report
    mock_pres = MagicMock()
    mock_pres.present_archon.return_value = 0

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.generators.create_generator_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(
            cli_test_app,
            [
                "archon",
                "-p",
                "core",
                "--force",
                "-f",
                "json",
            ],
        )
        assert res.exit_code == 0
        assert mock_bus.dispatch.called
        cmd = mock_bus.dispatch.call_args[0][0]
        assert "core" in cmd.packages
        assert cmd.force is True
        assert mock_pres.present_archon.called


def test_test_archon_failure() -> None:
    """Test test archon command handles non-zero presenter exit code."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_archon.return_value = 1

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.generators.create_generator_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(cli_test_app, ["archon"])
        assert res.exit_code == 1
