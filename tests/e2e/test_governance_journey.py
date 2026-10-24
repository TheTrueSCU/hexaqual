"""User Journey HQ-01: Zero-Drift Git Lifecycle Governance demo test.

Notes/Architectural Intent:
    Demonstrates turnkey developer governance using Hexaqual.
    Registers native Git hooks across all 5 lifecycle stages, validates
    hook permissions and installation health, auto-formats out-of-order
    `__all__` declarations, and executes the fast multi-check sanity pipeline.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from hexaqual.adapters.testing.narrator import CliNarrator
from hexaqual.cli.main import app


@pytest.mark.demo
def test_governance_journey(tmp_path: Path) -> None:
    """Execute and record the Zero-Drift Git Lifecycle Governance demo.

    Args:
        tmp_path: Temporary directory fixture provided by pytest.

    Notes/Architectural Intent:
        Exercises Git hook lifecycle automation and sanity validation in a hermetic
        temporary Git repository, ensuring zero mutations to user repository state.
    """
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)

    # Sample python file with unsorted __all__
    sample_file = repo_dir / "sample_module.py"
    sample_file.write_text(
        '"""Sample module."""\n\n__all__ = [\n    "zeta",\n    "beta",\n    "alpha",\n]\n\n'
        "alpha = 1\nbeta = 2\nzeta = 3\n",
        encoding="utf-8",
    )

    repo_root = Path(__file__).resolve().parent.parent.parent
    output_dir = repo_root / "docs" / "assets" / "demos"

    narrator = CliNarrator(
        app,
        output_name="hexaqual-hooks-and-sanity",
        output_dir=output_dir,
    )

    # Step 1: Install Git lifecycle hooks
    narrator.step(
        "1. Installing Git lifecycle hooks across pre-commit, commit-msg, pre-push, post-merge, post-checkout"
    )
    res_install = narrator.run_command(["hooks", "install", "-t", str(repo_dir), "-m", "native"])
    code_install = res_install.exit_code
    assert code_install == 0
    has_installed = "Installed" in res_install.stdout or "INSTALLED" in res_install.stdout
    assert has_installed is True

    # Step 2: Verify hook registration status
    narrator.step("2. Verifying Git hook registration status and execution permissions")
    res_check = narrator.run_command(["hooks", "check", "-t", str(repo_dir)])
    code_check = res_check.exit_code
    assert code_check == 0
    has_precommit = "pre-commit" in res_check.stdout
    assert has_precommit is True

    # Step 3: Auto-format and alphabetize __all__ declarations
    narrator.step("3. Auto-formatting and alphabetizing __all__ export declarations")
    res_fix = narrator.run_command(["statements", "fix", str(sample_file)])
    code_fix = res_fix.exit_code
    assert code_fix == 0
    fixed_content = sample_file.read_text(encoding="utf-8")
    has_alpha = '"alpha"' in fixed_content
    assert has_alpha is True
    is_sorted = fixed_content.index('"alpha"') < fixed_content.index('"beta"')
    assert is_sorted is True

    # Step 4: Execute workspace sanity check
    narrator.step("4. Executing turnkey workspace sanity check across governance rules")
    res_sanity = narrator.run_command(
        [
            "sanity",
            "--skip-tests",
            "--skip-parity",
            "--skip-diagrams",
            "--skip-ruff",
            "--skip-ty",
            str(sample_file),
        ]
    )
    code_sanity = res_sanity.exit_code
    assert code_sanity == 0
    has_sanity_dash = "Hexastack Scoped Sanity Check Dashboard" in res_sanity.stdout
    assert has_sanity_dash is True

    artifacts = narrator.finish()
    if os.environ.get("RECORD_DEMO") == "1":
        vtt = artifacts.get("vtt")
        vtt_exists = vtt is not None and vtt.is_file()
        assert vtt_exists is True

        webm = artifacts.get("webm")
        webm_exists = webm is not None and webm.is_file()
        assert webm_exists is True
