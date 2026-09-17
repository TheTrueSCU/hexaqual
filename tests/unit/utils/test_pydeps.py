"""Unit tests for pydeps diagram generation utilities.

Notes/Architectural Intent:
    Tests SVG output directory creation, package diagram generation with mocks,
    and overview diagram generation without requiring external graphviz/pydeps binaries.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from hexaqual.utils.pydeps import (
    _output_dir,
    check_all_diagrams,
    check_overview_diagram,
    check_package_diagram,
    generate_all_diagrams,
    generate_overview_diagram,
    generate_package_diagram,
)


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

    with patch("hexaqual.utils.pydeps.pydeps") as mock_pydeps:
        res = generate_package_diagram(pkg, tmp_path)
        assert res is not None
        assert "my_pkg.svg" in res
        mock_pydeps.assert_called_once()


def test_generate_overview_diagram(tmp_path: Path) -> None:
    """Verify overview diagram generation."""
    with patch("hexaqual.utils.pydeps.pydeps") as mock_pydeps:
        res = generate_overview_diagram(tmp_path)
        assert res is not None
        assert "hexastack_packages.svg" in res
        mock_pydeps.assert_called_once()


def test_generate_all_diagrams(tmp_path: Path) -> None:
    """Verify generate_all_diagrams invokes overview and packages."""
    with (
        patch("hexaqual.utils.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.utils.pydeps.get_package_directories",
            return_value=[],
        ),
        patch(
            "hexaqual.utils.pydeps.generate_overview_diagram",
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

    with patch("hexaqual.utils.pydeps.pydeps", side_effect=fake_pydeps):
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

    with patch("hexaqual.utils.pydeps.pydeps", side_effect=fake_pydeps):
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

    with patch("hexaqual.utils.pydeps.pydeps", side_effect=fake_pydeps):
        ok, msg = check_overview_diagram(tmp_path)
        assert ok is True
        assert "hexastack_packages.svg" in msg


def test_check_all_diagrams(tmp_path: Path) -> None:
    """Verify check_all_diagrams runs checks across packages and overview."""
    with (
        patch("hexaqual.utils.pydeps.ensure_tool_installed"),
        patch(
            "hexaqual.utils.pydeps.get_package_directories",
            return_value=[],
        ),
        patch(
            "hexaqual.utils.pydeps.check_overview_diagram",
            return_value=(True, "docs/assets/pydeps/hexastack_packages.svg"),
        ),
    ):
        results = check_all_diagrams(tmp_path, parallel=False)
        assert len(results) == 1
        assert results[0][0] == "Monorepo Overview"
        assert results[0][2] is True
