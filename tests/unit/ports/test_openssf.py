"""Unit tests for OpenSSF port contracts.

Notes/Architectural Intent:
    Verifies abstract interface requirements and ABC instantiation behaviors
    for OpenSsfBadgePort.
"""

from __future__ import annotations

import pytest

from hexaqual.ports.openssf import OpenSsfBadgePort, OpenSsfScorecardPort


def test_openssf_badge_port_is_abstract() -> None:
    """Test that OpenSsfBadgePort cannot be instantiated directly without implementations."""
    with pytest.raises(TypeError):
        OpenSsfBadgePort()  # type: ignore[abstract]


def test_openssf_scorecard_port_is_abstract() -> None:
    """Test that OpenSsfScorecardPort cannot be instantiated directly without implementations."""
    with pytest.raises(TypeError):
        OpenSsfScorecardPort()  # type: ignore[abstract]
