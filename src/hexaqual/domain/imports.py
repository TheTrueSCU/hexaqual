"""Dynamic module import helpers and optional dependency guards.

Notes/Architectural Intent:
    Provides standardized runtime verification for optional package extras
    without introducing third-party dependencies to hexaqual domain.
"""

from __future__ import annotations

import importlib
from typing import Any


def optional_dependency(
    module_name: str,
    *,
    default: Any = None,
) -> Any:
    """Import an optional third-party module, returning a default value if unavailable.

    Args:
        module_name: Python module import path (e.g. 'pytest_hexaqueue', 'pytest_benchmark').
        default: Fallback value returned if the module is not installed (defaults to None).

    Returns:
        The imported module object, or `default` if ModuleNotFoundError is encountered.

    Notes/Architectural Intent:
        Standardizes optional dependency verification across adapters, providing
        a safe mechanism for progressive enhancement without boilerplate try/except blocks.
    """
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return default


def require_dependency(
    module_name: str,
    *,
    extra: str | None = None,
    feature_name: str | None = None,
) -> Any:
    """Import a required module or raise ImportError with actionable installation advice.

    Args:
        module_name: Python module import path (e.g. 'pytest_hexaqueue').
        extra: Optional extra package name in pyproject.toml (e.g. 'cluster').
        feature_name: Optional human-readable feature name for diagnostic message.

    Returns:
        The imported module object.

    Raises:
        ImportError: If the module is not installed.

    Notes/Architectural Intent:
        Guarantees clear, uniform user instructions when optional extras are missing,
        preventing obscure ModuleNotFoundError tracebacks in higher-level driving adapters.
    """
    mod = optional_dependency(module_name)
    if mod is not None:
        return mod
    feat = feature_name or f"'{module_name}'"
    hint = f"uv add 'hexaqual[{extra}]'" if extra else f"uv pip install {module_name}"
    msg = f"The {feat} feature requires {module_name}.\nInstall it via: {hint}"
    raise ImportError(msg)


__all__ = [
    "optional_dependency",
    "require_dependency",
]
