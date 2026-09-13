"""Unit tests for inline_snapshot command."""

from hexaqual.commands.inline_snapshot import main


def test_inline_snapshot_main_callable() -> None:
    """Verify inline snapshot main callable."""
    assert callable(main)


def test_inline_snapshot_main_dispatches_bus() -> None:
    """Verify inline snapshot main dispatches UpdateInlineSnapshotsCommand and formats."""
    from unittest.mock import MagicMock, patch

    from hexaqual.domain.analysis import InlineSnapshotsReport

    mock_bus = MagicMock()
    mock_report = InlineSnapshotsReport(
        targets_updated=("packages/hexastack_core",),
        exit_code=0,
    )
    mock_bus.dispatch.return_value = mock_report

    with patch("hexaqual.infra.bootstrap.create_governance_bus", return_value=mock_bus):
        code = main(["-p", "core", "--mode", "fix", "--format", "json"])
        assert code == 0
        assert mock_bus.dispatch.called
