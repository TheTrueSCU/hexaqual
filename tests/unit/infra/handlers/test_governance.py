"""Unit tests for governance CQRS command handlers.

Notes/Architectural Intent:
    Verifies that leaf handlers invoke their respective ToolRunnerPort methods,
    and that RunSanityCheckHandler dispatches each sub-command through the bus.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.domain.governance import (
    AuditComplexityCommand,
    CheckAllStatementsCommand,
    CheckDiagramsCommand,
    CheckResult,
    CheckStatus,
    CheckTestParityCommand,
    DiagramAuditTask,
    RunDeptryCommand,
    RunLinterCommand,
    RunPytestCommand,
    RunSanityCheckCommand,
    RunTypecheckCommand,
    SanityTarget,
)
from hexaqual.infra.dispatcher import CommandDispatcher
from hexaqual.infra.handlers.governance import (
    AuditComplexityHandler,
    CheckAllStatementsHandler,
    CheckDiagramsHandler,
    CheckTestParityHandler,
    RunDeptryHandler,
    RunLinterHandler,
    RunPytestHandler,
    RunSanityCheckHandler,
    RunTypecheckHandler,
    _audit_diagram_worker,
)
from hexaqual.ports.governance import ToolRunnerPort


def test_leaf_governance_handlers():
    """Verify each leaf handler delegates to the matching ToolRunnerPort method."""
    mock_runner = MagicMock(spec=ToolRunnerPort)
    expected_res = CheckResult("Dummy", "pkg", CheckStatus.PASS, 0.05)
    mock_runner.run_ruff.return_value = expected_res
    mock_runner.run_ty.return_value = expected_res
    mock_runner.run_complexipy.return_value = expected_res
    mock_runner.run_all_statements.return_value = expected_res
    mock_runner.run_test_parity.return_value = expected_res
    mock_runner.run_diagrams.return_value = expected_res
    mock_runner.run_deptry.return_value = expected_res
    mock_runner.run_pytest.return_value = expected_res

    target = SanityTarget("cqrs", "package", Path("/tmp"), (Path("/tmp"),), ())

    h_lint = RunLinterHandler(mock_runner)
    assert (
        h_lint.handle(RunLinterCommand(paths=(Path(),), target_name="cqrs", fix=True))
        == expected_res
    )
    mock_runner.run_ruff.assert_called_once()

    h_ty = RunTypecheckHandler(mock_runner)
    assert h_ty.handle(RunTypecheckCommand(paths=(Path(),), target_name="cqrs")) == expected_res
    mock_runner.run_ty.assert_called_once()

    h_cpx = AuditComplexityHandler(mock_runner)
    assert (
        h_cpx.handle(AuditComplexityCommand(paths=(Path(),), target_name="cqrs", max_complexity=25))
        == expected_res
    )
    mock_runner.run_complexipy.assert_called_once()

    h_all = CheckAllStatementsHandler(mock_runner)
    assert (
        h_all.handle(CheckAllStatementsCommand(paths=(Path(),), target_name="cqrs")) == expected_res
    )
    mock_runner.run_all_statements.assert_called_once()

    h_parity = CheckTestParityHandler(mock_runner)
    assert (
        h_parity.handle(CheckTestParityCommand(target=target, repo_root=Path("/tmp")))
        == expected_res
    )
    mock_runner.run_test_parity.assert_called_once()

    h_diag = CheckDiagramsHandler(mock_runner)
    assert (
        h_diag.handle(CheckDiagramsCommand(target=target, repo_root=Path("/tmp"), fix=False))
        == expected_res
    )
    mock_runner.run_diagrams.assert_called_once()

    skip_diag_res = h_diag.handle(
        CheckDiagramsCommand(target=target, repo_root=Path("/tmp"), skip=True)
    )
    assert skip_diag_res.status == CheckStatus.SKIP

    h_deptry = RunDeptryHandler(mock_runner)
    assert h_deptry.handle(RunDeptryCommand(target=target, skip=False)) == expected_res
    mock_runner.run_deptry.assert_called_once()

    h_pytest = RunPytestHandler(mock_runner)
    assert (
        h_pytest.handle(RunPytestCommand(target=target, repo_root=Path("/tmp"), skip=True))
        == expected_res
    )
    mock_runner.run_pytest.assert_called_once()


def test_run_sanity_check_handler_composite_dispatch():
    """Verify RunSanityCheckHandler dispatches sub-commands through CommandDispatcher."""
    mock_bus = MagicMock(spec=CommandDispatcher)
    pass_res = CheckResult("SubCheck", "target", CheckStatus.PASS, 0.01)
    mock_bus.dispatch.return_value = pass_res

    handler = RunSanityCheckHandler(mock_bus)
    pkg_target = SanityTarget(
        name="cqrs",
        kind="package",
        path=Path("/tmp/cqrs"),
        src_paths=(Path("/tmp/cqrs/src"),),
        test_paths=(Path("/tmp/cqrs/tests"),),
    )
    cmd = RunSanityCheckCommand(
        targets=(pkg_target,),
        repo_root=Path("/tmp"),
        fix=False,
        skip_tests=False,
        max_complexity=25,
    )

    report = handler.handle(cmd)
    assert report.exit_code == 0
    # Package target should dispatch: linter, ty, complexipy, all_statements, parity, diagrams, deptry, pytest = 8 calls
    assert mock_bus.dispatch.call_count == 8
    assert len(report.results) == 8


def test_run_sanity_check_handler_skip_flags():
    """Verify RunSanityCheckHandler honors individual and step skip flags."""
    mock_bus = MagicMock(spec=CommandDispatcher)
    pass_res = CheckResult("SubCheck", "target", CheckStatus.PASS, 0.01)
    mock_bus.dispatch.return_value = pass_res

    handler = RunSanityCheckHandler(mock_bus)
    pkg_target = SanityTarget(
        name="cqrs",
        kind="package",
        path=Path("/tmp/cqrs"),
        src_paths=(Path("/tmp/cqrs/src"),),
        test_paths=(Path("/tmp/cqrs/tests"),),
    )
    cmd = RunSanityCheckCommand(
        targets=(pkg_target,),
        repo_root=Path("/tmp"),
        skip_tests=True,
        skip_deptry=True,
        skip_typecheck=True,
        skip_complexity=True,
        skip_parity=True,
        skip_all_statements=True,
        skip_diagrams=True,
        skip_steps=("lint",),
    )
    report = handler.handle(cmd)
    assert report.exit_code == 0
    # 5 steps are skipped immediately; diagrams, deptry, and pytest are dispatched with skip=True
    assert mock_bus.dispatch.call_count == 3
    assert len(report.results) == 8


def test_run_sanity_check_handler_with_failures():
    """Verify RunSanityCheckHandler sets exit_code=1 on any check failure."""
    mock_bus = MagicMock(spec=CommandDispatcher)
    fail_res = CheckResult("Linter", "target", CheckStatus.FAIL, 0.05, "error")
    mock_bus.dispatch.return_value = fail_res

    handler = RunSanityCheckHandler(mock_bus)
    target = SanityTarget("file.py", "file", Path("file.py"), (Path("file.py"),), ())
    cmd = RunSanityCheckCommand(
        targets=(target,),
        repo_root=Path("/tmp"),
    )

    report = handler.handle(cmd)
    assert report.exit_code == 1
    assert any(r.status == CheckStatus.FAIL for r in report.results)


def test_audit_diagram_worker():
    """Verify _audit_diagram_worker executes audit_single_target_diagram."""
    target = SanityTarget("pkg1", "package", Path("/tmp/pkg1"), (Path("/tmp/pkg1/src"),), ())
    task = DiagramAuditTask(target=target, repo_root=Path("/tmp"), fix=False)
    with patch(
        "hexaqual.infra.handlers.governance.audit_single_target_diagram",
        return_value=CheckResult("Architecture Diagrams", "pkg1", CheckStatus.PASS, 0.05),
    ) as mock_audit:
        res = _audit_diagram_worker(task)
        assert res.status == CheckStatus.PASS
        assert res.target_name == "pkg1"
        mock_audit.assert_called_once_with(target, Path("/tmp"), fix=False)


def test_run_sanity_check_handler_parallel_diagrams(tmp_path: Path):
    """Verify parallel diagram execution precomputes results for multiple packages."""
    pydeps_dir = tmp_path / "docs" / "assets" / "pydeps"
    pydeps_dir.mkdir(parents=True)

    t1 = SanityTarget("p1", "package", tmp_path / "p1", (tmp_path / "p1/src",), ())
    t2 = SanityTarget("p2", "package", tmp_path / "p2", (tmp_path / "p2/src",), ())

    mock_bus = MagicMock(spec=CommandDispatcher)
    pass_res = CheckResult("SubCheck", "target", CheckStatus.PASS, 0.01)
    mock_bus.dispatch.return_value = pass_res

    handler = RunSanityCheckHandler(mock_bus)
    cmd = RunSanityCheckCommand(
        targets=(t1, t2),
        repo_root=tmp_path,
        skip_tests=True,
        skip_deptry=True,
        skip_typecheck=True,
        skip_complexity=True,
        skip_parity=True,
        skip_all_statements=True,
        skip_steps=("lint",),
    )

    with (
        patch("shutil.which", return_value="/usr/bin/dot"),
        patch(
            "hexaqual.infra.handlers.governance.audit_single_target_diagram",
            side_effect=[
                CheckResult("Architecture Diagrams", "p1", CheckStatus.PASS, 0.02),
                CheckResult("Architecture Diagrams", "p2", CheckStatus.PASS, 0.03),
            ],
        ),
    ):
        report = handler.handle(cmd)
        exit_code = report.exit_code
        assert exit_code == 0
        diagram_calls = [
            c
            for c in mock_bus.dispatch.call_args_list
            if isinstance(c.args[0], CheckDiagramsCommand)
        ]
        num_diagram_calls = len(diagram_calls)
        assert num_diagram_calls == 2
        p1_cmd = diagram_calls[0].args[0]
        assert p1_cmd.precomputed_result is not None
        assert p1_cmd.precomputed_result.target_name == "p1"
