"""Filesystem and package resource adapter for agent assets synchronization.

Notes/Architectural Intent:
    Concrete implementation of AgentAssetPort leveraging importlib.resources
    to extract packaged agent assets and synchronize them to target repository
    .agents directories while strictly preserving unmanaged local assets.
"""

from __future__ import annotations

import importlib.resources as pkg_resources
from pathlib import Path

from hexaqual.domain.agents import (
    AgentAsset,
    AgentAssetKind,
    AgentCheckReport,
    AgentSyncReport,
)
from hexaqual.ports.agents import AgentAssetPort

__all__ = [
    "FileSystemAgentAssetAdapter",
    "MANAGED_GITIGNORE_PATTERNS",
]

MANAGED_GITIGNORE_PATTERNS: tuple[str, ...] = (
    ".agents/rules/hexaqual-*",
    ".agents/workflows/hexaqual-*",
    ".agents/skills/hexaqual_*",
)


class FileSystemAgentAssetAdapter(AgentAssetPort):
    """Adapter reading bundled agent assets and synchronizing to repositories."""

    def __init__(self, asset_root_override: Path | None = None) -> None:
        """Initialize adapter with optional asset root override.

        Args:
            asset_root_override: Optional path overriding standard importlib.resources path.

        Notes/Architectural Intent:
            Enables hermetic testing and local asset development without wheel re-installation.
        """
        self._asset_root_override = asset_root_override

    def _resolve_asset_root(self) -> Path:
        """Resolve path to the bundled assets root directory.

        Returns:
            Path pointing to the agent assets directory.

        Raises:
            RuntimeError: If assets directory cannot be resolved or does not exist.

        Notes/Architectural Intent:
            Prefers explicit override, falls back to importlib.resources traversable.
        """
        if self._asset_root_override is not None:
            if self._asset_root_override.is_dir():
                return self._asset_root_override
            msg = f"Asset root override path does not exist: {self._asset_root_override}"
            raise RuntimeError(msg)

        try:
            traversable = pkg_resources.files("hexaqual.assets.agents")
            # importlib.resources.files returns Traversable, convert to Path if local
            res_path = Path(str(traversable))
            if res_path.is_dir():
                return res_path
        except (ModuleNotFoundError, TypeError, ValueError):
            pass

        # Fallback to local source tree if running in development mode
        dev_path = Path(__file__).resolve().parent.parent.parent / "assets" / "agents"
        if dev_path.is_dir():
            return dev_path

        msg = "Unable to locate bundled hexaqual.assets.agents directory."
        raise RuntimeError(msg)

    def load_bundled_assets(self) -> tuple[AgentAsset, ...]:
        """Load all bundled rules, workflows, and skills from package resources.

        Returns:
            Tuple of AgentAsset models containing name, kind, path, and text.

        Raises:
            RuntimeError: If bundled assets cannot be discovered or loaded.

        Notes/Architectural Intent:
            Traverses rules, workflows, and skills subdirectories of the assets root.
        """
        root = self._resolve_asset_root()
        assets: list[AgentAsset] = []

        for kind in AgentAssetKind:
            kind_dir = root / kind.value
            if not kind_dir.is_dir():
                continue
            for item in sorted(kind_dir.iterdir()):
                if item.is_file() and not item.name.startswith("."):
                    content = item.read_text(encoding="utf-8")
                    rel_path = f"{kind.value}/{item.name}"
                    assets.append(
                        AgentAsset(
                            name=item.name,
                            kind=kind,
                            relative_path=rel_path,
                            content=content,
                        )
                    )

        return tuple(assets)

    def _resolve_agents_dir(self, target_dir: Path) -> Path:
        """Resolve the target .agents directory path.

        Args:
            target_dir: Target directory path.

        Returns:
            Path to the .agents directory.

        Notes/Architectural Intent:
            Handles both repository root and explicit .agents directory paths.
        """
        if target_dir.name == ".agents":
            return target_dir
        return target_dir / ".agents"

    def _ensure_kind_dirs(self, agents_dir: Path) -> None:
        """Create category subdirectories under .agents directory.

        Args:
            agents_dir: Path to the target .agents directory.
        """
        for kind in AgentAssetKind:
            (agents_dir / kind.value).mkdir(parents=True, exist_ok=True)

    def _sync_single_asset(
        self, agents_dir: Path, asset: AgentAsset, dry_run: bool
    ) -> tuple[str, str | None]:
        """Synchronize an individual agent asset to disk.

        Args:
            agents_dir: Target .agents directory path.
            asset: AgentAsset to synchronize.
            dry_run: Whether to simulate changes.

        Returns:
            Tuple of (status_tag, detail_message_or_none).
        """
        dest_file = agents_dir / asset.kind.value / asset.name
        if not dest_file.exists():
            if not dry_run:
                dest_file.write_text(asset.content, encoding="utf-8")
            return "created", f"Created {asset.relative_path}"

        existing_content = dest_file.read_text(encoding="utf-8")
        if existing_content != asset.content:
            if not dry_run:
                dest_file.write_text(asset.content, encoding="utf-8")
            return "updated", f"Updated {asset.relative_path}"

        return "unchanged", None

    def _count_preserved_unmanaged(self, agents_dir: Path) -> int:
        """Count existing local assets that are not managed by hexaqual.

        Args:
            agents_dir: Path to .agents directory.

        Returns:
            Count of preserved local files.
        """
        if not agents_dir.is_dir():
            return 0
        preserved = 0
        for kind in AgentAssetKind:
            kind_dir = agents_dir / kind.value
            if not kind_dir.is_dir():
                continue
            for item in kind_dir.iterdir():
                if item.is_file() and not (
                    item.name.startswith("hexaqual-") or item.name.startswith("hexaqual_")
                ):
                    preserved += 1
        return preserved

    def _generate_root_agents_markdown(self, agents_dir: Path) -> str:
        """Generate content for the root AGENTS.md index file.

        Args:
            agents_dir: Path to the target .agents directory.

        Returns:
            Markdown string indexing all active rules, workflows, and skills.

        Notes/Architectural Intent:
            Ensures tools and IDE agents that inspect a single root file
            have immediate visibility into all active modular guardrails.
        """
        lines = [
            "<!-- Generated by hexaqual agents sync - DO NOT EDIT MANUALLY -->",
            "# AI Agent Workspace Guardrails",
            "",
            "> This repository uses [**Hexaqual**](https://github.com/TheTrueSCU/hexaqual) unified AI guardrails and quality governance.",
            "",
        ]
        for kind in AgentAssetKind:
            kind_dir = agents_dir / kind.value
            if not kind_dir.is_dir():
                continue
            items = sorted(kind_dir.iterdir(), key=lambda p: p.name.casefold())
            active_items = [p for p in items if p.is_file()]
            if not active_items:
                continue
            lines.append(f"## Active {kind.value.capitalize()} (`.agents/{kind.value}/`)")
            lines.append("")
            for item in active_items:
                lines.append(f"- [{item.name}](.agents/{kind.value}/{item.name})")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def _ensure_gitignore(self, repo_root: Path) -> None:
        """Ensure managed agent asset patterns are recorded in .gitignore.

        Args:
            repo_root: Root directory of the repository.

        Notes/Architectural Intent:
            Prevents downstream repositories from committing duplicate copies
            of universal upstream assets.
        """
        gitignore = repo_root / ".gitignore"
        if not gitignore.is_file():
            return
        existing = gitignore.read_text(encoding="utf-8")
        lines = set(existing.splitlines())
        missing_patterns = [p for p in MANAGED_GITIGNORE_PATTERNS if p not in lines]
        if missing_patterns:
            with gitignore.open("a", encoding="utf-8") as f:
                if not existing.endswith("\n"):
                    f.write("\n")
                f.write(
                    "\n# Hexaqual managed agent assets (materialized via hexaqual agents sync)\n"
                )
                for pat in missing_patterns:
                    f.write(f"{pat}\n")

    def _sync_root_agents_index(self, target_dir: Path, agents_dir: Path, dry_run: bool) -> None:
        """Synchronize the root AGENTS.md index and ensure gitignore patterns.

        Args:
            target_dir: User-provided target directory path.
            agents_dir: Resolved .agents directory path.
            dry_run: Whether to simulate changes.

        Notes/Architectural Intent:
            Decoupled helper invoked at the conclusion of sync_assets.
        """
        repo_root = target_dir.parent if target_dir.name == ".agents" else target_dir
        if not dry_run:
            content = self._generate_root_agents_markdown(agents_dir)
            (repo_root / "AGENTS.md").write_text(content, encoding="utf-8")
            self._ensure_gitignore(repo_root)

    def sync_assets(self, target_dir: Path, dry_run: bool = False) -> AgentSyncReport:
        """Synchronize managed agent assets to the target repository directory.

        Args:
            target_dir: Path to the target repository root or .agents directory.
            dry_run: Whether to simulate changes without writing to disk.

        Returns:
            AgentSyncReport summarizing created, updated, and preserved files.

        Raises:
            OSError: If file read or write operations encounter I/O errors.

        Notes/Architectural Intent:
            Overwrites managed files (matching hexaqual-* or hexaqual_*) while
            strictly preserving repo-specific local assets.
        """
        agents_dir = self._resolve_agents_dir(target_dir)
        bundled = self.load_bundled_assets()

        created = 0
        updated = 0
        unchanged = 0
        details: list[str] = []

        if not dry_run:
            self._ensure_kind_dirs(agents_dir)

        for asset in bundled:
            status, detail = self._sync_single_asset(agents_dir, asset, dry_run)
            if status == "created":
                created += 1
                if detail:
                    details.append(detail)
            elif status == "updated":
                updated += 1
                if detail:
                    details.append(detail)
            else:
                unchanged += 1

        preserved = self._count_preserved_unmanaged(agents_dir)
        self._sync_root_agents_index(target_dir, agents_dir, dry_run)

        return AgentSyncReport(
            created_count=created,
            updated_count=updated,
            unchanged_count=unchanged,
            preserved_unmanaged_count=preserved,
            details=tuple(details),
        )

    def check_drift(self, target_dir: Path) -> AgentCheckReport:
        """Check for drift between target directory and bundled assets.

        Args:
            target_dir: Path to the target repository root or .agents directory.

        Returns:
            AgentCheckReport indicating whether assets match and listing differences.

        Raises:
            OSError: If files cannot be read for comparison.

        Notes/Architectural Intent:
            Powers pre-commit checks and CI validation to detect out-of-sync guardrails.
        """
        agents_dir = self._resolve_agents_dir(target_dir)
        bundled = self.load_bundled_assets()

        drifted: list[str] = []
        missing: list[str] = []
        details: list[str] = []

        for asset in bundled:
            dest_file = agents_dir / asset.kind.value / asset.name
            if not dest_file.exists():
                missing.append(asset.relative_path)
                details.append(f"Missing managed asset: {asset.relative_path}")
            else:
                existing_content = dest_file.read_text(encoding="utf-8")
                if existing_content != asset.content:
                    drifted.append(asset.relative_path)
                    details.append(f"Drift detected in managed asset: {asset.relative_path}")

        repo_root = target_dir.parent if target_dir.name == ".agents" else target_dir
        gitignore = repo_root / ".gitignore"
        if gitignore.is_file():
            existing_gi = set(gitignore.read_text(encoding="utf-8").splitlines())
            missing_gi = [p for p in MANAGED_GITIGNORE_PATTERNS if p not in existing_gi]
            for p in missing_gi:
                missing.append(f".gitignore:{p}")
                details.append(f"Missing .gitignore exclusion: {p}")

        is_clean = len(drifted) == 0 and len(missing) == 0
        return AgentCheckReport(
            is_clean=is_clean,
            drifted_files=tuple(drifted),
            missing_files=tuple(missing),
            details=tuple(details),
        )
