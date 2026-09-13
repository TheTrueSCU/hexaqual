"""Unit tests for domain base models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hexaqual.domain.base import Command, DomainModel


class SampleModel(DomainModel):
    """Sample immutable domain model."""

    name: str


class SampleCommand(Command):
    """Sample immutable command."""

    action: str


def test_domain_model_immutability() -> None:
    """Verify domain models are frozen."""
    model = SampleModel(name="test")
    with pytest.raises(ValidationError):
        model.name = "updated"  # type: ignore[misc]


def test_command_forbids_extra_fields() -> None:
    """Verify commands forbid extra undeclared attributes."""
    with pytest.raises(ValidationError):
        SampleCommand(action="run", extra_arg="forbidden")  # type: ignore[call-arg]
