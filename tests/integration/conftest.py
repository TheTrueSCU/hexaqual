"""Shared integration test fixtures providing synthetic multi-package workspaces and hermetic HTTP mocks.

Notes/Architectural Intent:
    Establishes isolated, temporary workspace environments for testing Hexaqual CLI
    commands end-to-end without touching the host filesystem or making external network calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Typer CLI runner with isolated output streams.

    Returns:
        CliRunner instance.

    Notes/Architectural Intent:
        Enables testing CLI commands end-to-end with exit code verification.
    """
    return CliRunner()


@pytest.fixture
def mock_devto_transport() -> httpx.MockTransport:
    """Hermetic mock HTTP transport simulating DEV.to REST API endpoints.

    Returns:
        httpx.MockTransport configured with deterministic responses.

    Notes/Architectural Intent:
        Guarantees zero outbound socket traffic while testing docs publishing workflows.
    """
    articles_db: dict[int, dict[str, Any]] = {}
    next_id = 1001

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal next_id
        path = request.url.path

        if request.method == "POST" and path == "/api/articles":
            payload = json.loads(request.content.decode("utf-8"))
            article_id = next_id
            next_id += 1
            title = payload.get("article", {}).get("title", "Untitled")
            slug = title.lower().replace(" ", "-")
            url = f"https://dev.to/user/{slug}-{article_id}"
            article_data = {
                "id": article_id,
                "title": title,
                "url": url,
                "published": payload.get("article", {}).get("published", False),
                "body_markdown": payload.get("article", {}).get("body_markdown", ""),
            }
            articles_db[article_id] = article_data
            return httpx.Response(201, json=article_data)

        if request.method in ("PUT", "PATCH") and path.startswith("/api/articles/"):
            try:
                article_id = int(path.split("/")[-1])
            except ValueError:
                return httpx.Response(400, json={"error": "Invalid article ID"})

            if article_id not in articles_db:
                return httpx.Response(404, json={"error": "Not found"})

            payload = json.loads(request.content.decode("utf-8"))
            article = articles_db[article_id]
            article_update = payload.get("article", {})
            if "title" in article_update:
                article["title"] = article_update["title"]
            if "published" in article_update:
                article["published"] = article_update["published"]
            if "body_markdown" in article_update:
                article["body_markdown"] = article_update["body_markdown"]
            return httpx.Response(200, json=article)

        if request.method == "GET" and path == "/api/articles/me/all":
            return httpx.Response(200, json=list(articles_db.values()))

        return httpx.Response(404, json={"error": f"Unhandled mock route: {request.method} {path}"})

    return httpx.MockTransport(handler)


