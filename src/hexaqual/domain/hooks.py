"""Domain models and value objects for Git hooks lifecycle management.

Notes/Architectural Intent:
    Pure domain models defining Git hook stages, install modes, manager types,
    and verification reports with zero external framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

__all__ = [
    "CommitMsgReport",
    "HookInstallMode",
    "HookManager",
    "HooksInstallReport",
    "HookStage",
    "HookStatusInfo",
    "HooksUninstallReport",
]


class HookStage(StrEnum):
    """Supported Git hook execution lifecycle stages."""

    COMMIT_MSG = "commit-msg"
    POST_CHECKOUT = "post-checkout"
    POST_MERGE = "post-merge"
    PRE_COMMIT = "pre-commit"
    PRE_PUSH = "pre-push"


class HookInstallMode(StrEnum):
    """Strategy for installing Git hooks."""

    AUTO = "auto"
    NATIVE = "native"
    PRE_COMMIT = "pre-commit"


class HookManager(StrEnum):
    """Categorization of how an installed hook is managed."""

    NATIVE = "native"
    NONE = "none"
    PRE_COMMIT = "pre-commit"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HookStatusInfo:
    """Current installation status for a specific Git hook stage."""

    stage: HookStage
    is_installed: bool
    manager: HookManager
    script_path: Path


@dataclass(frozen=True)
class HooksInstallReport:
    """Outcome and diagnostics from a Git hooks installation run."""

    mode: HookInstallMode
    installed_stages: tuple[HookStage, ...]
    details: tuple[str, ...]
    success: bool


@dataclass(frozen=True)
class HooksUninstallReport:
    """Outcome and diagnostics from a Git hooks uninstallation run."""

    removed_stages: tuple[HookStage, ...]
    details: tuple[str, ...]
    success: bool


@dataclass(frozen=True)
class CommitMsgReport:
    """Validation report analyzing a commit message against governance rules."""

    is_valid: bool
    title: str
    errors: tuple[str, ...]
    dco_found: bool
    conventional_match: bool
