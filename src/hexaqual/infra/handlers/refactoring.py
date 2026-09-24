"""CQRS command handlers for AST refactoring and publication tooling.

Notes/Architectural Intent:
    Orchestrates function and method alphabetization via LibCST and article
    publication workflows, returning immutable domain reports.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.adapters.code_analysis.rope import (
    FunctionAndMethodAlphabetizerCST,
    sort_python_file,
)
from hexaqual.domain.refactoring import (
    AlphabetizeCodeCommand,
    AlphabetizeCodeReport,
    MediumPublishReport,
    PublishMediumArticlesCommand,
)
from hexaqual.infra.workspace import get_repo_root


class AlphabetizeCodeHandler:
    """Handler executing AST function and method alphabetization."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize AlphabetizeCodeHandler.

        Args:
            root: Root path of monorepo workspace.
        """
        self._root = root or get_repo_root()

    def _resolve_target_files(self, targets: tuple[Path, ...]) -> list[Path]:
        target_paths = [Path(p) for p in targets] if targets else [self._root / "packages"]
        files: list[Path] = []
        for tp in target_paths:
            if tp.is_file() and tp.suffix == ".py":
                files.append(tp.resolve())
            elif tp.is_dir():
                files.extend(p.resolve() for p in tp.glob("**/*.py"))
        return sorted(set(files))

    def _to_rel_path(self, file_path: Path) -> str:
        if file_path.is_relative_to(self._root):
            return str(file_path.relative_to(self._root))
        return str(file_path)

    def _process_file(self, file_path: Path, dry_run: bool) -> tuple[str, bool]:
        rel = self._to_rel_path(file_path)
        try:
            if dry_run:
                content = file_path.read_text(encoding="utf-8")
                changed = sort_python_file(file_path)
                if changed:
                    file_path.write_text(content, encoding="utf-8")
                return rel, changed
            changed = sort_python_file(file_path)
            return rel, changed
        except Exception:
            return rel, False

    def handle(self, command: AlphabetizeCodeCommand) -> AlphabetizeCodeReport:
        """Execute alphabetization on targeted files.

        Args:
            command: AlphabetizeCodeCommand specifying targets and dry_run.

        Returns:
            AlphabetizeCodeReport with reordered and unchanged files.

        Notes/Architectural Intent:
            Parses target paths and applies LibCST FunctionAndMethodAlphabetizerCST
            transformations.
        """
        files = self._resolve_target_files(command.targets)
        reordered: list[str] = []
        unchanged: list[str] = []

        for file_path in files:
            rel, changed = self._process_file(file_path, command.dry_run)
            if changed:
                reordered.append(rel)
            else:
                unchanged.append(rel)

        return AlphabetizeCodeReport(
            reordered_files=tuple(reordered),
            unchanged_files=tuple(unchanged),
            is_successful=True,
        )


class PublishMediumArticlesHandler:
    """Handler executing article publishing workflow."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize PublishMediumArticlesHandler."""
        self._root = root or get_repo_root()

    def handle(self, command: PublishMediumArticlesCommand) -> MediumPublishReport:
        """Execute article publication, status inspection, or link syncing.

        Args:
            command: PublishMediumArticlesCommand with publication options.

        Returns:
            MediumPublishReport detailing publication counts, status, and links.

        Notes/Architectural Intent:
            Coordinates draft uploads, publication on DEV.to, cross-link
            resolution, and documentation synchronization across the monorepo.
        """
        import os

        from hexaqual.adapters.publishers.devto import (
            get_article_status_table,
            publish_or_upload_single,
            record_medium_url,
            sync_all_links,
            upload_all_drafts,
        )

        medium_dir = self._resolve_medium_dir(command.manifest_path)
        if not medium_dir.is_dir():
            return MediumPublishReport(
                published_count=0,
                total_count=0,
                is_successful=False,
                details=(("error", f"Directory does not exist: {medium_dir}"),),
            )

        if command.status:
            table = get_article_status_table(medium_dir)
            return MediumPublishReport(
                published_count=len(table),
                total_count=len(table),
                is_successful=True,
                status_table=tuple(table),
            )

        if command.medium_url:
            if not command.slug:
                return MediumPublishReport(
                    is_successful=False,
                    details=(("error", "Provide a slug with --medium-url."),),
                )
            slug, msg = record_medium_url(
                command.slug,
                command.medium_url,
                self._root,
                dry_run=command.dry_run,
                medium_dir=medium_dir,
            )
            return MediumPublishReport(
                published_count=1,
                total_count=1,
                is_successful=True,
                details=((slug, msg),),
            )

        api_key = command.api_key or os.environ.get("DEVTO_API_KEY", "")
        if not api_key and not command.dry_run:
            return MediumPublishReport(
                is_successful=False,
                details=(
                    (
                        "error",
                        "No DEV.to API key found. Set DEVTO_API_KEY or pass --api-key.",
                    ),
                ),
            )

        if command.sync_links:
            results = sync_all_links(
                medium_dir,
                api_key,
                self._root,
                dry_run=command.dry_run,
            )
            return MediumPublishReport(
                published_count=len(results),
                total_count=len(results),
                is_successful=True,
                details=tuple(results),
            )

        if command.all_drafts:
            results = upload_all_drafts(
                medium_dir,
                api_key,
                dry_run=command.dry_run,
            )
            return MediumPublishReport(
                published_count=len(results),
                total_count=len(results),
                is_successful=True,
                details=tuple(results),
            )

        target = command.slug
        if not target and command.manifest_path and command.manifest_path.is_file():
            target = str(command.manifest_path)

        if not target:
            return MediumPublishReport(
                is_successful=False,
                details=(
                    (
                        "error",
                        "Provide an article slug or pass --status / --all-drafts / --sync-links.",
                    ),
                ),
            )

        try:
            slug, msg = publish_or_upload_single(
                target,
                publish=command.publish,
                api_key=api_key,
                repo_root=self._root,
                dry_run=command.dry_run,
                medium_dir=medium_dir,
            )
            return MediumPublishReport(
                published_count=1,
                total_count=1,
                is_successful=True,
                details=((slug, msg),),
            )
        except Exception as exc:
            return MediumPublishReport(
                is_successful=False,
                details=((target, f"Failed: {exc}"),),
            )

    def _resolve_medium_dir(self, manifest_path: Path | None) -> Path:
        """Resolve the medium drafts directory path."""
        if manifest_path:
            return manifest_path if manifest_path.is_dir() else manifest_path.parent
        return self._root / "docs" / "medium"


__all__ = [
    "AlphabetizeCodeHandler",
    "FunctionAndMethodAlphabetizerCST",
    "PublishMediumArticlesHandler",
    "sort_python_file",
]
