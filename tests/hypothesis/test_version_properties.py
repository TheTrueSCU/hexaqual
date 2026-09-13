"""Property-based tests for Hexaqual version structure."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

import hexaqual


@given(st.text())
def test_version_immutable(extra: str) -> None:
    """Verify package version is always fixed string."""
    assert hexaqual.__version__ == "0.0.0"
