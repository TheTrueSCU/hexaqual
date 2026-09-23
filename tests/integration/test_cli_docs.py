"""Integration tests for hexaqual docs CLI subcommands.

Notes/Architectural Intent:
    Exercises end-to-end documentation publication and link scanning across
    a synthetic multi-package workspace with hermetic HTTP mocking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from hexaqual.cli.docs import docs_app


@pytest.mark.integration
def test_docs_publish_status(synthetic_workspace: Path, runner: CliRunner) -> None:
    """Verify hexaqual docs publish --status renders article registry state.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
    """
    res = runner.invoke(docs_app, ["publish", "--status", "--root", str(synthetic_workspace)])
    assert res.exit_code == 0
    assert "Slug" in res.stdout or "initial-setup" in res.stdout


@pytest.mark.integration
def test_docs_publish_dry_run(synthetic_workspace: Path, runner: CliRunner) -> None:
    """Verify --dry-run validates article without file mutation or HTTP traffic.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
    """
    article_path = synthetic_workspace / "docs" / "medium" / "article-0-intro.md"
    original_content = article_path.read_text(encoding="utf-8")

    res = runner.invoke(
        docs_app,
        [
            "publish",
            "article-0-intro",
            "--dry-run",
            "--api-key",
            "dummy-token",
            "--root",
            str(synthetic_workspace),
        ],
    )
    assert res.exit_code == 0
    current_content = article_path.read_text(encoding="utf-8")
    assert current_content == original_content


@pytest.mark.integration
def test_docs_publish_draft_and_live(
    synthetic_workspace: Path,
    runner: CliRunner,
    mock_devto_transport: httpx.MockTransport,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify two-phase publication workflow (draft upload then live publish).

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        mock_devto_transport: Mock transport intercepting DEV.to REST endpoints.
        monkeypatch: Pytest monkeypatch fixture.
    """
    orig_client_init = httpx.Client.__init__

    def patched_init(self: Any, *args: Any, **kwargs: Any) -> None:
        kwargs["transport"] = mock_devto_transport
        orig_client_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", patched_init)

    article_path = synthetic_workspace / "docs" / "medium" / "article-0-intro.md"

    # Phase 1: Draft upload
    res1 = runner.invoke(
        docs_app,
        [
            "publish",
            "article-0-intro",
            "--api-key",
            "test-token",
            "--root",
            str(synthetic_workspace),
        ],
    )
    assert res1.exit_code == 0
    content1 = article_path.read_text(encoding="utf-8")
    assert "devto_id:" in content1

    # Phase 2: Live publication
    res2 = runner.invoke(
        docs_app,
        [
            "publish",
            "article-0-intro",
            "--publish",
            "--api-key",
            "test-token",
            "--root",
            str(synthetic_workspace),
        ],
    )
    assert res2.exit_code == 0
    content2 = article_path.read_text(encoding="utf-8")
    assert "devto_url: https://dev.to/user/" in content2
    assert "canonical_url: https://dev.to/user/" in content2


@pytest.mark.integration
def test_docs_links_scan(synthetic_workspace: Path, runner: CliRunner) -> None:
    """Verify hexaqual docs links scans documentation directories.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
    """
    res = runner.invoke(
        docs_app,
        [
            "links",
            "--path",
            str(synthetic_workspace / "docs"),
            "--root",
            str(synthetic_workspace),
        ],
    )
    assert res.exit_code in (0, 1)
