"""Unit tests for dynamic module import helpers and optional dependency guards."""

from __future__ import annotations

from unittest.mock import patch

from hexaqual.domain.imports import optional_dependency, require_dependency


def test_optional_dependency_returns_module_when_available() -> None:
    """Verify optional_dependency returns the imported module for installed packages."""
    math_mod = optional_dependency("math")
    is_not_none = math_mod is not None
    assert is_not_none is True
    has_sqrt = hasattr(math_mod, "sqrt")
    assert has_sqrt is True


def test_optional_dependency_returns_default_when_missing() -> None:
    """Verify optional_dependency returns default value when ModuleNotFoundError is raised."""
    missing = optional_dependency("non_existent_package_xyz_123")
    is_none = missing is None
    assert is_none is True

    custom_default = optional_dependency("non_existent_package_xyz_123", default="fallback")
    is_fallback = custom_default == "fallback"
    assert is_fallback is True


def test_optional_dependency_with_mocked_import() -> None:
    """Verify optional_dependency delegates to importlib.import_module."""
    with patch("importlib.import_module", side_effect=ModuleNotFoundError("Module missing")):
        res = optional_dependency("some_pkg", default=42)
        is_42 = res == 42
        assert is_42 is True


def test_require_dependency_success() -> None:
    """Verify require_dependency returns module when available."""
    sys_mod = require_dependency("sys")
    is_not_none = sys_mod is not None
    assert is_not_none is True


def test_require_dependency_raises_with_actionable_hint() -> None:
    """Verify require_dependency raises ImportError with extra installation hint."""
    import pytest

    with pytest.raises(ImportError, match="hexaqual\\[cluster\\]") as exc_info:
        require_dependency("fake_cluster_pkg", extra="cluster", feature_name="Hexaqueue cluster")
    has_msg = "The Hexaqueue cluster feature requires fake_cluster_pkg." in str(exc_info.value)
    assert has_msg is True

    with pytest.raises(ImportError, match="uv pip install") as exc_info2:
        require_dependency("standalone_tool")
    has_pip = "uv pip install standalone_tool" in str(exc_info2.value)
    assert has_pip is True
