"""Unit tests for agent command handlers.

Notes/Architectural Intent:
    Validates sync_agents_command, check_agents_command, and list_agents_command
    using pure port doubles to verify delegation and error propagation.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.commands.agents import (
    check_agents_command,
    list_agents_command,
    sync_agents_command,
)
from hexaqual.domain.agents import (
    AgentAsset,
    AgentAssetKind,
    AgentCheckReport,
    AgentSyncReport,
)
from hexaqual.ports.agents import AgentAssetPort, AgentPresenterPort


class MockAssetPort(AgentAssetPort):
    """Mock test double for AgentAssetPort."""

    def __init__(self, is_clean: bool = True) -> None:
        self.is_clean = is_clean
        self.sync_called = False
        self.check_called = False
        self.load_called = False

    def load_bundled_assets(self) -> tuple[AgentAsset, ...]:
        self.load_called = True
        return (
            AgentAsset(
                "hexaqual-boundaries.md",
                AgentAssetKind.RULE,
                "rules/hexaqual-boundaries.md",
                "# Content",
            ),
        )

    def sync_assets(self, target_dir: Path, dry_run: bool = False) -> AgentSyncReport:
        self.sync_called = True
        return AgentSyncReport(1, 0, 0, 0, ("Created rules/hexaqual-boundaries.md",))

    def check_drift(self, target_dir: Path) -> AgentCheckReport:
        self.check_called = True
        if self.is_clean:
            return AgentCheckReport(True, (), (), ())
        return AgentCheckReport(False, ("rules/drifted.md",), (), ("Drift detected",))


class MockPresenterPort(AgentPresenterPort):
    """Mock test double for AgentPresenterPort."""

    def __init__(self) -> None:
        self.sync_presented = False
        self.check_presented = False
        self.list_presented = False

    def present_sync(self, report: AgentSyncReport) -> int:
        self.sync_presented = True
        return 0

    def present_check(self, report: AgentCheckReport) -> int:
        self.check_presented = True
        return 0 if report.is_clean else 1

    def present_list(self, assets: tuple[AgentAsset, ...]) -> int:
        self.list_presented = True
        return 0


def test_sync_agents_command_delegation(tmp_path: Path) -> None:
    """Verify sync_agents_command coordinates adapter and presenter.

    Notes/Architectural Intent:
        Asserts adapter.sync_assets and presenter.present_sync are both invoked.
    """
    adapter = MockAssetPort()
    presenter = MockPresenterPort()

    exit_code = sync_agents_command(
        target_dir=tmp_path,
        dry_run=False,
        format_type="table",
        presenter=presenter,
        adapter=adapter,
    )

    sync_called = adapter.sync_called
    sync_presented = presenter.sync_presented

    assert exit_code == 0
    assert sync_called is True
    assert sync_presented is True


def test_check_agents_command_clean_and_dirty(tmp_path: Path) -> None:
    """Verify check_agents_command returns 0 when clean and 1 when dirty.

    Notes/Architectural Intent:
        Validates check exit code propagation.
    """
    clean_adapter = MockAssetPort(is_clean=True)
    presenter = MockPresenterPort()

    clean_exit = check_agents_command(
        target_dir=tmp_path,
        format_type="table",
        presenter=presenter,
        adapter=clean_adapter,
    )
    assert clean_exit == 0

    dirty_adapter = MockAssetPort(is_clean=False)
    dirty_exit = check_agents_command(
        target_dir=tmp_path,
        format_type="table",
        presenter=presenter,
        adapter=dirty_adapter,
    )
    assert dirty_exit == 1


def test_list_agents_command_delegation() -> None:
    """Verify list_agents_command loads assets and presents catalog.

    Notes/Architectural Intent:
        Asserts adapter.load_bundled_assets and presenter.present_list are invoked.
    """
    adapter = MockAssetPort()
    presenter = MockPresenterPort()

    exit_code = list_agents_command(
        format_type="table",
        presenter=presenter,
        adapter=adapter,
    )

    load_called = adapter.load_called
    list_presented = presenter.list_presented

    assert exit_code == 0
    assert load_called is True
    assert list_presented is True
