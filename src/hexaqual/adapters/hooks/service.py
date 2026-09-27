"""Service layer orchestrating Git hooks lifecycle commands.

Notes/Architectural Intent:
    Connects driving CLI controllers with GitHooksAdapter and HooksPresenterPort.
    Keeps CLI thin and decouples presentation from core hook orchestration.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hexaqual.adapters.hooks.git_hooks import GitHooksAdapter
from hexaqual.adapters.presenters.hooks import RichHooksPresenter
from hexaqual.domain.hooks import HookInstallMode
from hexaqual.ports.hooks import GitHooksPort, HooksPresenterPort

__all__ = [
    "check_hooks_command",
    "install_hooks_command",
    "uninstall_hooks_command",
    "validate_commit_msg_command",
]


def install_hooks_command(
    target_dir: Path | None = None,
    mode: HookInstallMode = HookInstallMode.AUTO,
    presenter: HooksPresenterPort | None = None,
    adapter: GitHooksPort | None = None,
) -> int:
    """Install Git lifecycle hooks in the target repository.

    Args:
        target_dir: Optional path to repository root (defaults to CWD).
        mode: Hook installation mode (auto, pre-commit, native).
        presenter: Optional presenter port override for testing.
        adapter: Optional hooks port override for testing.

    Returns:
        Process exit code (0 for success).

    Raises:
        None.

    Notes/Architectural Intent:
        Delegates to adapter and formats report through presenter.
    """
    repo_root = target_dir or Path.cwd()
    hooks_adapter = adapter or GitHooksAdapter()
    hooks_presenter = presenter or RichHooksPresenter()

    report = hooks_adapter.install_hooks(repo_root=repo_root, mode=mode)
    return hooks_presenter.present_install(report)


def uninstall_hooks_command(
    target_dir: Path | None = None,
    presenter: HooksPresenterPort | None = None,
    adapter: GitHooksPort | None = None,
) -> int:
    """Uninstall Git lifecycle hooks from the target repository.

    Args:
        target_dir: Optional path to repository root (defaults to CWD).
        presenter: Optional presenter port override for testing.
        adapter: Optional hooks port override for testing.

    Returns:
        Process exit code (0 for success).

    Raises:
        None.

    Notes/Architectural Intent:
        Removes managed hooks and reports outcome.
    """
    repo_root = target_dir or Path.cwd()
    hooks_adapter = adapter or GitHooksAdapter()
    hooks_presenter = presenter or RichHooksPresenter()

    report = hooks_adapter.uninstall_hooks(repo_root=repo_root)
    return hooks_presenter.present_uninstall(report)


def check_hooks_command(
    target_dir: Path | None = None,
    presenter: HooksPresenterPort | None = None,
    adapter: GitHooksPort | None = None,
) -> int:
    """Inspect and report Git lifecycle hook statuses in the target repository.

    Args:
        target_dir: Optional path to repository root (defaults to CWD).
        presenter: Optional presenter port override for testing.
        adapter: Optional hooks port override for testing.

    Returns:
        Process exit code (0 if all hooks active, 1 otherwise).

    Raises:
        None.

    Notes/Architectural Intent:
        Inspects each lifecycle stage and renders Rich summary dashboard.
    """
    repo_root = target_dir or Path.cwd()
    hooks_adapter = adapter or GitHooksAdapter()
    hooks_presenter = presenter or RichHooksPresenter()

    statuses = hooks_adapter.check_hooks(repo_root=repo_root)
    return hooks_presenter.present_check(statuses)


def validate_commit_msg_command(
    msg_file: Path | None = None,
    msg_text: str | None = None,
    require_dco: bool = True,
    require_conventional: bool = True,
    presenter: HooksPresenterPort | None = None,
    adapter: GitHooksPort | None = None,
) -> int:
    """Validate a commit message against Conventional Commits and DCO requirements.

    Args:
        msg_file: Path to commit message file (e.g. .git/COMMIT_EDITMSG).
        msg_text: Optional explicit commit message string.
        require_dco: Whether to enforce Signed-off-by trailer.
        require_conventional: Whether to enforce Conventional Commits title format.
        presenter: Optional presenter port override for testing.
        adapter: Optional hooks port override for testing.

    Returns:
        Process exit code (0 if valid, 1 if invalid).

    Raises:
        None.

    Notes/Architectural Intent:
        Powers commit-msg hook verification across Git and pre-commit workflows.
    """
    hooks_adapter = adapter or GitHooksAdapter()
    hooks_presenter = presenter or RichHooksPresenter()

    raw_text: str
    if msg_text is not None:
        raw_text = msg_text
    elif msg_file is not None and msg_file.is_file():
        raw_text = msg_file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        raw_text = sys.stdin.read()
    else:
        raw_text = ""

    report = hooks_adapter.validate_commit_msg(
        msg=raw_text,
        require_dco=require_dco,
        require_conventional=require_conventional,
    )
    return hooks_presenter.present_commit_msg(report)
