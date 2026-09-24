import argparse
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from hexaqual.adapters.workspace import (
    HexaqualScriptArgumentParser,
    LocalWorkspaceAdapter,
    check_tool_availability,
    ensure_tool_installed,
    get_canonical_scripts,
    get_downstream_dependents,
    get_example_directory,
    get_package_dependencies,
    get_package_directories,
    get_package_directory,
    get_package_module_dir,
    get_packages_directory,
    get_present_layers,
    get_repo_root,
    get_valid_example_names,
    get_valid_package_names,
    get_workspace_dependency_graph,
    get_workspace_scripts,
    group_scripts_by_entrypoint,
    has_examples,
    is_multipackage_workspace,
    resolve_affected_packages,
    resolve_target_python_files,
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


def test_has_examples_and_example_helpers(tmp_path: Path) -> None:
    """Verify has_examples, get_valid_example_names, and get_example_directory."""
    assert has_examples(tmp_path) is False

    ex_dir = tmp_path / "examples"
    ex1 = ex_dir / "sample-app"
    ex1.mkdir(parents=True)
    (ex1 / "src").mkdir()
    (ex1 / "pyproject.toml").write_text('[project]\nname = "sample-app"\n', encoding="utf-8")

    assert has_examples(tmp_path) is True
    names = get_valid_example_names(tmp_path)
    assert "sample-app" in names
    assert "sample_app" in names

    found_dir = get_example_directory("sample-app", tmp_path)
    assert found_dir == ex1.resolve()

    found_dir_clean = get_example_directory("sample_app", tmp_path)
    assert found_dir_clean == ex1.resolve()

    fallback_dir = get_example_directory("unknown-app", tmp_path)
    assert fallback_dir == (ex_dir / "unknown-app").resolve()


def test_is_multipackage_workspace(tmp_path: Path) -> None:
    """Verify is_multipackage_workspace checks for packages/ directory."""
    assert is_multipackage_workspace(tmp_path) is False
    (tmp_path / "packages").mkdir()
    assert is_multipackage_workspace(tmp_path) is True


def test_resolve_target_python_files(tmp_path: Path) -> None:
    """Verify resolve_target_python_files handles explicit files, packages, and fallback."""
    # Setup a mock workspace
    pkgs = tmp_path / "packages"
    pkg1 = pkgs / "hexastack_core"
    pkg1_src = pkg1 / "src" / "hexastack_core"
    pkg1_src.mkdir(parents=True)
    f1 = pkg1_src / "mod1.py"
    f1.write_text("x = 1\n", encoding="utf-8")

    pkg2 = pkgs / "hexastack_events"
    pkg2_src = pkg2 / "src" / "hexastack_events"
    pkg2_src.mkdir(parents=True)
    f2 = pkg2_src / "mod2.py"
    f2.write_text("y = 2\n", encoding="utf-8")

    (tmp_path / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n', encoding="utf-8"
    )
    (pkg1 / "pyproject.toml").write_text('[project]\nname = "hexastack-core"\n', encoding="utf-8")
    (pkg2 / "pyproject.toml").write_text('[project]\nname = "hexastack-events"\n', encoding="utf-8")

    # 1. Explicit files
    res_files = resolve_target_python_files(repo_root=tmp_path, files=[f1])
    assert res_files == [f1.resolve()]

    # 2. Scoped to a package
    res_pkg = resolve_target_python_files(repo_root=tmp_path, packages=["core"])
    assert res_pkg == [f1.resolve()]

    # 3. All packages
    res_all = resolve_target_python_files(repo_root=tmp_path)
    assert f1.resolve() in res_all
    assert f2.resolve() in res_all

    # 4. Via legacy args object
    dummy_args = argparse.Namespace(files=[str(f2)], custom_paths=None, packages=None)
    res_args = resolve_target_python_files(args=dummy_args, repo_root=tmp_path)
    assert res_args == [f2.resolve()]


def test_package_dependencies_and_dependency_graphs(tmp_path: Path) -> None:
    """Verify get_package_dependencies, graph resolution, and downstream dependents."""
    pkgs = tmp_path / "packages"
    core = pkgs / "hexastack_core"
    core.mkdir(parents=True)
    (core / "pyproject.toml").write_text(
        '[project]\nname = "hexastack-core"\ndependencies = []\n',
        encoding="utf-8",
    )

    cqrs = pkgs / "hexastack_cqrs"
    cqrs.mkdir(parents=True)
    (cqrs / "pyproject.toml").write_text(
        '[project]\nname = "hexastack-cqrs"\n'
        'dependencies = ["hexastack-core>=0.5.0"]\n'
        "[tool.uv.sources]\nhexastack-core = { workspace = true }\n",
        encoding="utf-8",
    )

    events = pkgs / "hexastack_events"
    events.mkdir(parents=True)
    (events / "pyproject.toml").write_text(
        '[project]\nname = "hexastack-events"\ndependencies = ["hexastack-cqrs>=0.5.0"]\n',
        encoding="utf-8",
    )

    (tmp_path / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n', encoding="utf-8"
    )

    # Test single package dependencies
    deps_core = get_package_dependencies(core)
    assert deps_core == set()

    deps_cqrs = get_package_dependencies(cqrs)
    assert "core" in deps_cqrs

    # Test workspace dependency graphs
    forward, reverse = get_workspace_dependency_graph(tmp_path)
    assert "core" in forward["cqrs"]
    assert "cqrs" in forward["events"]

    assert "cqrs" in reverse["core"]
    assert "events" in reverse["cqrs"]

    # Test downstream dependents
    downstream = get_downstream_dependents("core", reverse)
    assert downstream == {"cqrs", "events"}

    downstream_cqrs = get_downstream_dependents("cqrs", reverse)
    assert downstream_cqrs == {"events"}

    # Test package with unreadable or missing pyproject
    empty_dir = tmp_path / "empty_pkg"
    empty_dir.mkdir()
    assert get_package_dependencies(empty_dir) == set()


def test_resolve_affected_packages_detailed(tmp_path: Path) -> None:
    """Verify resolve_affected_packages handles pyproject changes, src changes, tests changes."""
    pkgs = tmp_path / "packages"
    core = pkgs / "hexastack_core"
    core.mkdir(parents=True)
    (core / "pyproject.toml").write_text('[project]\nname = "hexastack-core"\n', encoding="utf-8")
    cqrs = pkgs / "hexastack_cqrs"
    cqrs.mkdir(parents=True)
    (cqrs / "pyproject.toml").write_text(
        '[project]\nname = "hexastack-cqrs"\ndependencies = ["hexastack-core"]\n',
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n', encoding="utf-8"
    )

    # 1. Package pyproject.toml changed -> impacts self + downstream
    aff1 = resolve_affected_packages(["packages/hexastack_core/pyproject.toml"], repo_root=tmp_path)
    assert aff1 == {"core", "cqrs"}

    # 2. Package src/ changed -> impacts self + downstream
    aff2 = resolve_affected_packages(
        ["packages/hexastack_core/src/hexastack_core/mod.py"], repo_root=tmp_path
    )
    assert aff2 == {"core", "cqrs"}

    # 3. Package tests/ changed -> impacts ONLY self
    aff3 = resolve_affected_packages(
        ["packages/hexastack_core/tests/unit/test_mod.py"], repo_root=tmp_path
    )
    assert aff3 == {"core"}


def test_local_workspace_adapter(tmp_path: Path) -> None:
    """Verify LocalWorkspaceAdapter delegates to module-level functions."""
    adapter = LocalWorkspaceAdapter()
    root = adapter.get_repo_root()
    assert (root / "pyproject.toml").is_file()

    pkgs = tmp_path / "packages" / "hexastack_core"
    pkgs.mkdir(parents=True)
    (pkgs / "pyproject.toml").write_text('[project]\nname = "hexastack-core"\n', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.uv.workspace]\nmembers = ["packages/*"]\n', encoding="utf-8"
    )

    assert adapter.is_multipackage_workspace(tmp_path) is True
    assert adapter.get_packages_directory(tmp_path) == tmp_path / "packages"
    assert len(adapter.get_package_directories(tmp_path)) == 1
    assert adapter.get_package_directory("core", tmp_path).name == "hexastack_core"


