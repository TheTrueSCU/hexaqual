"""Unit tests for FileSystemAgentAssetAdapter.

Notes/Architectural Intent:
    Verifies asset loading, sync operations, dry-run simulation, drift detection,
    and unmanaged local asset preservation using hermetic tmp_path fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hexaqual.adapters.agents.fs import FileSystemAgentAssetAdapter


def test_load_bundled_assets() -> None:
    """Verify adapter successfully loads bundled rules, workflows, and skills.

    Notes/Architectural Intent:
        Guarantees packaged assets are discoverable and non-empty.
    """
    adapter = FileSystemAgentAssetAdapter()
    assets = adapter.load_bundled_assets()

    asset_count = len(assets)
    assert asset_count >= 18

    kinds = {a.kind.value for a in assets}
    assert "rules" in kinds
    assert "workflows" in kinds
    assert "skills" in kinds

    # Verify every asset has non-empty content
    for a in assets:
        content_len = len(a.content)
        assert content_len > 0


def test_sync_assets_creates_and_preserves(tmp_path: Path) -> None:
    """Verify sync creates managed assets and preserves unmanaged local assets.

    Notes/Architectural Intent:
        Tests initial synchronization into a clean directory and asserts local files
        are never deleted or modified.
    """
    adapter = FileSystemAgentAssetAdapter()

    # Pre-create unmanaged local rules
    rules_dir = tmp_path / ".agents" / "rules"
    rules_dir.mkdir(parents=True)
    local_rule = rules_dir / "hexaqueue-custom.md"
    local_rule.write_text("# Local Custom Rule\n", encoding="utf-8")

    # Run sync
    report = adapter.sync_assets(target_dir=tmp_path, dry_run=False)

    created = report.created_count
    updated = report.updated_count
    unchanged = report.unchanged_count
    preserved = report.preserved_unmanaged_count

    assert created >= 18
    assert updated == 0
    assert unchanged == 0
    assert preserved == 1

    # Check that unmanaged file was preserved
    local_content = local_rule.read_text(encoding="utf-8")
    assert local_content == "# Local Custom Rule\n"

    # Second sync should result in all unchanged
    second_report = adapter.sync_assets(target_dir=tmp_path, dry_run=False)
    assert second_report.created_count == 0
    assert second_report.updated_count == 0
    assert second_report.unchanged_count >= 18
    assert second_report.preserved_unmanaged_count == 1


def test_sync_assets_dry_run(tmp_path: Path) -> None:
    """Verify dry-run simulates creation without writing files to disk.

    Notes/Architectural Intent:
        Ensures dry_run parameter does not mutate target filesystem.
    """
    adapter = FileSystemAgentAssetAdapter()
    report = adapter.sync_assets(target_dir=tmp_path, dry_run=True)

    created = report.created_count
    assert created >= 18

    # Target directory should not have files written
    target_agents = tmp_path / ".agents"
    has_dir = target_agents.exists()
    assert has_dir is False


def test_check_drift_clean_and_dirty(tmp_path: Path) -> None:
    """Verify drift detection reports clean when synced and dirty when modified.

    Notes/Architectural Intent:
        Validates check_drift return contracts for pre-commit enforcement.
    """
    adapter = FileSystemAgentAssetAdapter()

    # Before sync, files are missing
    initial_check = adapter.check_drift(target_dir=tmp_path)
    is_initial_clean = initial_check.is_clean
    missing_count = len(initial_check.missing_files)
    assert is_initial_clean is False
    assert missing_count >= 18

    # After sync, directory is clean
    adapter.sync_assets(target_dir=tmp_path, dry_run=False)
    clean_check = adapter.check_drift(target_dir=tmp_path)
    is_clean = clean_check.is_clean
    assert is_clean is True

    # Mutate one managed file
    rule_file = tmp_path / ".agents" / "rules" / "hexaqual-boundaries.md"
    rule_file.write_text("# Mutated content\n", encoding="utf-8")

    dirty_check = adapter.check_drift(target_dir=tmp_path)
    is_dirty_clean = dirty_check.is_clean
    drifted_files = dirty_check.drifted_files

    assert is_dirty_clean is False
    assert "rules/hexaqual-boundaries.md" in drifted_files


def test_invalid_asset_root_override_raises() -> None:
    """Verify RuntimeError is raised when invalid override path is provided.

    Notes/Architectural Intent:
        Asserts explicit error messaging when configuration path is invalid.
    """
    adapter = FileSystemAgentAssetAdapter(asset_root_override=Path("/non/existent/path"))
    with pytest.raises(RuntimeError):
        adapter.load_bundled_assets()


def test_sync_assets_generates_agents_md(tmp_path: Path) -> None:
    """Verify sync_assets generates root AGENTS.md index file.

    Notes/Architectural Intent:
        Confirms root AGENTS.md pointer is created and contains active rules.
    """
    adapter = FileSystemAgentAssetAdapter()
    adapter.sync_assets(target_dir=tmp_path, dry_run=False)

    agents_md = tmp_path / "AGENTS.md"
    has_agents_md = agents_md.is_file()
    assert has_agents_md is True

    content = agents_md.read_text(encoding="utf-8")
    assert "# AI Agent Workspace Guardrails" in content
    assert "hexaqual-boundaries.md" in content
    assert "hexaqual-pre-commit.md" in content


def test_sync_assets_and_check_drift_gitignore(tmp_path: Path) -> None:
    """Verify sync_assets appends managed patterns to .gitignore and check_drift reports missing patterns.

    Notes/Architectural Intent:
        Guarantees that repositories are audited for proper .gitignore exclusion of upstream assets.
    """
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("# existing gitignore\n", encoding="utf-8")

    adapter = FileSystemAgentAssetAdapter()
    adapter.sync_assets(target_dir=tmp_path, dry_run=False)

    # After sync, .gitignore should have all managed patterns
    content = gitignore.read_text(encoding="utf-8")
    assert ".agents/rules/hexaqual-*" in content
    assert ".agents/workflows/hexaqual-*" in content
    assert ".agents/skills/hexaqual_*" in content

    # check_drift should report clean
    report = adapter.check_drift(target_dir=tmp_path)
    is_clean = report.is_clean
    assert is_clean is True

    # If .gitignore has managed patterns removed, check_drift should detect missing exclusions
    gitignore.write_text("# stripped\n", encoding="utf-8")
    dirty_report = adapter.check_drift(target_dir=tmp_path)
    is_dirty_clean = dirty_report.is_clean
    assert is_dirty_clean is False
    assert any(".gitignore:" in f for f in dirty_report.missing_files)
