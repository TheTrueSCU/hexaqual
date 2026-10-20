"""Unit tests for OpenSSF port contracts.

Notes/Architectural Intent:
    Verifies abstract interface requirements and ABC instantiation behaviors
    for OpenSsfBadgePort.
"""

from __future__ import annotations

import inspect

from hexaqual.ports.openssf import OpenSsfBadgePort, OpenSsfScorecardPort


def test_openssf_badge_port_is_abstract() -> None:
    """Test that OpenSsfBadgePort is an abstract interface."""
    assert inspect.isabstract(OpenSsfBadgePort)
    assert "build_proposal_urls" in OpenSsfBadgePort.__abstractmethods__


def test_openssf_scorecard_port_is_abstract() -> None:
    """Test that OpenSsfScorecardPort is an abstract interface."""
    assert inspect.isabstract(OpenSsfScorecardPort)
    assert "fetch_scorecard" in OpenSsfScorecardPort.__abstractmethods__
