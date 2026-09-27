"""Concrete adapter for managing Git lifecycle hooks and commit message validation.

Notes/Architectural Intent:
    Implements GitHooksPort to manage both pre-commit multi-stage hooks and
    standalone native bash scripts. Validates Conventional Commits and OpenSSF DCO sign-off.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from hexaqual.domain.hooks import (
    CommitMsgReport,
    HookInstallMode,
    HookManager,
    HooksInstallReport,
    HookStage,
    HookStatusInfo,
    HooksUninstallReport,
)
from hexaqual.ports.hooks import GitHooksPort

__all__ = [
    "GitHooksAdapter",
    "HEXAQUAL_HOOK_HEADER",
]

HEXAQUAL_HOOK_HEADER = "# Managed by hexaqual"

CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\([a-zA-Z0-9_\-\./]+\))?(!)?:\s+.+$"
)

DCO_PATTERN = re.compile(r"^Signed-off-by:\s+([^<]+)\s+<([^>]+)>$", re.MULTILINE)

NATIVE_HOOK_TEMPLATES: dict[HookStage, str] = {
    HookStage.PRE_COMMIT: f"""#!/usr/bin/env bash
{HEXAQUAL_HOOK_HEADER}
set -e

echo "[hexaqual] Running pre-commit quality sanity checks..."
uv run hexaqual sanity -a --skip-tests
""",
    HookStage.COMMIT_MSG: f"""#!/usr/bin/env bash
{HEXAQUAL_HOOK_HEADER}
set -e

uv run hexaqual hooks commit-msg "$1"
""",
    HookStage.PRE_PUSH: f"""#!/usr/bin/env bash
{HEXAQUAL_HOOK_HEADER}
set -e

echo "[hexaqual] Running pre-push verification..."
uv run hexaqual sanity -a --skip-tests
""",
    HookStage.POST_MERGE: f"""#!/usr/bin/env bash
{HEXAQUAL_HOOK_HEADER}
set -e

if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD 2>/dev/null | grep -qE '(uv\\.lock|pyproject\\.toml|\\.agents/)'; then
    echo "[hexaqual] Upstream dependencies or agent guardrails changed. Synchronizing..."
    uv sync --quiet && uv run hexaqual agents sync
fi
""",
    HookStage.POST_CHECKOUT: f"""#!/usr/bin/env bash
{HEXAQUAL_HOOK_HEADER}
set -e

# Parameters: $1 = prev head, $2 = new head, $3 = flag (1 if branch checkout)
if [ "$3" = "1" ]; then
    if git diff --name-only "$1" "$2" 2>/dev/null | grep -qE '(uv\\.lock|pyproject\\.toml|\\.agents/)'; then
        echo "[hexaqual] Branch dependencies or agent guardrails changed. Synchronizing..."
        uv sync --quiet && uv run hexaqual agents sync
    fi
