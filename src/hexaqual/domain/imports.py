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


__all__ = [
    "optional_dependency",
]
