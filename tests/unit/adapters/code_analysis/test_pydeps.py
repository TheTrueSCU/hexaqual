"""Unit tests for pydeps diagram generation utilities.

Notes/Architectural Intent:
    Tests SVG output directory creation, package diagram generation with mocks,
    and overview diagram generation without requiring external graphviz/pydeps binaries.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from hexaqual.adapters.code_analysis.pydeps import (
    _output_dir,
    check_all_diagrams,
    check_overview_diagram,
    check_package_diagram,
    generate_all_diagrams,
    generate_overview_diagram,
    generate_package_diagram,
)


@pytest.fixture(autouse=True)
def mock_dot_available() -> Generator[None]:
    """Provide a mock dot executable path so unit tests don't depend on system graphviz."""
    with patch("shutil.which", return_value="/usr/bin/dot"):
        yield


def test_output_dir(tmp_path: Path) -> None:
    """Verify _output_dir respects create parameter."""
    out_no_create = _output_dir(tmp_path, create=False)
    assert not out_no_create.exists()
    assert out_no_create == tmp_path / "docs" / "assets" / "pydeps"

    out_create = _output_dir(tmp_path, create=True)
    assert out_create.is_dir()
    assert out_create == tmp_path / "docs" / "assets" / "pydeps"


def test_generate_package_diagram_no_entry_point(tmp_path: Path) -> None:
    """Verify None returned when package has no src/<name> dir."""
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    res = generate_package_diagram(pkg, tmp_path)
    assert res is None


def test_generate_package_diagram_success(tmp_path: Path) -> None:
    """Verify SVG path returned when pydeps completes."""
    pkg = tmp_path / "my_pkg"
    (pkg / "src" / "my_pkg").mkdir(parents=True)

    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps") as mock_pydeps:
        res = generate_package_diagram(pkg, tmp_path)
        assert res is not None
        assert "my_pkg.svg" in res
        mock_pydeps.assert_called_once()


def test_generate_overview_diagram(tmp_path: Path) -> None:
    """Verify overview diagram generation."""
    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps") as mock_pydeps:
        res = generate_overview_diagram(tmp_path)
        assert res is not None
        assert "hexastack_packages.svg" in res
        mock_pydeps.assert_called_once()


def test_generate_all_diagrams(tmp_path: Path) -> None:
    """Verify generate_all_diagrams invokes overview and packages."""
    with (
        patch("hexaqual.adapters.code_analysis.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.get_package_directories",
            return_value=[],
        ),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.generate_overview_diagram",
            return_value="docs/assets/pydeps/hexastack_packages.svg",
        ),
    ):
        results = generate_all_diagrams(tmp_path)
        assert len(results) == 1
        assert results[0][0] == "Monorepo Overview"


def test_check_package_diagram_no_entry_point(tmp_path: Path) -> None:
    """Verify check_package_diagram handles missing src directory gracefully."""
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    ok, msg = check_package_diagram(pkg, tmp_path)
    assert ok is True
    assert "No source directory" in msg


def test_check_package_diagram_missing_svg(tmp_path: Path) -> None:
    """Verify check_package_diagram flags missing existing SVG as stale."""
    pkg = tmp_path / "my_pkg"
    (pkg / "src" / "my_pkg").mkdir(parents=True)
    ok, msg = check_package_diagram(pkg, tmp_path)
    assert ok is False
    assert "does not exist" in msg


def test_check_package_diagram_up_to_date(tmp_path: Path) -> None:
    """Verify check_package_diagram returns True when bytes match."""
    pkg = tmp_path / "my_pkg"
    (pkg / "src" / "my_pkg").mkdir(parents=True)
    svg_dir = tmp_path / "docs" / "assets" / "pydeps"
    svg_dir.mkdir(parents=True)
    target_svg = svg_dir / "my_pkg.svg"
    target_svg.write_bytes(b"<svg>match</svg>")

    def fake_pydeps(*args: object, **kwargs: object) -> None:
        out_path = Path(str(kwargs.get("output")))
        out_path.write_bytes(b"<svg>match</svg>")

    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=fake_pydeps):
        ok, msg = check_package_diagram(pkg, tmp_path)
        assert ok is True
        assert "my_pkg.svg" in msg