fi
""",
}


class GitHooksAdapter(GitHooksPort):
    """Adapter for inspecting, installing, and validating repository Git hooks."""

    def resolve_git_dir(self, repo_root: Path) -> Path | None:
        """Resolve the active .git directory, handling worktrees and submodules.

        Args:
            repo_root: Root directory of the repository.

        Returns:
            Path to the .git directory or None if not a Git repository.

        Notes/Architectural Intent:
            Correctly handles linked Git worktrees where .git is a file referencing gitdir.
        """
        dot_git = repo_root / ".git"
        if not dot_git.exists():
            return None
        if dot_git.is_dir():
            return dot_git

        # .git file in worktree or submodule
        try:
            content = dot_git.read_text(encoding="utf-8").strip()
            if content.startswith("gitdir:"):
                target = content.split("gitdir:", 1)[1].strip()
                target_path = Path(target)
                return (
                    target_path
                    if target_path.is_absolute()
                    else (repo_root / target_path).resolve()
                )
        except OSError:
            return None

        return None

    def resolve_hooks_dir(self, repo_root: Path) -> Path | None:
        """Resolve the .git/hooks directory for the target repository.

        Args:
            repo_root: Root directory of the repository.

        Returns:
            Path to the hooks directory or None if outside a Git repository.

        Notes/Architectural Intent:
            Resolves standard or common hooks paths for worktrees.
        """
        git_dir = self.resolve_git_dir(repo_root)
        if not git_dir:
            return None

        # Check for common dir in worktrees
        commondir_file = git_dir / "commondir"
        if commondir_file.is_file():
            try:
                common_rel = commondir_file.read_text(encoding="utf-8").strip()
                common_dir = (git_dir / common_rel).resolve()
                return common_dir / "hooks"
            except OSError:
                return git_dir / "hooks"

        return git_dir / "hooks"

    def install_hooks(
        self,
        repo_root: Path,
        mode: HookInstallMode = HookInstallMode.AUTO,
    ) -> HooksInstallReport:
        """Install Git lifecycle hooks into the target repository.

        Args:
            repo_root: Path to the target repository root.
            mode: Installation strategy (auto, pre-commit, or native).

        Returns:
            HooksInstallReport detailing installed stages and execution mode.

        Raises:
            None.

        Notes/Architectural Intent:
            Dispatches to pre-commit or native file generation based on strategy.
        """
        hooks_dir = self.resolve_hooks_dir(repo_root)
        if not hooks_dir:
            return HooksInstallReport(
                mode=mode,
                installed_stages=(),
                details=(f"Repository '{repo_root}' is not a valid Git repository.",),
                success=False,
            )

        resolved_mode = mode
        if resolved_mode == HookInstallMode.AUTO:
            precommit_cfg = repo_root / ".pre-commit-config.yaml"
            has_precommit = shutil.which("pre-commit") is not None or shutil.which("uv") is not None
            resolved_mode = (
                HookInstallMode.PRE_COMMIT
                if precommit_cfg.is_file() and has_precommit
                else HookInstallMode.NATIVE
            )

        if resolved_mode == HookInstallMode.PRE_COMMIT:
            return self._install_precommit_hooks(repo_root, resolved_mode)
        return self._install_native_hooks(hooks_dir, resolved_mode)

    def _install_precommit_hooks(
        self,
        repo_root: Path,
        mode: HookInstallMode,
    ) -> HooksInstallReport:
        """Install all supported stages using pre-commit CLI."""
        stages: list[HookStage] = [
            HookStage.PRE_COMMIT,
            HookStage.PRE_PUSH,
            HookStage.COMMIT_MSG,
            HookStage.POST_MERGE,
            HookStage.POST_CHECKOUT,
        ]
        cmd: list[str] = ["pre-commit", "install"]
        if shutil.which("uv") is not None:
            cmd = ["uv", "run", "pre-commit", "install"]

        for stage in stages:
            cmd.extend(["--hook-type", stage.value])

        try:
            res = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                details = tuple(line for line in res.stdout.splitlines() if line.strip())
                return HooksInstallReport(
                    mode=mode,
                    installed_stages=tuple(stages),
                    details=details or ("All pre-commit hook types installed successfully.",),
                    success=True,
                )
            details = tuple(line for line in res.stderr.splitlines() if line.strip())
            return HooksInstallReport(
                mode=mode,
                installed_stages=(),
                details=details or ("pre-commit install returned non-zero exit code.",),
                success=False,
            )
        except Exception as exc:
            return HooksInstallReport(
                mode=mode,
                installed_stages=(),
                details=(f"Failed to execute pre-commit install: {exc}",),
                success=False,
            )

    def _install_native_hooks(
        self,
        hooks_dir: Path,
        mode: HookInstallMode,
    ) -> HooksInstallReport:
        """Install zero-dependency native bash hook scripts into .git/hooks/."""
        hooks_dir.mkdir(parents=True, exist_ok=True)
        installed: list[HookStage] = []
        details: list[str] = []

        for stage, template in NATIVE_HOOK_TEMPLATES.items():
            script_path = hooks_dir / stage.value
            try:
                script_path.write_text(template, encoding="utf-8")
                # chmod 0755 (rwxr-xr-x)
                os.chmod(script_path, script_path.stat().st_mode | 0o755)
                installed.append(stage)
                details.append(f"Installed native hook: {script_path.name}")
            except OSError as exc:
                details.append(f"Failed to write {script_path.name}: {exc}")

        return HooksInstallReport(
            mode=mode,
            installed_stages=tuple(installed),
            details=tuple(details),
            success=len(installed) == len(NATIVE_HOOK_TEMPLATES),
        )

    def uninstall_hooks(self, repo_root: Path) -> HooksUninstallReport:
        """Uninstall Git lifecycle hooks from the target repository.

        Args:
            repo_root: Path to the target repository root.

        Returns:
            HooksUninstallReport detailing removed stages and outcomes.

        Raises:
            None.

        Notes/Architectural Intent:
            Safely removes managed native scripts and triggers pre-commit uninstall.
        """
        hooks_dir = self.resolve_hooks_dir(repo_root)
        if not hooks_dir:
            return HooksUninstallReport(
                removed_stages=(),
                details=(f"Repository '{repo_root}' is not a valid Git repository.",),
                success=False,
            )

        removed: list[HookStage] = []
        details: list[str] = []

        # 1. Attempt pre-commit uninstall if available
        stages: list[HookStage] = [
            HookStage.PRE_COMMIT,
            HookStage.PRE_PUSH,
            HookStage.COMMIT_MSG,
            HookStage.POST_MERGE,
            HookStage.POST_CHECKOUT,
        ]
        cmd: list[str] = ["pre-commit", "uninstall"]
        if shutil.which("uv") is not None:
            cmd = ["uv", "run", "pre-commit", "uninstall"]

        for stage in stages:
            cmd.extend(["--hook-type", stage.value])

        try:
            res = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                details.append("Cleaned pre-commit hook wrappers.")
        except Exception as exc:
            details.append(f"Pre-commit uninstall invocation failed: {exc}")

        # 2. Clean any native scripts containing the hexaqual header
        for stage in HookStage:
            script_path = hooks_dir / stage.value
            if script_path.is_file():
                try:
                    content = script_path.read_text(encoding="utf-8")
                    if HEXAQUAL_HOOK_HEADER in content:
                        script_path.unlink()
                        removed.append(stage)
                        details.append(f"Removed native hook: {stage.value}")
                except OSError as exc:
                    details.append(f"Failed to remove {stage.value}: {exc}")

        return HooksUninstallReport(
            removed_stages=tuple(removed),
            details=tuple(details) if details else ("No managed hooks found to remove.",),
            success=True,
        )

    def check_hooks(self, repo_root: Path) -> tuple[HookStatusInfo, ...]:
        """Inspect the current installation status of all supported Git hooks.

        Args:
            repo_root: Path to the target repository root.

        Returns:
            Tuple of HookStatusInfo records for each lifecycle stage.

        Raises:
            None.

        Notes/Architectural Intent:
            Inspects the hooks directory and categorizes hook managers.
        """
        hooks_dir = self.resolve_hooks_dir(repo_root)
        results: list[HookStatusInfo] = []

        for stage in HookStage:
            script_path = (
                (hooks_dir / stage.value)
                if hooks_dir
                else (repo_root / ".git" / "hooks" / stage.value)
            )
            if not script_path.is_file():
                results.append(
                    HookStatusInfo(
                        stage=stage,
                        is_installed=False,
                        manager=HookManager.NONE,
                        script_path=script_path,
                    )
                )
                continue

            try:
                content = script_path.read_text(encoding="utf-8")
                if "pre-commit" in content:
                    manager = HookManager.PRE_COMMIT
                elif HEXAQUAL_HOOK_HEADER in content:
                    manager = HookManager.NATIVE
                else:
                    manager = HookManager.UNKNOWN
            except OSError:
                manager = HookManager.UNKNOWN

            results.append(
                HookStatusInfo(
                    stage=stage,
                    is_installed=True,
                    manager=manager,
                    script_path=script_path,
                )
            )

        return tuple(results)

    def validate_commit_msg(
        self,
        msg: str,
        require_dco: bool = True,
        require_conventional: bool = True,
    ) -> CommitMsgReport:
        """Validate a commit message against Conventional Commits and DCO sign-off rules.

        Args:
            msg: Raw commit message text to analyze.
            require_dco: Whether to enforce Developer Certificate of Origin (Signed-off-by:).
            require_conventional: Whether to enforce Conventional Commits title format.

        Returns:
            CommitMsgReport detailing validity and any diagnostic failure messages.

        Raises:
            None.

        Notes/Architectural Intent:
            Permits merge commits and automated rebase messages while enforcing standards on feature commits.
        """
        lines = [line.strip() for line in msg.splitlines() if not line.strip().startswith("#")]
        non_empty = [line for line in lines if line]

        if not non_empty:
            return CommitMsgReport(
                is_valid=False,
                title="",
                errors=("Commit message is empty.",),
                dco_found=False,
                conventional_match=False,
            )

        title = non_empty[0]
        errors: list[str] = []

        # Check for automated merge / revert commit
        is_merge_or_revert = title.startswith(("Merge ", 'Revert "', "Revert '"))

        # Conventional Commits format verification
        conventional_match = True
        if require_conventional and not is_merge_or_revert:
            match = CONVENTIONAL_COMMIT_PATTERN.match(title)
            if not match:
                conventional_match = False
                errors.append(
                    f"Title '{title}' does not conform to Conventional Commits format "
                    f"'<type>(<scope>): <subject>'. Valid types: feat, fix, docs, style, "
                    f"refactor, perf, test, build, ci, chore, revert."
                )

        # DCO Signed-off-by verification
        dco_found = bool(DCO_PATTERN.search(msg))
        if require_dco and not is_merge_or_revert and not dco_found:
            errors.append(
                "Missing Developer Certificate of Origin (DCO) sign-off trailer. "
                "Please run 'git commit -s' or amend with 'git commit -s --amend'."
            )

        return CommitMsgReport(
            is_valid=len(errors) == 0,
            title=title,
            errors=tuple(errors),
            dco_found=dco_found,
            conventional_match=conventional_match,
        )
