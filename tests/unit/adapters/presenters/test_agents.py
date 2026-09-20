"""Unit tests for agent presenter adapters.

Notes/Architectural Intent:
    Validates Rich, JSON, and Markdown presentation adapters for agent sync,
    drift check, and catalog listing using captured console outputs.
"""

from __future__ import annotations

import io

from rich.console import Console

from hexaqual.adapters.presenters.agents import (
    JsonAgentPresenterAdapter,
    MarkdownAgentPresenterAdapter,
    RichAgentPresenterAdapter,
    create_agent_presenter,
)
from hexaqual.domain.agents import (
    AgentAsset,
    AgentAssetKind,
    AgentCheckReport,
    AgentSyncReport,
)


def _create_sample_sync_report() -> AgentSyncReport:
    return AgentSyncReport(
        created_count=2,
        updated_count=1,
        unchanged_count=15,
        preserved_unmanaged_count=3,
        details=("Created rules/rule1.md", "Updated workflows/wf1.md"),
    )


def _create_sample_check_report(is_clean: bool) -> AgentCheckReport:
    if is_clean:
        return AgentCheckReport(is_clean=True, drifted_files=(), missing_files=(), details=())
    return AgentCheckReport(
        is_clean=False,
        drifted_files=("rules/rule1.md",),
        missing_files=("workflows/wf1.md",),
        details=("Drift detected",),
    )


def _create_sample_assets() -> tuple[AgentAsset, ...]:
    return (
        AgentAsset(
            "hexaqual-boundaries.md",
            AgentAssetKind.RULE,
            "rules/hexaqual-boundaries.md",
            "# Content",
        ),
        AgentAsset(
            "hexaqual-pre-commit.md",
            AgentAssetKind.WORKFLOW,
            "workflows/hexaqual-pre-commit.md",
            "# Content",
        ),
    )


def test_create_agent_presenter_factory() -> None:
    """Verify factory returns appropriate presenter subclass.

    Notes/Architectural Intent:
        Confirms format string selection maps to correct adapter.
    """
    table_p = create_agent_presenter("table")
    json_p = create_agent_presenter("json")
    md_p = create_agent_presenter("markdown")

    assert isinstance(table_p, RichAgentPresenterAdapter)
    assert isinstance(json_p, JsonAgentPresenterAdapter)
    assert isinstance(md_p, MarkdownAgentPresenterAdapter)


def test_rich_agent_presenter_methods() -> None:
    """Verify RichAgentPresenterAdapter renders without errors and returns valid exit codes.

    Notes/Architectural Intent:
        Validates exit code contracts for clean (0) and dirty (1) checks.
    """
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False)
    presenter = RichAgentPresenterAdapter(console=console)

    sync_exit = presenter.present_sync(_create_sample_sync_report())
    clean_exit = presenter.present_check(_create_sample_check_report(is_clean=True))
    dirty_exit = presenter.present_check(_create_sample_check_report(is_clean=False))
    list_exit = presenter.present_list(_create_sample_assets())

    output = buf.getvalue()

    assert sync_exit == 0
    assert clean_exit == 0
    assert dirty_exit == 1
    assert list_exit == 0
    assert "Synchronization" in output
    assert "Drift Detection" in output
    assert "Catalog" in output


def test_json_agent_presenter_methods() -> None:
    """Verify JsonAgentPresenterAdapter emits valid JSON and returns valid exit codes.

    Notes/Architectural Intent:
        Asserts parseable JSON payload on stdout.
    """
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False)
    presenter = JsonAgentPresenterAdapter(console=console)

    sync_exit = presenter.present_sync(_create_sample_sync_report())
    clean_exit = presenter.present_check(_create_sample_check_report(is_clean=True))
    dirty_exit = presenter.present_check(_create_sample_check_report(is_clean=False))
    list_exit = presenter.present_list(_create_sample_assets())

    assert sync_exit == 0
    assert clean_exit == 0
    assert dirty_exit == 1
    assert list_exit == 0


def test_markdown_agent_presenter_methods() -> None:
    """Verify MarkdownAgentPresenterAdapter emits Markdown and returns valid exit codes.

    Notes/Architectural Intent:
        Asserts Markdown table structure for CI summary presentation.
    """
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False)
    presenter = MarkdownAgentPresenterAdapter(console=console)

    sync_exit = presenter.present_sync(_create_sample_sync_report())
    clean_exit = presenter.present_check(_create_sample_check_report(is_clean=True))
    dirty_exit = presenter.present_check(_create_sample_check_report(is_clean=False))
    list_exit = presenter.present_list(_create_sample_assets())

    output = buf.getvalue()

    assert sync_exit == 0
    assert clean_exit == 0
    assert dirty_exit == 1
    assert list_exit == 0
    assert "# Hexaqual Universal Agent Guardrails Synchronization" in output