def test_check_package_diagram_stale(tmp_path: Path) -> None:
    """Verify check_package_diagram returns False when bytes differ."""
    pkg = tmp_path / "my_pkg"
    (pkg / "src" / "my_pkg").mkdir(parents=True)
    svg_dir = tmp_path / "docs" / "assets" / "pydeps"
    svg_dir.mkdir(parents=True)
    target_svg = svg_dir / "my_pkg.svg"
    target_svg.write_bytes(b"<svg>old</svg>")

    def fake_pydeps(*args: object, **kwargs: object) -> None:
        out_path = Path(str(kwargs.get("output")))
        out_path.write_bytes(b"<svg>new</svg>")

    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=fake_pydeps):
        ok, msg = check_package_diagram(pkg, tmp_path)
        assert ok is False
        assert "my_pkg.svg" in msg


def test_check_overview_diagram_missing_svg(tmp_path: Path) -> None:
    """Verify check_overview_diagram flags missing overview SVG."""
    pkgs = tmp_path / "packages"
    pkgs.mkdir(parents=True)
    ok, msg = check_overview_diagram(tmp_path)
    assert ok is False
    assert "does not exist" in msg


def test_check_overview_diagram_up_to_date(tmp_path: Path) -> None:
    """Verify check_overview_diagram returns True when bytes match."""
    pkgs = tmp_path / "packages"
    pkgs.mkdir(parents=True)
    svg_dir = tmp_path / "docs" / "assets" / "pydeps"
    svg_dir.mkdir(parents=True)
    target_svg = svg_dir / "hexastack_packages.svg"
    target_svg.write_bytes(b"<svg>overview</svg>")

    def fake_pydeps(*args: object, **kwargs: object) -> None:
        out_path = Path(str(kwargs.get("output")))
        out_path.write_bytes(b"<svg>overview</svg>")

    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=fake_pydeps):
        ok, msg = check_overview_diagram(tmp_path)
        assert ok is True
        assert "hexastack_packages.svg" in msg


def test_check_all_diagrams(tmp_path: Path) -> None:
    """Verify check_all_diagrams runs checks across packages and overview."""
    with (
        patch("hexaqual.adapters.code_analysis.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.get_package_directories",
            return_value=[],
        ),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.check_overview_diagram",
            return_value=(True, "docs/assets/pydeps/hexastack_packages.svg"),
        ),
    ):
        results = check_all_diagrams(tmp_path, parallel=False)
        assert len(results) == 1
        assert results[0][0] == "Monorepo Overview"
        assert results[0][2] is True


def test_pydeps_missing_dot_handling(tmp_path: Path) -> None:
    """Verify pydeps generation and checks handle missing dot executable gracefully.

    Args:
        tmp_path: Temporary filesystem fixture path.

    Notes/Architectural Intent:
        Ensures graceful skipping without hard crashes when Graphviz is not installed.
    """
    pkg = tmp_path / "my_pkg"
    (pkg / "src" / "my_pkg").mkdir(parents=True)
    (tmp_path / "packages").mkdir(parents=True)

    with patch("shutil.which", return_value=None):
        gen_pkg = generate_package_diagram(pkg, tmp_path)
        assert gen_pkg is None

        gen_ov = generate_overview_diagram(tmp_path)
        assert gen_ov is None

        with patch("hexaqual.adapters.code_analysis.pydeps.ensure_tool_installed"):
            gen_all = generate_all_diagrams(tmp_path)
            assert gen_all == []

            check_all = check_all_diagrams(tmp_path)
            assert len(check_all) == 1
            assert check_all[0][2] is True
            assert "Graphviz 'dot' not installed" in check_all[0][1]

        check_pkg_ok, check_pkg_msg = check_package_diagram(pkg, tmp_path)
        assert check_pkg_ok is True
        assert "Graphviz 'dot' not installed" in check_pkg_msg

        check_ov_ok, check_ov_msg = check_overview_diagram(tmp_path)
        assert check_ov_ok is True
        assert "Graphviz 'dot' not installed" in check_ov_msg


def test_pydeps_entry_point_fallback_and_exceptions(tmp_path: Path) -> None:
    """Verify entry point detection for single subfolder and exception handling in pydeps."""
    # 1. Single subfolder in src/
    pkg = tmp_path / "custom_pkg"
    (pkg / "src" / "internal_mod").mkdir(parents=True)
    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps") as mock_pydeps:
        res = generate_package_diagram(pkg, tmp_path)
        assert res is not None
        mock_pydeps.assert_called_once()

    # 2. generate_package_diagram exception
    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=RuntimeError("boom")):
        res_err = generate_package_diagram(pkg, tmp_path)
        assert res_err is None

    # 3. generate_overview_diagram exception
    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=RuntimeError("boom")):
        res_ov_err = generate_overview_diagram(tmp_path)
        assert res_ov_err is None


