import tempfile
from pathlib import Path

import pytest

from hexaqual.infra.workspace import (
    check_tool_availability,
    ensure_tool_installed,
    get_canonical_scripts,
    get_package_directories,
    get_package_directory,
    get_package_module_dir,
    get_packages_directory,
    get_present_layers,
    get_repo_root,
    get_valid_package_names,
    get_workspace_scripts,
    group_scripts_by_entrypoint,
    resolve_affected_packages,
)


def test_check_tool_availability_existing() -> None:
    """Verify check_tool_availability for installed package."""
    is_ok, err = check_tool_availability("rich")
    assert is_ok is True
    assert err == ""


def test_check_tool_availability_missing() -> None:
    """Verify check_tool_availability for non-existent package."""
    is_ok, err = check_tool_availability("non_existent_package_xyz_99")
    assert is_ok is False
    assert "not installed" in err


def test_ensure_tool_installed_raises_system_exit_on_missing() -> None:
    """Verify ensure_tool_installed exits with error code 1 when missing."""
    with pytest.raises(SystemExit) as exc_info:
        ensure_tool_installed("non_existent_tool_123", extra_name="test-extra")
    assert exc_info.value.code == 1


def test_get_repo_root() -> None:
    """Verify repo root discovery."""
    root = get_repo_root()
    assert (root / "pyproject.toml").is_file()


def test_get_packages_directory(tmp_path: Path) -> None:
    """Verify packages directory resolution."""
    pkg_dir = get_packages_directory()
    assert pkg_dir.is_dir()

    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    assert get_packages_directory(tmp_path) == pkgs


def test_get_package_directory(tmp_path: Path) -> None:
    """Verify individual package path resolution."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    pkg_dir.mkdir(parents=True)
    core_dir = get_package_directory("core", tmp_path)
    assert core_dir.name == "hexastack_core"
    assert core_dir.is_dir()


def test_get_package_directories(tmp_path: Path) -> None:
    """Verify list of package directories contains known packages."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "pyproject.toml").write_text("[project]\nname='hexastack-core'\n")
    dirs = get_package_directories(tmp_path)
    names = {d.name for d in dirs}
    assert "hexastack_core" in names
    assert len(dirs) >= 1


def test_get_valid_package_names(tmp_path: Path) -> None:
    """Verify dynamic valid package name enumeration."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "pyproject.toml").write_text("[project]\nname='hexastack-core'\n")
    names = get_valid_package_names(tmp_path)
    assert "core" in names
    assert "hexastack_core" in names


def test_get_package_module_dir(tmp_path: Path) -> None:
    """Verify detection of internal module directory under src/."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    mod = pkg_dir / "src" / "hexastack_core"
    mod.mkdir(parents=True)
    mod_dir = get_package_module_dir(pkg_dir)
    assert mod_dir is not None
    assert mod_dir.name == "hexastack_core"


def test_get_present_layers(tmp_path: Path) -> None:
    """Verify detection of hexagonal layers."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    for layer in ("domain", "ports", "adapters"):
        (pkg_dir / "src" / "hexastack_core" / layer).mkdir(parents=True)
    layers = get_present_layers(pkg_dir)
    assert "domain" in layers
    assert "ports" in layers
    assert "adapters" in layers

    # Single-package root with src
    single_dir = tmp_path / "single_pkg"
    for layer in ("domain", "ports"):
        (single_dir / "src" / "single_pkg" / layer).mkdir(parents=True)
    single_layers = get_present_layers(single_dir)
    assert "domain" in single_layers
    assert "ports" in single_layers


def test_standalone_single_package_workspace_discovery() -> None:
    """Verify workspace tools function in a standalone single-package repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pyproject.toml").write_text('[project]\nname = "my-service"\n', encoding="utf-8")
        src_dir = root / "src" / "my_service" / "domain"
        src_dir.mkdir(parents=True)
        (src_dir / "models.py").write_text("# domain model", encoding="utf-8")

        discovered_dirs = get_package_directories(repo_root=root)
        assert len(discovered_dirs) == 1
        assert discovered_dirs[0] == root

        pkg_dir = get_package_directory("my-service", repo_root=root)
        assert pkg_dir == root

        mod_dir = get_package_module_dir(root)
        assert mod_dir is not None
        assert mod_dir.name == "my_service"

        layers = get_present_layers(root)
        assert "domain" in layers


