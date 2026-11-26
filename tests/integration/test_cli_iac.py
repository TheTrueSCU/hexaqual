"""Integration tests for ``hexaqual iac`` CLI commands.

Notes/Architectural Intent:
    Exercises end-to-end IaC discovery and execution on synthetic repositories
    to verify graceful skipping on pure Python repos and accurate detection +
    JSON/Markdown output on repositories containing IaC assets.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hexaqual.cli.main import app


@pytest.mark.integration
def test_iac_clean_skip_on_pure_python_repo(
    synthetic_workspace: Path,
    runner: CliRunner,
) -> None:
    """Verify hexaqual iac discover and check skip cleanly on a pure Python repo."""
    disc_res = runner.invoke(
        app, ["iac", "discover", "--root", str(synthetic_workspace), "--format", "json"]
    )
    assert disc_res.exit_code == 0
    disc_payload = json.loads(disc_res.stdout)
    assert disc_payload["has_any"] is False
    assert disc_payload["total_files"] == 0

    chk_res = runner.invoke(
        app,
        ["iac", "check", "--root", str(synthetic_workspace), "--strict", "--format", "json"],
    )
    assert chk_res.exit_code == 0
    chk_payload = json.loads(chk_res.stdout)
    assert chk_payload["status"] == "PASS"
    assert chk_payload["has_iac_assets"] is False
    assert all(r["status"] == "SKIP" for r in chk_payload["results"])


@pytest.mark.integration
def test_iac_discovers_synthetic_assets_and_formats_output(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    """Verify hexaqual iac discover and check detect .tf, Dockerfile, and .sh files end-to-end."""
    tf_dir = tmp_path / "deploy" / "tofu" / "oci"
    tf_dir.mkdir(parents=True)
    (tf_dir / "main.tf").write_text(
        'terraform {\n  required_version = ">= 1.6.0"\n}\n',
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.13-slim-bookworm\nUSER 10001:10001\n",
        encoding="utf-8",
    )
    (tmp_path / "boot.sh").write_text(
        "#!/bin/bash\nset -euo pipefail\necho ok\n",
        encoding="utf-8",
    )

    disc_res = runner.invoke(app, ["iac", "discover", "--root", str(tmp_path), "--format", "json"])
    assert disc_res.exit_code == 0
    disc_payload = json.loads(disc_res.stdout)
    assert disc_payload["has_any"] is True
    assert disc_payload["total_files"] == 3
    assert disc_payload["assets"]["tofu_dirs"] == ["deploy/tofu/oci"]
    assert disc_payload["assets"]["dockerfiles"] == ["Dockerfile"]
    assert disc_payload["assets"]["shell_scripts"] == ["boot.sh"]

    md_res = runner.invoke(
        app,
        [
            "iac",
            "check",
            "--root",
            str(tmp_path),
            "--tool",
            "tofu-fmt",
            "--tool",
            "shellcheck",
            "--format",
            "markdown",
        ],
    )
    assert md_res.exit_code == 0
    assert "Hexaqual IaC Quality & Security Dashboard" in md_res.stdout
