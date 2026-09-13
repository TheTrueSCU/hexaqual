"""CLI package exports for Hexaqual.

Notes/Architectural Intent:
    Provides Typer CLI entrypoints for developer interactive usage and CI automation.
"""

from __future__ import annotations

from hexaqual.cli.main import app

__all__ = [
    "app",
]
