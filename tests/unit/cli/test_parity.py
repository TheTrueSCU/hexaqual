"""Unit tests for Hexaqual parity CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.parity import parity_app

runner = CliRunner()


def test_parity_help() -> None:
    """Test parity help output."""
    res = runner.invoke(parity_app, ["--help"])
    assert res.exit_code == 0
    assert "Audit test symmetry and optional extras parity" in res.stdout


def test_parity_test_clean() -> None:
    """Test parity test with zero errors."""
    with (
        patch(
            "hexaqual.adapters.code_analysis.test_parity.check_test_directories_inits",
            return_value=[],
        ),
        patch(
            "hexaqual.adapters.code_analysis.test_parity.check_src_to_test_symmetry",
            return_value=[],
        ),
    ):
        res = runner.invoke(parity_app, ["test"])
        assert res.exit_code == 0


def test_parity_test_violations() -> None:
    """Test parity test with missing inits or asymmetry."""
    with (
        patch(
            "hexaqual.adapters.code_analysis.test_parity.check_test_directories_inits",
            return_value=["missing __init__.py"],
        ),
        patch(
            "hexaqual.adapters.code_analysis.test_parity.check_src_to_test_symmetry",
            return_value=[],
        ),
    ):
        res = runner.invoke(parity_app, ["test"])
        assert res.exit_code == 1


def test_parity_extras() -> None:
    """Test parity extras command."""
    from hexaqual.domain.dependencies import ExtrasAuditResult

    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = ExtrasAuditResult(
        violations=(),
        total_packages_checked=1,
    )
    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        res = runner.invoke(parity_app, ["extras"])
        assert res.exit_code == 0


def test_parity_architecture_clean() -> None:
    """Test parity architecture with zero errors."""
    with patch(
        "hexaqual.adapters.code_analysis.test_parity.check_architecture_test_parity",
        return_value=[],
    ):
        res = runner.invoke(parity_app, ["architecture"])
        assert res.exit_code == 0


def test_parity_architecture_violations() -> None:
    """Test parity architecture with detected errors."""
    with patch(
        "hexaqual.adapters.code_analysis.test_parity.check_architecture_test_parity",
        return_value=["Missing architecture tests in packages/foo/tests/architecture"],
    ):
        res = runner.invoke(parity_app, ["architecture"])
        assert res.exit_code == 1
