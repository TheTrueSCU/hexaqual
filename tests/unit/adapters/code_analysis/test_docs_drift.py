"""Unit tests for documentation prose drift scanner.

Notes/Architectural Intent:
    Verifies detection of contradictory facts, stale release versions, and out-of-date
    package counts across documentation files, and verifies exclusion of CHANGELOG.md.
"""

from __future__ import annotations

from pathlib import Path

from hexaqual.adapters.code_analysis.docs_drift import (
    extract_canonical_version,
    get_package_count,
    scan_docs_drift,
)


def test_extract_canonical_version(tmp_path: Path) -> None:
    """Verify version extraction from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-pkg"\nversion = "0.9.0"\n', encoding="utf-8")

    version = extract_canonical_version(tmp_path)
    assert version == "0.9.0"

    missing_version = extract_canonical_version(tmp_path / "nonexistent")
    assert missing_version == ""


def test_get_package_count(tmp_path: Path) -> None:
    """Verify package directory counting."""
    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    (pkgs / "pkg_a").mkdir()
    (pkgs / "pkg_a" / "pyproject.toml").write_text(
        "[project]\nversion = '1.0.0'\n", encoding="utf-8"
    )
    (pkgs / "pkg_b").mkdir()
    (pkgs / "pkg_b" / "pyproject.toml").write_text(
        "[project]\nversion = '1.0.0'\n", encoding="utf-8"
    )
    (pkgs / "not_a_pkg").mkdir()

    count = get_package_count(tmp_path)
    assert count == 2

    empty_count = get_package_count(tmp_path / "other")
    assert empty_count == 0


def test_scan_docs_drift_detects_stale_prose(tmp_path: Path) -> None:
    """Verify scan_docs_drift detects stale version and package count in markdown."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.9.0"\n', encoding="utf-8")

    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    for name in ("a", "b", "c"):
        p = pkgs / name
        p.mkdir()
        (p / "pyproject.toml").write_text("[project]\nversion = '0.9.0'\n", encoding="utf-8")

    doc = tmp_path / "README.md"
    doc.write_text(
        "# My Project\n\n![badge](https://img.shields.io/badge/version-v0.8.0-blue.svg)\n\nAcross all 2 packages.\n",
        encoding="utf-8",
    )

    report = scan_docs_drift(tmp_path)
    assert report.is_successful is False
    drift_types = [f.drift_type for f in report.findings]
    assert "version_mismatch" in drift_types
    assert "package_count_mismatch" in drift_types


def test_scan_docs_drift_ignores_changelog(tmp_path: Path) -> None:
    """Verify CHANGELOG.md is excluded from drift detection."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.9.0"\n', encoding="utf-8")

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "## v0.8.0 - Historical Release\n- Added 2 packages\n",
        encoding="utf-8",
    )

    report = scan_docs_drift(tmp_path)
    assert report.is_successful is True
    assert len(report.findings) == 0


def test_scan_docs_drift_clean(tmp_path: Path) -> None:
    """Verify scan_docs_drift passes when docs match canonical truths."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.9.0"\n', encoding="utf-8")

    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    for name in ("a", "b"):
        p = pkgs / name
        p.mkdir()
        (p / "pyproject.toml").write_text("[project]\nversion = '0.9.0'\n", encoding="utf-8")

    doc = tmp_path / "README.md"
    doc.write_text(
        "# My Project\n\n![badge](https://img.shields.io/badge/version-v0.9.0-blue.svg)\n\nAcross all 2 packages.\n",
        encoding="utf-8",
    )

    report = scan_docs_drift(tmp_path)
    assert report.is_successful is True
    assert len(report.findings) == 0
