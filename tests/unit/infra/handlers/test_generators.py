"""Unit tests for generator CQRS command handlers."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from hexaqual.domain.generators import (
    GenerateArchonTestsCommand,
    GeneratePydepsCommand,
    GenerateUsageDocsCommand,
)
from hexaqual.infra.handlers.generators import (
    GenerateArchonTestsHandler,
    GeneratePydepsHandler,
    GenerateUsageDocsHandler,
)


@pytest.fixture(autouse=True)
def mock_dot_available() -> Generator[None]:
    """Provide a mock dot executable path so unit tests don't depend on system graphviz."""
    with patch("shutil.which", return_value="/usr/bin/dot"):
        yield


def test_generate_pydeps_handler(tmp_path: Path) -> None:
    """Verify GeneratePydepsHandler executes pydeps generation and returns report."""
    handler = GeneratePydepsHandler(root=tmp_path, parallel=False)
    with (
        patch(
            "hexaqual.infra.handlers.generators.generate_overview_diagram",
            return_value="docs/overview.svg",
        ),
        patch(
            "hexaqual.infra.handlers.generators.generate_package_diagram",
            return_value="docs/core.svg",
        ),
        patch(
            "hexaqual.infra.handlers.generators.get_package_directories",
            return_value=[tmp_path / "packages" / "core"],
        ),
    ):
        report = handler.handle(GeneratePydepsCommand())
        assert report.is_successful is True
        assert len(report.results) >= 1


def test_generate_pydeps_handler_check_mode(tmp_path: Path) -> None:
    """Verify GeneratePydepsHandler executes checks in check mode."""
    handler = GeneratePydepsHandler(root=tmp_path, parallel=False)
    with (
        patch(
            "hexaqual.infra.handlers.generators.check_overview_diagram",
            return_value=(True, "docs/overview.svg"),
        ),
        patch(
            "hexaqual.infra.handlers.generators.check_package_diagram",
            return_value=(True, "docs/core.svg"),
        ),
        patch(
            "hexaqual.infra.handlers.generators.get_package_directories",
            return_value=[tmp_path / "packages" / "core"],
        ),
    ):
        report = handler.handle(GeneratePydepsCommand(check_only=True))
        assert report.is_successful is True
        assert report.is_check is True
        assert len(report.results) == 2
        assert report.results[0].success is True
        assert report.results[0].is_stale is False


def test_generate_pydeps_handler_missing_dot_check_mode(tmp_path: Path) -> None:
    """Verify GeneratePydepsHandler gracefully skips when dot is missing in check mode."""
    handler = GeneratePydepsHandler(root=tmp_path, parallel=False)
    with patch("shutil.which", return_value=None):
        report = handler.handle(GeneratePydepsCommand(check_only=True))
        assert report.is_successful is True
        assert report.is_check is True
        assert len(report.results) == 1
        assert report.results[0].success is True
        assert "Graphviz 'dot' not installed" in report.results[0].details


def test_generate_pydeps_handler_missing_dot_generate_mode(tmp_path: Path) -> None:
    """Verify GeneratePydepsHandler fails gracefully when dot is missing in generate mode."""
    handler = GeneratePydepsHandler(root=tmp_path, parallel=False)
    with patch("shutil.which", return_value=None):
        report = handler.handle(GeneratePydepsCommand(check_only=False))
        assert report.is_successful is False
        assert report.is_check is False
        assert len(report.results) == 1
        assert report.results[0].success is False
        assert "Graphviz 'dot' not installed" in report.results[0].details


def test_generate_usage_docs_handler_check_and_fix(tmp_path: Path) -> None:
    """Verify GenerateUsageDocsHandler checks and fixes USAGE.md."""
    usage_file = tmp_path / "USAGE.md"
    usage_file.write_text("Old content\n", encoding="utf-8")

    handler = GenerateUsageDocsHandler(root=tmp_path)
    with (
        patch(
            "hexaqual.infra.handlers.generators.discover_usage_targets",
            return_value={"test": usage_file},
        ),
        patch(
            "hexaqual.infra.handlers.generators.build_tools_usage_markdown",
            return_value="New content\n",
        ),
        patch(
            "hexaqual.infra.handlers.generators.resolve_impacted_usage_targets",
            return_value=["test"],
        ),
    ):
        # Check only -> should report stale
        rep_check = handler.handle(GenerateUsageDocsCommand(check_only=True, fix=False))
        assert rep_check.is_valid is False
        assert len(rep_check.stale_files) == 1

        # Fix mode -> should update file
        rep_fix = handler.handle(GenerateUsageDocsCommand(check_only=False, fix=True))
        assert rep_fix.is_valid is True
        assert usage_file.read_text(encoding="utf-8") == "New content\n"


