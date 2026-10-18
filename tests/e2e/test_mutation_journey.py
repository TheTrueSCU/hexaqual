"""User Journey HQ-02: Mutation Testing & Mutant Triage demo test.

Notes/Architectural Intent:
    Demonstrates mutation testing inspection and triage workflows using Hexaqual.
    Inspects mutation engine options and concurrency worker decoupling, executes
    high-level triage summaries across surviving mutants, and drills down into
    actionable critical mutants with test coverage correlation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from hexastack_cli.testing.narrator import CliNarrator

from hexaqual.cli.main import app


@pytest.mark.demo
def test_mutation_journey(tmp_path: Path) -> None:
    """Execute and record the Mutation Testing & Mutant Triage demo.

    Args:
        tmp_path: Temporary directory fixture provided by pytest.

    Notes/Architectural Intent:
        Uses an isolated gremlins JSON mutation report fixture to hermetically
        exercise triage dashboards and actionable mutant inspection without
        incurring long live test execution overhead.
    """
    src_file = tmp_path / "sample.py"
    src_file.write_text(
        "def is_valid(x: int) -> bool:\n    if x > 10:\n        return True\n    return False\n",
        encoding="utf-8",
    )

    report_file = tmp_path / "gremlins.json"
    report_data = {
        "summary": {"total": 3, "zapped": 2, "survived": 1},
        "results": [
            {
                "gremlin_id": "g001",
                "file_path": str(src_file),
                "line_number": 2,
                "status": "survived",
                "operator": "comparison",
                "description": "> to >=",
            },
            {
                "gremlin_id": "g002",
                "file_path": str(src_file),
                "line_number": 3,
                "status": "zapped",
                "operator": "boolean",
                "description": "True to False",
            },
            {
                "gremlin_id": "g003",
                "file_path": str(src_file),
                "line_number": 4,
                "status": "zapped",
                "operator": "boolean",
                "description": "False to True",
            },
        ],
    }
    report_file.write_text(json.dumps(report_data), encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent.parent
    output_dir = repo_root / "docs" / "assets" / "demos"

    narrator = CliNarrator(
        app,
        output_name="hexaqual-mutation-triage",
        output_dir=output_dir,
    )

    # Step 1: Inspect mutation CLI options
    narrator.step("1. Inspecting mutation testing CLI entrypoints and worker configuration")
    res_help = narrator.run_command(["mutate", "--help"])
    code_help = res_help.exit_code
    assert code_help == 0
    has_inspect = "inspect" in res_help.stdout
    assert has_inspect is True

    # Step 2: Triage mutation summary
    narrator.step("2. Triaging mutation test cache summary and mutant survival rates")
    res_summary = narrator.run_command(
        ["mutate", "inspect", "-s", "--report-file", str(report_file)]
    )
    has_summary_table = "Surviving Mutants Triage Summary" in res_summary.stdout
    assert has_summary_table is True
    has_critical = "Critical" in res_summary.stdout
    assert has_critical is True

    # Step 3: Inspect actionable surviving mutants with coverage correlation
    narrator.step("3. Inspecting actionable surviving mutants and correlating test coverage")
    res_act = narrator.run_command(
        ["mutate", "inspect", "-act", "-c", "--report-file", str(report_file)]
    )
    has_actionable_table = "Actionable Surviving Mutants" in res_act.stdout
    assert has_actionable_table is True
    has_gremlin_desc = "if x > 10:" in res_act.stdout
    assert has_gremlin_desc is True

    artifacts = narrator.finish()
    if os.environ.get("RECORD_DEMO") == "1":
        vtt = artifacts.get("vtt")
        vtt_exists = vtt is not None and vtt.is_file()
        assert vtt_exists is True

        webm = artifacts.get("webm")
        webm_exists = webm is not None and webm.is_file()
        assert webm_exists is True
