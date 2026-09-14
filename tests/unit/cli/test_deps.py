"""Unit tests for Hexaqual deps CLI commands.

Notes/Architectural Intent:
    Validates deps subcommands (audit, pydeps, linter, linter-generate)
    using CliRunner and mocked bus dispatchers and presenters.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hexaqual.cli.deps import deps_app

runner = CliRunner()


def test_deps_help() -> None:
    """Test deps help output."""
    res = runner.invoke(deps_app, ["--help"])
    exit_code = res.exit_code
    stdout = res.stdout
    assert exit_code == 0
    assert "Audit dependencies" in stdout


def test_deps_audit_clean() -> None:
    """Test deps audit clean run."""
    mock_report = MagicMock()
    mock_presenter = MagicMock()
    mock_presenter.present_unified_deps_audit.return_value = 0

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus") as mock_bus_factory,
        patch(
            "hexaqual.adapters.presenters.dependency.create_dependency_presenter",
            return_value=mock_presenter,
        ),
    ):
        mock_bus = MagicMock()
        mock_bus.dispatch.return_value = mock_report
        mock_bus_factory.return_value = mock_bus

        res = runner.invoke(deps_app, ["audit", "--extras-only"])
        exit_code = res.exit_code
        assert exit_code == 0
        mock_presenter.present_unified_deps_audit.assert_called_once_with(mock_report)


def test_deps_audit_failure() -> None:
    """Test deps audit failure exits with non-zero code."""
    mock_report = MagicMock()
    mock_presenter = MagicMock()
    mock_presenter.present_unified_deps_audit.return_value = 1

    with (
        patch("hexaqual.infra.bootstrap.create_governance_bus") as mock_bus_factory,
        patch(
            "hexaqual.adapters.presenters.dependency.create_dependency_presenter",
            return_value=mock_presenter,
        ),
    ):
        mock_bus = MagicMock()
        mock_bus.dispatch.return_value = mock_report
        mock_bus_factory.return_value = mock_bus

        res = runner.invoke(deps_app, ["audit", "--deptry-only"])
        exit_code = res.exit_code
        assert exit_code == 1


def test_deps_pydeps_success() -> None:
    """Test deps pydeps generates diagrams successfully."""
    mock_report = MagicMock()
    mock_presenter = MagicMock()
    mock_presenter.present_pydeps.return_value = 0

    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.infra.bootstrap.create_governance_bus") as mock_bus_factory,
        patch(
            "hexaqual.adapters.presenters.generators.create_generator_presenter",
            return_value=mock_presenter,
        ),
    ):
        mock_bus = MagicMock()
        mock_bus.dispatch.return_value = mock_report
        mock_bus_factory.return_value = mock_bus

        res = runner.invoke(deps_app, ["pydeps", "-p", "core"])
        exit_code = res.exit_code
        assert exit_code == 0
        mock_presenter.present_pydeps.assert_called_once_with(mock_report)


def test_deps_pydeps_failure() -> None:
    """Test deps pydeps exits with error code when diagramming fails."""
    mock_report = MagicMock()
    mock_presenter = MagicMock()
    mock_presenter.present_pydeps.return_value = 1

    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.infra.bootstrap.create_governance_bus") as mock_bus_factory,
        patch(
            "hexaqual.adapters.presenters.generators.create_generator_presenter",
            return_value=mock_presenter,
        ),
    ):
        mock_bus = MagicMock()
        mock_bus.dispatch.return_value = mock_report
        mock_bus_factory.return_value = mock_bus

        res = runner.invoke(deps_app, ["pydeps"])
        exit_code = res.exit_code
        assert exit_code == 1


def test_deps_linter_success(tmp_path: Path) -> None:
    """Test deps linter evaluates contracts successfully."""
    mock_report = MagicMock()
    mock_presenter = MagicMock()
    mock_presenter.present_import_linter.return_value = 0

    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.utils.workspace.get_repo_root", return_value=tmp_path),
        patch(
            "hexaqual.utils.workspace.get_packages_directory", return_value=tmp_path / "packages"
        ),
        patch(
            "hexaqual.utils.workspace.get_package_directories",
            return_value=[tmp_path / "packages" / "core"],
        ),
        patch("hexaqual.infra.bootstrap.create_governance_bus") as mock_bus_factory,
        patch(
            "hexaqual.adapters.presenters.dependency.create_dependency_presenter",
            return_value=mock_presenter,
        ),
    ):
        mock_bus = MagicMock()
        mock_bus.dispatch.return_value = mock_report
        mock_bus_factory.return_value = mock_bus

        res = runner.invoke(deps_app, ["linter", "--all"])
        exit_code = res.exit_code
        assert exit_code == 0


def test_deps_linter_failure(tmp_path: Path) -> None:
    """Test deps linter failure exits with non-zero code."""
    mock_report = MagicMock()
    mock_presenter = MagicMock()
    mock_presenter.present_import_linter.return_value = 1

    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.utils.workspace.get_repo_root", return_value=tmp_path),
        patch(
            "hexaqual.utils.workspace.get_packages_directory", return_value=tmp_path / "packages"
        ),
        patch(
            "hexaqual.utils.workspace.get_package_directories",
            return_value=[tmp_path / "packages" / "core"],
        ),
        patch("hexaqual.infra.bootstrap.create_governance_bus") as mock_bus_factory,
        patch(
            "hexaqual.adapters.presenters.dependency.create_dependency_presenter",
            return_value=mock_presenter,
        ),
    ):
        mock_bus = MagicMock()
        mock_bus.dispatch.return_value = mock_report
        mock_bus_factory.return_value = mock_bus

        res = runner.invoke(deps_app, ["linter", "--all"])
        exit_code = res.exit_code
        assert exit_code == 1


def test_deps_linter_generate(tmp_path: Path) -> None:
    """Test deps linter-generate dispatches config generation command."""
    mock_bus = MagicMock()
    with (
        patch("hexaqual.utils.workspace.get_repo_root", return_value=tmp_path),
        patch(
            "hexaqual.utils.workspace.get_package_directories",
            return_value=[tmp_path / "packages" / "core"],
        ),
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
    ):
        res = runner.invoke(deps_app, ["linter-generate"])
        exit_code = res.exit_code
        assert exit_code == 0
        mock_bus.dispatch.assert_called_once()


def test_deps_deptry_success() -> None:
    """Test deps deptry dispatches RunDeptryAuditCommand across governance bus."""
    mock_bus = MagicMock()
    mock_report = MagicMock()
    mock_bus.dispatch.return_value = mock_report
    mock_pres = MagicMock()
    mock_pres.present_deptry_audit.return_value = 0

    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.dependency.create_dependency_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(deps_app, ["deptry", "-f", "json"])
        exit_code = res.exit_code
        assert exit_code == 0
        assert mock_bus.dispatch.called
        assert mock_pres.present_deptry_audit.called


def test_deps_deptry_failure() -> None:
    """Test deps deptry handles non-zero presenter exit code."""
    mock_bus = MagicMock()
    mock_pres = MagicMock()
    mock_pres.present_deptry_audit.return_value = 1

    with (
        patch("hexaqual.utils.workspace.ensure_tool_installed"),
        patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus),
        patch(
            "hexaqual.adapters.presenters.dependency.create_dependency_presenter",
            return_value=mock_pres,
        ),
    ):
        res = runner.invoke(deps_app, ["deptry"])
        exit_code = res.exit_code
        assert exit_code == 1
