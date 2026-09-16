"""Unit tests for Hexaqual version and exports."""

from __future__ import annotations

import hexaqual


def test_version_string() -> None:
    """Ensure version string is well-formed semver."""
    version = hexaqual.__version__
    assert version == "0.4.0"
    parts = version.split(".")
    assert len(parts) == 3
