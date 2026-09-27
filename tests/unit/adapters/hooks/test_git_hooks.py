"""Unit tests for GitHooksAdapter.

Notes/Architectural Intent:
    Validates Git directory discovery, native script templating and chmod execution,
    pre-commit delegation, uninstallation safety, hook status inspection,
    and semantic Conventional Commit + DCO sign-off validation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.adapters.hooks.git_hooks import (
    HEXAQUAL_HOOK_HEADER,
    GitHooksAdapter,
)
from hexaqual.domain.hooks import (
    HookInstallMode,
    HookManager,
    HookStage,
)


def test_resolve_git_dir_and_hooks_dir(tmp_path: Path) -> None:
    """Verify Git directory resolution for regular repositories and worktrees."""
    adapter = GitHooksAdapter()

    # 1. Non-existent git repo
    no_git = adapter.resolve_git_dir(tmp_path)
    assert no_git is None
    no_hooks = adapter.resolve_hooks_dir(tmp_path)
    assert no_hooks is None

    # 2. Standard directory repo
    dot_git = tmp_path / ".git"
    dot_git.mkdir()
    res_git = adapter.resolve_git_dir(tmp_path)
    assert res_git == dot_git

    res_hooks = adapter.resolve_hooks_dir(tmp_path)
    assert res_hooks == dot_git / "hooks"

    # 3. Worktree .git file
    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
    actual_gitdir = tmp_path / "main_repo" / ".git" / "worktrees" / "worktree"
    actual_gitdir.mkdir(parents=True)
    (worktree_root / ".git").write_text(f"gitdir: {actual_gitdir}\n", encoding="utf-8")

    res_wt_git = adapter.resolve_git_dir(worktree_root)
    assert res_wt_git == actual_gitdir

    # With commondir
    (actual_gitdir / "commondir").write_text("../..\n", encoding="utf-8")
    res_wt_hooks = adapter.resolve_hooks_dir(worktree_root)
    assert res_wt_hooks == (tmp_path / "main_repo" / ".git" / "hooks")


def test_install_native_hooks(tmp_path: Path) -> None:
    """Verify native installation generates executable scripts with header."""
    adapter = GitHooksAdapter()
    (tmp_path / ".git").mkdir()

    report = adapter.install_hooks(repo_root=tmp_path, mode=HookInstallMode.NATIVE)
    success = report.success
    mode = report.mode
    stages = report.installed_stages

    assert success is True
    assert mode == HookInstallMode.NATIVE
    assert len(stages) == 5

    hooks_dir = tmp_path / ".git" / "hooks"
    for stage in HookStage:
        script = hooks_dir / stage.value
        assert script.is_file()
        content = script.read_text(encoding="utf-8")
        assert HEXAQUAL_HOOK_HEADER in content


def test_install_precommit_hooks(tmp_path: Path) -> None:
    """Verify pre-commit installation delegates to pre-commit CLI."""
    adapter = GitHooksAdapter()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")

    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "pre-commit installed\n"

    with patch("subprocess.run", return_value=mock_run) as mock_sub:
        report = adapter.install_hooks(repo_root=tmp_path, mode=HookInstallMode.PRE_COMMIT)
        called = mock_sub.called
        success = report.success
        stages = report.installed_stages

        assert called is True
        assert success is True
        assert len(stages) == 5


def test_install_hooks_not_a_git_repo(tmp_path: Path) -> None:
    """Verify installation fails gracefully if not in a Git repository."""
    adapter = GitHooksAdapter()
    report = adapter.install_hooks(repo_root=tmp_path, mode=HookInstallMode.AUTO)

    success = report.success
    assert success is False
    assert "not a valid Git repository" in report.details[0]


def test_uninstall_hooks(tmp_path: Path) -> None:
    """Verify uninstallation cleans managed native scripts and preserves unmanaged hooks."""
    adapter = GitHooksAdapter()
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)

    # 1. Managed script
    managed_script = hooks_dir / "pre-commit"
    managed_script.write_text(f"#!/bin/bash\n{HEXAQUAL_HOOK_HEADER}\nexit 0\n", encoding="utf-8")

    # 2. Unmanaged script
    unmanaged_script = hooks_dir / "commit-msg"
    unmanaged_script.write_text("#!/bin/bash\n# Custom company hook\nexit 0\n", encoding="utf-8")

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        report = adapter.uninstall_hooks(repo_root=tmp_path)
        success = report.success
        removed = report.removed_stages

        assert success is True
        assert HookStage.PRE_COMMIT in removed
        assert HookStage.COMMIT_MSG not in removed

    assert not managed_script.exists()
    assert unmanaged_script.exists()


def test_check_hooks(tmp_path: Path) -> None:
    """Verify inspection distinguishes between pre-commit, native, unknown, and none."""
    adapter = GitHooksAdapter()
    hooks_dir = tmp_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)

    (hooks_dir / "pre-commit").write_text("#!/bin/bash\n# pre-commit wrapper\n", encoding="utf-8")
    (hooks_dir / "commit-msg").write_text(
        f"#!/bin/bash\n{HEXAQUAL_HOOK_HEADER}\n", encoding="utf-8"
    )
    (hooks_dir / "pre-push").write_text("#!/bin/bash\n# custom\n", encoding="utf-8")
    # post-merge and post-checkout do not exist

    statuses = adapter.check_hooks(repo_root=tmp_path)
    status_map = {s.stage: s for s in statuses}

    assert status_map[HookStage.PRE_COMMIT].is_installed is True
    assert status_map[HookStage.PRE_COMMIT].manager == HookManager.PRE_COMMIT

    assert status_map[HookStage.COMMIT_MSG].is_installed is True
    assert status_map[HookStage.COMMIT_MSG].manager == HookManager.NATIVE

    assert status_map[HookStage.PRE_PUSH].is_installed is True
    assert status_map[HookStage.PRE_PUSH].manager == HookManager.UNKNOWN

    assert status_map[HookStage.POST_MERGE].is_installed is False
    assert status_map[HookStage.POST_MERGE].manager == HookManager.NONE


def test_validate_commit_msg_empty() -> None:
    """Verify validation rejects empty commit message."""
    adapter = GitHooksAdapter()
    res = adapter.validate_commit_msg("   \n# comment\n")
    assert res.is_valid is False
    assert "empty" in res.errors[0]


def test_validate_commit_msg_conventional_and_dco() -> None:
    """Verify validation enforces Conventional Commits title and DCO trailer."""
    adapter = GitHooksAdapter()

    # 1. Fully valid
    valid_msg = (
        "feat(hooks): add git hooks automation\n\n"
        "Detailed explanation here.\n\n"
        "Signed-off-by: Developer <dev@example.com>\n"
    )
    res_valid = adapter.validate_commit_msg(valid_msg)
    assert res_valid.is_valid is True
    assert res_valid.conventional_match is True
    assert res_valid.dco_found is True

    # 2. Missing DCO trailer
    no_dco_msg = "feat(hooks): add git hooks automation\n\nNo signoff."
    res_no_dco = adapter.validate_commit_msg(no_dco_msg, require_dco=True)
    assert res_no_dco.is_valid is False
    assert res_no_dco.dco_found is False
    assert any("DCO" in err for err in res_no_dco.errors)

    # Allowed without DCO if require_dco=False
    res_allowed_no_dco = adapter.validate_commit_msg(no_dco_msg, require_dco=False)
    assert res_allowed_no_dco.is_valid is True

    # 3. Invalid title format
    bad_title_msg = "Updated some stuff\n\nSigned-off-by: Developer <dev@example.com>\n"
    res_bad_title = adapter.validate_commit_msg(bad_title_msg)
    assert res_bad_title.is_valid is False
    assert res_bad_title.conventional_match is False
    assert any("Conventional Commits" in err for err in res_bad_title.errors)


def test_validate_commit_msg_merge_exempt() -> None:
    """Verify merge commits are exempt from conventional format and DCO requirements."""
    adapter = GitHooksAdapter()
    merge_msg = "Merge branch 'main' into feat/branch\n"
    res = adapter.validate_commit_msg(merge_msg)
    assert res.is_valid is True