def test_check_package_and_overview_diagram_exceptions_and_mismatches(tmp_path: Path) -> None:
    """Verify check_package_diagram and check_overview_diagram error and mismatch branches."""
    # 1. check_overview_diagram without packages dir
    with patch(
        "hexaqual.adapters.code_analysis.pydeps.get_packages_directory",
        return_value=tmp_path / "nonexistent_pkgs",
    ):
        ok_no_pkg, msg_no_pkg = check_overview_diagram(tmp_path)
        assert ok_no_pkg is True
        assert "No packages directory found" in msg_no_pkg

    # 2. check_package_diagram failed tmp file generation
    pkg = tmp_path / "my_pkg"
    (pkg / "src" / "my_pkg").mkdir(parents=True)
    svg_dir = tmp_path / "docs" / "assets" / "pydeps"
    svg_dir.mkdir(parents=True)
    (svg_dir / "my_pkg.svg").write_bytes(b"<svg>1</svg>")

    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps"):
        ok_no_tmp, msg_no_tmp = check_package_diagram(pkg, tmp_path)
        assert ok_no_tmp is False
        assert "Failed to generate comparison diagram" in msg_no_tmp

    # 3. check_package_diagram exception
    with patch(
        "hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=RuntimeError("pydeps crash")
    ):
        ok_exc, msg_exc = check_package_diagram(pkg, tmp_path)
        assert ok_exc is False
        assert "Error verifying diagram" in msg_exc

    # 4. check_overview_diagram failed tmp file generation
    pkgs = tmp_path / "packages"
    pkgs.mkdir(parents=True)
    (svg_dir / "hexastack_packages.svg").write_bytes(b"<svg>old</svg>")

    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps"):
        ok_ov_tmp, msg_ov_tmp = check_overview_diagram(tmp_path)
        assert ok_ov_tmp is False
        assert "Failed to generate comparison overview diagram" in msg_ov_tmp

    # 5. check_overview_diagram mismatch
    def write_diff_overview(*args: object, **kwargs: object) -> None:
        out = Path(str(kwargs.get("output")))
        out.write_bytes(b"<svg>different</svg>")

    with patch("hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=write_diff_overview):
        ok_diff, msg_diff = check_overview_diagram(tmp_path)
        assert ok_diff is False
        assert "hexastack_packages.svg" in msg_diff

    # 6. check_overview_diagram exception
    with patch(
        "hexaqual.adapters.code_analysis.pydeps.pydeps", side_effect=RuntimeError("ov crash")
    ):
        ok_ov_exc, msg_ov_exc = check_overview_diagram(tmp_path)
        assert ok_ov_exc is False
        assert "Error verifying overview diagram" in msg_ov_exc


def test_generate_and_check_all_diagrams_execution_modes(tmp_path: Path) -> None:
    """Verify generate_all_diagrams and check_all_diagrams in sequential and parallel modes."""
    import concurrent.futures

    pkg = tmp_path / "packages" / "hexastack_core"
    (pkg / "src" / "hexastack_core").mkdir(parents=True)

    with (
        patch("hexaqual.adapters.code_analysis.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.generate_overview_diagram",
            return_value="ov.svg",
        ),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.generate_package_diagram",
            return_value="pkg.svg",
        ),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.check_overview_diagram",
            return_value=(True, "ov.svg"),
        ),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.check_package_diagram",
            return_value=(True, "pkg.svg"),
        ),
        patch(
            "hexaqual.adapters.code_analysis.pydeps.ProcessPoolExecutor",
            concurrent.futures.ThreadPoolExecutor,
        ),
    ):
        # 1. generate_all_diagrams sequential with explicit packages
        gen_seq = generate_all_diagrams(tmp_path, packages=[pkg], parallel=False)
        assert len(gen_seq) == 1
        assert gen_seq[0] == ("hexastack_core", "pkg.svg")

        # 2. generate_all_diagrams parallel with all packages (including overview)
        gen_par = generate_all_diagrams(tmp_path, packages=[pkg], parallel=True)
        assert len(gen_par) == 1
        assert gen_par[0] == ("hexastack_core", "pkg.svg")

        # 3. check_all_diagrams sequential
        chk_seq = check_all_diagrams(tmp_path, packages=[pkg], parallel=False)
        assert len(chk_seq) == 1
        assert chk_seq[0] == ("hexastack_core", "pkg.svg", True)

        # 4. check_all_diagrams parallel
        chk_par = check_all_diagrams(tmp_path, packages=[pkg], parallel=True)
        assert len(chk_par) == 1
        assert chk_par[0] == ("hexastack_core", "pkg.svg", True)
