"""Agent asset adapters for filesystem and package resources.

Notes/Architectural Intent:
    Exposes concrete implementations of AgentAssetPort.
"""

from __future__ import annotations

from hexaqual.adapters.agents.fs import FileSystemAgentAssetAdapter

__all__ = [
    "FileSystemAgentAssetAdapter",
]