def test_get_repo_root_starting_from_file_and_error(tmp_path: Path) -> None:
    """Verify get_repo_root when starting from a file or when root cannot be found."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    child_file = tmp_path / "sub" / "file.py"
    child_file.parent.mkdir()
    child_file.write_text("print(1)\n", encoding="utf-8")

    assert get_repo_root(child_file) == tmp_path

    # Completely isolated empty temp dir without git or pyproject
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    with (
        pytest.raises(RuntimeError) as exc_info,
        patch.object(Path, "parents", new=[]),
    ):
        get_repo_root(isolated)
    assert "Could not determine repository root" in str(exc_info.value)


def test_hexaqual_script_argument_parser() -> None:
    """Verify HexaqualScriptArgumentParser parses files, packages, paths, and flags."""
    parser = HexaqualScriptArgumentParser("Test parser")
    args = parser.parse_args(["-p", "core", "--path", "src", "-a", "file1.py"])
    assert args.packages == ["core"]
    assert args.custom_paths == ["src"]
    assert args.files == ["file1.py"]
    assert args.all is True


def test_check_tool_availability_cli_command() -> None:
    """Verify check_tool_availability with cli_command present and missing."""
    is_ok, err = check_tool_availability("pytest", cli_command="python")
    assert is_ok is True
    assert err == ""

    is_ok2, err2 = check_tool_availability("pytest", cli_command="non_existent_binary_xyz_123")
    assert is_ok2 is False
    assert "was not found in PATH" in err2


def test_ensure_tool_installed_success() -> None:
    """Verify ensure_tool_installed does not exit when tool is present."""
    ensure_tool_installed("pytest")


def test_package_module_dir_and_fallback(tmp_path: Path) -> None:
    """Verify get_package_module_dir edge cases and get_package_directory fallback."""
    no_src = tmp_path / "no_src_pkg"
    no_src.mkdir()
    assert get_package_module_dir(no_src) is None
    assert get_present_layers(no_src) == set()

    empty_src = tmp_path / "empty_src_pkg"
    (empty_src / "src").mkdir(parents=True)
    assert get_package_module_dir(empty_src) is None

    # Fallback in get_package_directory when package is not found
    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    fallback = get_package_directory("non_existent_pkg", tmp_path)
    assert fallback == pkgs / "non_existent_pkg"
