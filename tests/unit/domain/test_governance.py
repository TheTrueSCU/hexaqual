"""Unit tests for governance domain models and commands.

Notes/Architectural Intent:
    Verifies that governance commands, enums, targets, and result aggregates
    instantiate correctly with immutable data invariants.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from hexaqual.domain.governance import (
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckDiagramsCommand,
    CheckResult,
    CheckStatus,
    CheckTestParityCommand,
    RunLinterCommand,
    RunPytestCommand,
    RunSanityCheckCommand,
    RunTypecheckCommand,
    SanityCheckReport,
    SanityTarget,
    resolve_default_parallelism,
    resolve_parallelism,
)


def test_check_status_enum():
    """Verify CheckStatus enum members."""
    assert CheckStatus.PASS.value == "PASS"
    assert CheckStatus.FAIL.value == "FAIL"
    assert CheckStatus.SKIP.value == "SKIP"


def test_sanity_target_and_check_result():
    """Verify SanityTarget and CheckResult creation."""
    target = SanityTarget(
        name="test-pkg",
        kind="package",
        path=Path("/tmp/test"),
        src_paths=(Path("/tmp/test/src"),),
        test_paths=(Path("/tmp/test/tests"),),
    )
    assert target.name == "test-pkg"
    assert target.kind == "package"

    result = CheckResult(
        check_name="Ruff",
        target_name="test-pkg",
        status=CheckStatus.PASS,
        duration=0.12,
        details="Clean",
    )
    assert result.status == CheckStatus.PASS
    assert result.duration == 0.12

    report = SanityCheckReport(
        results=(result,),
        total_duration=0.12,
        exit_code=0,
    )
    assert report.exit_code == 0
    assert len(report.results) == 1


def test_governance_commands():
    """Verify instantiation of all governance command objects."""
    target = SanityTarget(
        name="cqrs",
        kind="package",
        path=Path("/tmp/cqrs"),
        src_paths=(Path("/tmp/cqrs/src"),),
        test_paths=(Path("/tmp/cqrs/tests"),),
    )
    repo_root = Path("/tmp/repo")

    cmd_lint = RunLinterCommand(paths=target.src_paths, target_name="cqrs", fix=True)
    assert cmd_lint.fix is True

    cmd_ty = RunTypecheckCommand(paths=target.src_paths, target_name="cqrs")
    assert cmd_ty.target_name == "cqrs"

    cmd_cpx = AuditComplexityCommand(paths=target.src_paths, target_name="cqrs", max_complexity=20)
    assert cmd_cpx.max_complexity == 20

    cmd_all = CheckAllStatementsCommand(paths=target.src_paths, target_name="cqrs")
    assert cmd_all.fix is False

    cmd_parity = CheckTestParityCommand(target=target, repo_root=repo_root)
    assert cmd_parity.target.name == "cqrs"

    cmd_diag = CheckDiagramsCommand(target=target, repo_root=repo_root, fix=True)
    assert cmd_diag.fix is True

    cmd_test = RunPytestCommand(target=target, repo_root=repo_root, skip=True)
    assert cmd_test.skip is True

    cmd_sanity = RunSanityCheckCommand(
        targets=(target,),
        repo_root=repo_root,
        fix=False,
        skip_tests=False,
        skip_diagrams=True,
        max_complexity=25,
    )
    targets_len = len(cmd_sanity.targets)
    assert targets_len == 1
    skip_diag = cmd_sanity.skip_diagrams
    assert skip_diag is True
    cmd_parallelism = cmd_sanity.parallelism
    assert cmd_parallelism >= 1


def test_resolve_default_parallelism():
    """Verify default parallelism logic calculates cores minus two, clamping to 1."""
    with patch("os.cpu_count", return_value=8):
        val_8 = resolve_default_parallelism()
        assert val_8 == 6

    with patch("os.cpu_count", return_value=4):
        val_4 = resolve_default_parallelism()
        assert val_4 == 2

    with patch("os.cpu_count", return_value=2):
        val_2 = resolve_default_parallelism()
        assert val_2 == 1

    with patch("os.cpu_count", return_value=1):
        val_1 = resolve_default_parallelism()
        assert val_1 == 1

    with patch("os.cpu_count", return_value=None):
        val_none = resolve_default_parallelism()
        assert val_none == 1


def test_resolve_parallelism():
    """Verify resolution of auto and explicit worker configurations."""
    with patch("os.cpu_count", return_value=8):
        auto_res = resolve_parallelism("auto")
        assert auto_res == 6

        none_res = resolve_parallelism(None)
        assert none_res == 6

        explicit_res = resolve_parallelism("4")
        assert explicit_res == 4

        int_res = resolve_parallelism(2)
        assert int_res == 2

        with pytest.raises(ValueError, match="out of bounds"):
            resolve_parallelism(0)

        with pytest.raises(ValueError, match="out of bounds"):
            resolve_parallelism(10)

        with pytest.raises(ValueError, match="Invalid worker count"):
            resolve_parallelism("invalid")
