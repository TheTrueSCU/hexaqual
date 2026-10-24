"""User Journey HQ-04: Reproducible Multi-Package Release demo test.

Notes/Architectural Intent:
    Demonstrates package release verification, distribution artifact building,
    and byte-for-byte reproducible build verification using Hexaqual.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hexaqual.adapters.testing.narrator import CliNarrator
from hexaqual.cli.main import app
from hexaqual.domain.pypi import (
    PackageBuildResult,
    PackageMetadata,
    PackageReleaseCheck,
    PyPiBuildReport,
    PyPiCheckReport,
    ReproducibleArtifactResult,
    ReproducibleBuildReport,
)


@pytest.mark.demo
def test_release_journey(tmp_path: Path) -> None:
    """Execute and record the Reproducible Multi-Package Release demo.

    Args:
        tmp_path: Temporary directory fixture provided by pytest.

    Notes/Architectural Intent:
        Mocks the PyPI publisher bus dispatcher to present authentic release
        engineering dashboards and reproducibility comparisons without network writes.
    """
    pkg = PackageMetadata(
        name="hexaqual",
        version="0.3.0",
        dir_path=tmp_path,
        pyproject_path=tmp_path / "pyproject.toml",
    )
    mock_check = PyPiCheckReport(checks=(PackageReleaseCheck(pkg, exists=True),))
    mock_build = PyPiBuildReport(
        target_dist=tmp_path / "dist",
        results=(PackageBuildResult(package=pkg, success=True),),
    )
    mock_repro = ReproducibleBuildReport(
        epoch="1700000000",
        results=(
            ReproducibleArtifactResult(
                package_name="hexaqual",
                artifact_name="hexaqual-0.3.0-py3-none-any.whl",
                hash1="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                hash2="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                is_reproducible=True,
            ),
        ),
    )

    repo_root = Path(__file__).resolve().parent.parent.parent
    output_dir = repo_root / "docs" / "assets" / "demos"

    narrator = CliNarrator(
        app,
        output_name="hexaqual-reproducible-release",
        output_dir=output_dir,
    )

    with patch("hexaqual.cli.release.create_governance_bus") as mock_bus_builder:
        mock_bus_builder.return_value.dispatch.side_effect = [
            mock_check,
            mock_build,
            mock_repro,
        ]

        # Step 1: Check PyPI release status
        narrator.step("1. Validating package distributions and inspecting PyPI release status")
        res_check = narrator.run_command(["release", "check", "-p", "hexaqual"])
        code_check = res_check.exit_code
        assert code_check == 0
        has_check_dash = "PyPI Release Version Availability Checker" in res_check.stdout
        assert has_check_dash is True

        # Step 2: Build reproducible distributions
        narrator.step("2. Building reproducible distribution wheels and source archives")
        res_build = narrator.run_command(["release", "build"])
        code_build = res_build.exit_code
        assert code_build == 0
        has_build_dash = "PyPI Monorepo Distribution Builder" in res_build.stdout
        assert has_build_dash is True

        # Step 3: Verify bit-for-bit reproducible wheel builds
        narrator.step(
            "3. Verifying byte-for-byte reproducible wheel package builds across isolated environments"
        )
        res_repro = narrator.run_command(["release", "reproducible"])
        code_repro = res_repro.exit_code
        assert code_repro == 0
        has_repro_dash = "PyPI Reproducible Build Auditor" in res_repro.stdout
        assert has_repro_dash is True

    artifacts = narrator.finish()
    if os.environ.get("RECORD_DEMO") == "1":
        vtt = artifacts.get("vtt")
        vtt_exists = vtt is not None and vtt.is_file()
        assert vtt_exists is True

        webm = artifacts.get("webm")
        webm_exists = webm is not None and webm.is_file()
        assert webm_exists is True
