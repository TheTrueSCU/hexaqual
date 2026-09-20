"""Unit tests for agent port interfaces.

Notes/Architectural Intent:
    Validates abstract method contracts for AgentAssetPort and AgentPresenterPort.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hexaqual.domain.agents import (
    AgentAsset,
    AgentCheckReport,
    AgentSyncReport,
)
from hexaqual.ports.agents import AgentAssetPort, AgentPresenterPort


class DummyAssetPort(AgentAssetPort):
    """Concrete test stub for AgentAssetPort."""

    def load_bundled_assets(self) -> tuple[AgentAsset, ...]:
        return ()

    def sync_assets(self, target_dir: Path, dry_run: bool = False) -> AgentSyncReport:
        return AgentSyncReport(0, 0, 0, 0, ())

    def check_drift(self, target_dir: Path) -> AgentCheckReport:
        return AgentCheckReport(True, (), (), ())


class DummyPresenterPort(AgentPresenterPort):
    """Concrete test stub for AgentPresenterPort."""

    def present_sync(self, report: AgentSyncReport) -> int:
        return 0

    def present_check(self, report: AgentCheckReport) -> int:
        return 0

    def present_list(self, assets: tuple[AgentAsset, ...]) -> int:
        return 0


def test_agent_asset_port_abstract_instantiation() -> None:
    """Verify AgentAssetPort cannot be instantiated directly.

    Notes/Architectural Intent:
        Guarantees abstract method invariants cannot be bypassed.
    """
    with pytest.raises(TypeError):
        AgentAssetPort()  # type: ignore[abstract]


def test_agent_presenter_port_abstract_instantiation() -> None:
    """Verify AgentPresenterPort cannot be instantiated directly.

    Notes/Architectural Intent:
        Guarantees abstract method invariants cannot be bypassed.
    """
    with pytest.raises(TypeError):
        AgentPresenterPort()  # type: ignore[abstract]


def test_dummy_ports_conformance() -> None:
    """Verify concrete stubs implement all abstract methods.

    Notes/Architectural Intent:
        Asserts standard subclassing behavior for test doubles.
    """
    asset_port = DummyAssetPort()
    presenter_port = DummyPresenterPort()

    assets = asset_port.load_bundled_assets()
    sync_report = asset_port.sync_assets(Path("."))
    check_report = asset_port.check_drift(Path("."))

    sync_exit = presenter_port.present_sync(sync_report)
    check_exit = presenter_port.present_check(check_report)
    list_exit = presenter_port.present_list(assets)

    assert len(assets) == 0
    assert sync_report.total_synced == 0
    assert check_report.is_clean is True
    assert sync_exit == 0
    assert check_exit == 0
    assert list_exit == 0
