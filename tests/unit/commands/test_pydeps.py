"""Unit tests for pydeps command."""

from unittest.mock import MagicMock, patch

from hexaqual.commands.pydeps import generate_main
from hexaqual.domain.generators import PydepsDiagramResult, PydepsReport


def test_pydeps_generate_main_callable() -> None:
    """Verify pydeps generate main callable."""
    assert callable(generate_main)


def test_pydeps_generate_main_dispatches_bus() -> None:
    """Verify generate_main parses args, dispatches GeneratePydepsCommand, and formats."""
    mock_bus = MagicMock()
    mock_report = PydepsReport(
        results=(
            PydepsDiagramResult(name="core", path="docs/assets/pydeps/core.svg", success=True),
        ),
        is_successful=True,
    )
    mock_bus.dispatch.return_value = mock_report

    with (
        patch("hexaqual.commands.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.infra.bootstrap.create_governance_bus",
            return_value=mock_bus,
        ),
    ):
        code = generate_main(["-p", "core", "--format", "json"])
        assert code == 0
        assert mock_bus.dispatch.called


def test_pydeps_generate_main_check_flag() -> None:
    """Verify generate_main passes check_only=True when --check is supplied."""
    mock_bus = MagicMock()
    mock_report = PydepsReport(
        results=(
            PydepsDiagramResult(name="core", path="docs/assets/pydeps/core.svg", success=True),
        ),
        is_successful=True,
        is_check=True,
    )
    mock_bus.dispatch.return_value = mock_report

    with (
        patch("hexaqual.commands.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.infra.bootstrap.create_governance_bus",
            return_value=mock_bus,
        ),
    ):
        code = generate_main(["--check"])
        assert code == 0
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.check_only is True
        assert cmd.fix is False


def test_pydeps_generate_main_fix_flag() -> None:
    """Verify generate_main passes fix=True when --fix is supplied."""
    mock_bus = MagicMock()
    mock_report = PydepsReport(
        results=(
            PydepsDiagramResult(name="core", path="docs/assets/pydeps/core.svg", success=True),
        ),
        is_successful=True,
        is_check=False,
    )
    mock_bus.dispatch.return_value = mock_report

    with (
        patch("hexaqual.commands.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.infra.bootstrap.create_governance_bus",
            return_value=mock_bus,
        ),
    ):
        code = generate_main(["--fix"])
        assert code == 0
        cmd = mock_bus.dispatch.call_args[0][0]
        assert cmd.fix is True
        assert cmd.check_only is False