def test_generate_archon_tests_handler(tmp_path: Path) -> None:
    """Verify GenerateArchonTestsHandler scaffolds architecture test files."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    pkg_dir.mkdir(parents=True)
    handler = GenerateArchonTestsHandler(root=tmp_path)

    with (
        patch(
            "hexaqual.infra.handlers.generators.get_package_directories",
            return_value=[pkg_dir],
        ),
        patch(
            "hexaqual.infra.handlers.generators.get_present_layers",
            return_value=["domain", "ports"],
        ),
    ):
        report = handler.handle(GenerateArchonTestsCommand())
        assert report.is_successful is True
        assert len(report.generated_files) == 1
        test_file = pkg_dir / "tests" / "architecture" / "test_hexagonal_boundaries.py"
        assert test_file.is_file()

        # Running again without force should skip
        rep_skip = handler.handle(GenerateArchonTestsCommand(force=False))
        assert len(rep_skip.skipped_files) == 1


def test_discover_usage_targets_and_path_resolution(tmp_path: Path) -> None:
    """Verify discover_usage_targets scans pyproject.toml scripts dynamically."""
    from hexaqual.infra.handlers.generators import (
        discover_usage_targets,
        resolve_usage_target_rel_path,
    )

    root_toml = tmp_path / "pyproject.toml"
    root_toml.write_text(
        '[project]\nname = "my_root"\n[project.scripts]\nmytool = "my.main:app"\n',
        encoding="utf-8",
    )

    pkg_dir = tmp_path / "packages" / "my_pkg"
    pkg_dir.mkdir(parents=True)
    pkg_toml = pkg_dir / "pyproject.toml"
    pkg_toml.write_text(
        '[project]\nname = "my_pkg"\n[project.scripts]\npkgtool = "pkg.main:app"\n',
        encoding="utf-8",
    )

    targets = discover_usage_targets(tmp_path)
    assert "my_root" in targets
    assert "my_pkg" in targets

    rel_root = resolve_usage_target_rel_path("my_root", tmp_path)
    assert rel_root == "USAGE.md"

    rel_pkg = resolve_usage_target_rel_path("my_pkg", tmp_path)
    assert rel_pkg == "packages/my_pkg/USAGE.md"


def test_build_tools_usage_markdown_mocked(tmp_path: Path) -> None:
    """Verify build_tools_usage_markdown constructs catalog header and sections."""
    from hexaqual.infra.handlers.generators import (
        build_tools_usage_markdown,
        build_umbrella_usage_markdown,
    )

    with (
        patch(
            "hexaqual.infra.handlers.generators._resolve_workspace_commands",
            return_value={"mytool": ["mytool-alias"]},
        ),
        patch("hexaqual.infra.handlers.generators._append_single_command_tree") as mock_single,
    ):
        md = build_tools_usage_markdown(tmp_path)
        assert "# Hexaqual Quality Suite & CLI Catalog" in md
        assert mock_single.called

    with (
        patch(
            "hexaqual.infra.handlers.generators.extract_command_tree_bfs",
            return_value={("hexastack",): "Base help", ("hexastack", "sub"): "Sub help"},
        ),
        patch(
            "hexaqual.infra.handlers.generators.extract_subcommands_from_help",
            return_value=["sub"],
        ),
    ):
        umbrella_md = build_umbrella_usage_markdown(tmp_path)
        assert "Hexastack CLI & Framework Usage Guide" in umbrella_md
        assert "### `hexastack sub`" in umbrella_md


def test_filter_target_map_variants(tmp_path: Path) -> None:
    """Verify _filter_target_map filtering by package and affected status."""
    from hexaqual.infra.handlers.generators import _filter_target_map

    targets = {"core": tmp_path / "packages" / "core" / "USAGE.md"}

    # 1. By package
    m1 = _filter_target_map(targets, tmp_path, package="core", affected_only=False)
    assert "core" in m1

    # 2. Unknown package
    m2 = _filter_target_map(targets, tmp_path, package="unknown", affected_only=False)
    assert m2 == {}

    # 3. Affected only with empty diff
    with patch(
        "hexaqual.infra.handlers.generators.resolve_impacted_usage_targets",
        return_value=["core"],
    ):
        m3 = _filter_target_map(targets, tmp_path, package=None, affected_only=True)
        assert "core" in m3


def test_generate_pydeps_parallel_modes(tmp_path: Path) -> None:
    """Verify GeneratePydepsHandler executes with parallel=True."""
    import concurrent.futures

    handler = GeneratePydepsHandler(root=tmp_path, parallel=True)
    pkg = tmp_path / "packages" / "core"
    pkg.mkdir(parents=True)

    with (
        patch(
            "hexaqual.infra.handlers.generators.ProcessPoolExecutor",
            concurrent.futures.ThreadPoolExecutor,
        ),
        patch("hexaqual.infra.handlers.generators.get_package_directories", return_value=[pkg]),
        patch(
            "hexaqual.infra.handlers.generators.check_overview_diagram",
            return_value=(True, "docs/overview.svg"),
        ),
        patch(
            "hexaqual.infra.handlers.generators.check_package_diagram",
            return_value=(True, "docs/core.svg"),
        ),
        patch(
            "hexaqual.infra.handlers.generators.generate_package_diagram",
            return_value="docs/core.svg",
        ),
        patch(
            "hexaqual.infra.handlers.generators.generate_overview_diagram",
            return_value="docs/overview.svg",
        ),
    ):
        rep_check = handler.handle(GeneratePydepsCommand(check_only=True))
        assert rep_check.is_successful is True

        rep_gen = handler.handle(GeneratePydepsCommand(check_only=False))
        assert rep_gen.is_successful is True


def test_build_tools_usage_markdown_multi_command(tmp_path: Path) -> None:
    """Verify build_tools_usage_markdown appends multi command trees."""
    from hexaqual.infra.handlers.generators import build_tools_usage_markdown

    with (
        patch(
            "hexaqual.infra.handlers.generators._resolve_workspace_commands",
            return_value={"tool_a": ["ta"], "tool_b": []},
        ),
        patch(
            "hexaqual.infra.handlers.generators.extract_command_tree_bfs",
            return_value={("tool_a",): "Help A", ("tool_a", "sub"): "Sub A"},
        ),
    ):
        md = build_tools_usage_markdown(tmp_path)
        assert "Complete Command & Subcommand Reference" in md
        assert "### `tool_a` (aliases: `ta`)" in md
