"""Base model and command classes for Hexaqual domain.

Notes/Architectural Intent:
    Defines immutable, strictly validated Pydantic models for domain value objects
    and commands with zero dependencies on external frameworks.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Base immutable Pydantic model for Hexaqual domain entities."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Command(DomainModel):
    """Base class for all intent-capturing Command objects."""


__all__ = [
    "Command",
    "DomainModel",
]
