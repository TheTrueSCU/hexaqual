"""Property-based tests for Hexaqual version structure."""

from __future__ import annotations

import re

from hypothesis import given
from hypothesis import strategies as st

import hexaqual

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+")


@given(st.text())
def test_version_immutable(extra: str) -> None:
    """Verify package version is always a valid semver string."""
    assert isinstance(hexaqual.__version__, str)
    assert SEMVER_PATTERN.match(hexaqual.__version__) is not None
