"""Command handlers for .agents assets synchronization and drift verification.

Notes/Architectural Intent:
    Application layer service wiring FileSystemAgentAssetAdapter to presenter adapters.
    Provides entrypoints for syncing, checking, and listing universal agent assets.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.adapters.agents.fs import FileSystemAgentAssetAdapter
from hexaqual.adapters.presenters.agents import create_agent_presenter
from hexaqual.ports.agents import AgentAssetPort, AgentPresenterPort

__all__ = [
    "check_agents_command",
    "list_agents_command",
    "sync_agents_command",
]


def sync_agents_command(
    target_dir: Path | None = None,
    dry_run: bool = False,
    format_type: str = "table",
    presenter: AgentPresenterPort | None = None,
    adapter: AgentAssetPort | None = None,
) -> int:
    """Execute synchronization of managed agent guardrails to target repository.

    Args:
        target_dir: Optional path to target directory or repository root (defaults to CWD).
        dry_run: Whether to simulate changes without writing files.
        format_type: Requested output presentation format ('table', 'json', 'markdown').
        presenter: Optional presenter port override for testing.
        adapter: Optional asset port override for testing.

    Returns:
        Process exit code (0 for success).

    Raises:
        None.

    Notes/Architectural Intent:
        Synchronizes all rules, workflows, and skills while strictly preserving
        unmanaged local repository assets (e.g. hexaqueue-*, hexaflow-*).
    """
    dest = target_dir or Path.cwd()
    asset_adapter = adapter or FileSystemAgentAssetAdapter()
    report = asset_adapter.sync_assets(target_dir=dest, dry_run=dry_run)

    active_presenter = presenter or create_agent_presenter(format_type=format_type)
    return active_presenter.present_sync(report)


def check_agents_command(
    target_dir: Path | None = None,
    format_type: str = "table",
    presenter: AgentPresenterPort | None = None,
    adapter: AgentAssetPort | None = None,
) -> int:
    """Check target repository for drift against bundled agent guardrails.

    Args:
        target_dir: Optional path to target directory or repository root (defaults to CWD).
        format_type: Requested output presentation format ('table', 'json', 'markdown').
        presenter: Optional presenter port override for testing.
        adapter: Optional asset port override for testing.

    Returns:
        Process exit code (0 if clean, 1 if drift detected).

    Raises:
        None.

    Notes/Architectural Intent:
        Powers pre-commit hooks and CI pipelines to enforce synchronicity with
        installed hexaqual version.
    """
    dest = target_dir or Path.cwd()
    asset_adapter = adapter or FileSystemAgentAssetAdapter()
    report = asset_adapter.check_drift(target_dir=dest)

    active_presenter = presenter or create_agent_presenter(format_type=format_type)
    return active_presenter.present_check(report)


def list_agents_command(
    format_type: str = "table",
    presenter: AgentPresenterPort | None = None,
    adapter: AgentAssetPort | None = None,
) -> int:
    """Display catalog of universal agent assets bundled with hexaqual.

    Args:
        format_type: Requested output presentation format ('table', 'json', 'markdown').
        presenter: Optional presenter port override for testing.
        adapter: Optional asset port override for testing.

    Returns:
        Process exit code (0 for success).

    Raises:
        None.

    Notes/Architectural Intent:
        Informational command listing available rules, workflows, and skills.
    """
    asset_adapter = adapter or FileSystemAgentAssetAdapter()
    assets = asset_adapter.load_bundled_assets()

    active_presenter = presenter or create_agent_presenter(format_type=format_type)
    return active_presenter.present_list(assets)