@pytest.fixture
def synthetic_workspace(tmp_path: Path) -> Path:
    """Scaffold a realistic synthetic multi-package workspace.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the root of the created synthetic workspace.

    Notes/Architectural Intent:
        Creates a valid uv workspace with packages, optional dependencies, docs,
        and draft Markdown files for end-to-end integration validation.
    """
    root = tmp_path / "workspace"
    root.mkdir()

    # Root pyproject.toml
    root_pyproject = root / "pyproject.toml"
    root_pyproject.write_text(
        """[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
pkg-core = { workspace = true }
pkg-events = { workspace = true }
umbrella-pkg = { workspace = true }

[dependency-groups]
dev = [
    "hexaqual>=0.5.0",
]
"""
    )

    # Docs directory with blog index and medium registry
    docs_dir = root / "docs"
    docs_dir.mkdir()
    blog_dir = docs_dir / "blog"
    blog_dir.mkdir()
    (blog_dir / "index.md").write_text(
        """# Engineering Blog

| Title | Slug | Topic | Published Date | Canonical URL |
|---|---|---|---|---|
| Initial Setup | initial-setup | Architecture | 2026-09-01 | https://dev.to/user/initial-setup-1000 |
"""
    )

    medium_dir = docs_dir / "medium"
    medium_dir.mkdir()
    (medium_dir / "README.md").write_text(
        """# Medium Articles Registry

| Title | Slug | DEV.to URL | Medium URL | Status |
|---|---|---|---|---|
| Initial Setup | initial-setup | https://dev.to/user/initial-setup-1000 | | Published |
"""
    )

    # Draft article 0
    (medium_dir / "article-0-intro.md").write_text(
        """---
title: "Article 0: Intro to Architecture"
subtitle: "Getting started with hexagonal design"
date: 2026-09-08
status: draft
tags: [python, architecture]
cross_post:
  devto: true
  canonical_url: ""
---

# Article 0: Intro to Architecture

Welcome to the series. Check out [Patterns](devto://patterns) for the next step.
"""
    )

    # Draft article 1
    (medium_dir / "article-1-patterns.md").write_text(
        """---
title: "Article 1: Architectural Patterns"
subtitle: "Ports and adapters in practice"
date: 2026-09-09
status: draft
tags: [python, patterns]
cross_post:
  devto: true
  canonical_url: ""
---

# Article 1: Architectural Patterns

Building on [Intro](devto://intro-to-architecture), we explore ports and adapters.
"""
    )

    # Packages
    packages_dir = root / "packages"
    packages_dir.mkdir()

    # Package: pkg_core
    pkg_core = packages_dir / "pkg_core"
    pkg_core.mkdir()
    (pkg_core / "pyproject.toml").write_text(
        """[project]
name = "pkg-core"
version = "0.1.0"
dependencies = []
"""
    )
    src_core = pkg_core / "src" / "pkg_core"
    src_core.mkdir(parents=True)
    (src_core / "__init__.py").write_text(
        """\"\"\"Core primitives.\"\"\"

from pkg_core.models import User

__all__ = [
    "User",
]
"""
    )
    (src_core / "models.py").write_text(
        """\"\"\"Domain models.\"\"\"

class User:
    def __init__(self, name: str) -> None:
        self.name = name

__all__ = [
    "User",
]
"""
    )
    tests_core = pkg_core / "tests" / "unit"
    tests_core.mkdir(parents=True)
    (tests_core / "__init__.py").write_text("")
    (tests_core / "test_models.py").write_text(
        """from pkg_core.models import User

def test_user():
    user = User("Alice")
    assert user.name == "Alice"
"""
    )

    # Package: pkg_events
    pkg_events = packages_dir / "pkg_events"
    pkg_events.mkdir()
    (pkg_events / "pyproject.toml").write_text(
        """[project]
name = "pkg-events"
version = "0.1.0"
dependencies = ["pkg-core"]

[project.optional-dependencies]
nats = ["nats-py>=2.3.0"]
huey = ["huey>=3.3.4"]

[tool.uv.sources]
pkg-core = { workspace = true }
"""
    )
    src_events = pkg_events / "src" / "pkg_events"
    src_events.mkdir(parents=True)
    (src_events / "__init__.py").write_text(
        """\"\"\"Events module.\"\"\"

__all__ = []
"""
    )
    (src_events / "events.py").write_text(
        """\"\"\"Events logic.\"\"\"

__all__ = []
"""
    )
    tests_events = pkg_events / "tests" / "unit"
    tests_events.mkdir(parents=True)
    (tests_events / "__init__.py").write_text("")
    (tests_events / "test_events.py").write_text(
        """def test_events_placeholder():
    assert True
"""
    )

    # Package: umbrella_pkg
    umbrella = packages_dir / "umbrella_pkg"
    umbrella.mkdir()
    (umbrella / "pyproject.toml").write_text(
        """[project]
name = "umbrella-pkg"
version = "0.1.0"
dependencies = [
    "pkg-core",
    "pkg-events",
]

[project.optional-dependencies]
events-nats = ["pkg-events[nats]"]
events-huey = ["pkg-events[huey]"]

[tool.uv.sources]
pkg-core = { workspace = true }
pkg-events = { workspace = true }
"""
    )
    src_umbrella = umbrella / "src" / "umbrella_pkg"
    src_umbrella.mkdir(parents=True)
    (src_umbrella / "__init__.py").write_text(
        """\"\"\"Umbrella exports.\"\"\"

__all__ = []
"""
    )
    (src_umbrella / "umbrella.py").write_text(
        """\"\"\"Umbrella entrypoint.\"\"\"

__all__ = []
"""
    )
    tests_umbrella = umbrella / "tests" / "unit"
    tests_umbrella.mkdir(parents=True)
    (tests_umbrella / "__init__.py").write_text("")
    (tests_umbrella / "test_umbrella.py").write_text(
        """def test_umbrella_placeholder():
    assert True
"""
    )

    return root