def test_custom_monorepo_workspace_discovery() -> None:
    """Verify workspace tools discover custom monorepo members like hexaqueue."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        pyproject_content = """[tool.uv.workspace]
members = [
    "services/*",
]
"""
        (root / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

        for s in ("hq_server", "hq_worker"):
            pkg_path = root / "services" / s
            (pkg_path / "src" / s / "domain").mkdir(parents=True)
            (pkg_path / "pyproject.toml").write_text(f'[project]\nname = "{s}"\n', encoding="utf-8")

        discovered_dirs = get_package_directories(repo_root=root)
        assert len(discovered_dirs) == 2
        dir_names = {d.name for d in discovered_dirs}
        assert dir_names == {"hq_server", "hq_worker"}

        server_dir = get_package_directory("hq_server", repo_root=root)
        assert server_dir.name == "hq_server"


def test_resolve_affected_packages(tmp_path: Path) -> None:
    """Verify affected packages resolution for various changed file paths."""
    # 1. Empty change list returns empty set
    assert resolve_affected_packages([], repo_root=tmp_path) == set()

    # 2. Root files (pyproject.toml, uv.lock) impact all (None)
    assert resolve_affected_packages(["pyproject.toml"], repo_root=tmp_path) is None
    assert resolve_affected_packages(["uv.lock"], repo_root=tmp_path) is None

    # 3. .github impacts all (None)
    assert resolve_affected_packages([".github/workflows/ci.yml"], repo_root=tmp_path) is None

    # 4. examples directory changes do NOT impact packages
    assert (
        resolve_affected_packages(["examples/financial-ledger/Dockerfile"], repo_root=tmp_path)
        == set()
    )

    # 5. docs changes do NOT impact packages
    assert (
        resolve_affected_packages(["docs/assets/pydeps/hexaqual.svg"], repo_root=tmp_path) == set()
    )


def test_get_workspace_scripts(tmp_path: Path) -> None:
    """Verify get_workspace_scripts extracts scripts from root pyproject.toml."""
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text(
        '[project.scripts]\nhexaqual = "hexaqual.cli.main:app"\n',
        encoding="utf-8",
    )
    scripts = get_workspace_scripts(tmp_path)
    assert scripts == {
        "hexaqual": "hexaqual.cli.main:app",
    }

    # Non-existent pyproject returns empty dict
    assert get_workspace_scripts(tmp_path / "nonexistent") == {}


def test_group_scripts_by_entrypoint() -> None:
    """Verify grouping scripts by target entrypoint string."""
    scripts = {
        "alphabetizer": "hexaqual.commands.rope:alphabetize_main",
        "rope-alphabetizer": "hexaqual.commands.rope:alphabetize_main",
        "sanity-check": "hexaqual.commands.sanity_check:main",
    }
    grouped = group_scripts_by_entrypoint(scripts)
    assert grouped["hexaqual.commands.rope:alphabetize_main"] == [
        "alphabetizer",
        "rope-alphabetizer",
    ]
    assert grouped["hexaqual.commands.sanity_check:main"] == ["sanity-check"]


def test_get_canonical_scripts() -> None:
    """Verify resolving canonical scripts and detecting aliases."""
    scripts = {
        "hexaqual": "hexaqual.cli.main:app",
        "sanity-check": "hexaqual.commands.sanity_check:main",
        "alphabetizer": "hexaqual.commands.rope:alphabetize_main",
        "rope-alphabetizer": "hexaqual.commands.rope:alphabetize_main",
    }
    canonical = get_canonical_scripts(scripts)
    assert canonical["hexaqual"] == []
    assert canonical["alphabetizer"] == ["rope-alphabetizer"]
    assert canonical["sanity-check"] == []
