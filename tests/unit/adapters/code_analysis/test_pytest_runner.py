"""Unit tests for pytest runner commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.adapters.code_analysis.pytest_runner import (
    run_main,
)


def test_pytest_runner_callables() -> None:
    """Verify pytest runner callables."""
    assert callable(run_main)


@patch("subprocess.run", return_value=MagicMock(returncode=0))
@patch("sys.exit")
@patch("sys.argv", ["pytest-run", "--with-context", "-p", "core"])
def test_run_main_with_context(
    mock_exit: MagicMock, mock_subproc: MagicMock, tmp_path: Path
) -> None:
    """Verify run_main forwards -n 0 and --cov-context=test when --with-context is enabled."""
    with patch(
        "hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        pkg_dir = tmp_path / "packages" / "hexastack_core"
        (pkg_dir / "src").mkdir(parents=True)
        (pkg_dir / "tests").mkdir(parents=True)
        run_main()
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert "-n" in cmd_args
        assert "0" in cmd_args
        assert "--cov-context=test" in cmd_args


@patch("subprocess.run", return_value=MagicMock(returncode=0))
@patch("sys.exit")
@patch("sys.argv", ["pytest-run", "-e", "financial-ledger"])
def test_run_main_with_example(
    mock_exit: MagicMock, mock_subproc: MagicMock, tmp_path: Path
) -> None:
    """Verify run_main resolves example test path and adds src to sys.path."""
    with patch(
        "hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        ex_dir = tmp_path / "examples" / "financial-ledger"
        (ex_dir / "src" / "financial_ledger").mkdir(parents=True)
        (ex_dir / "tests").mkdir(parents=True)
        run_main()
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert str(ex_dir / "tests") in cmd_args
        assert "--no-cov" in cmd_args


@patch("subprocess.run", return_value=MagicMock(returncode=0))
@patch("sys.exit")
@patch(
    "hexaqual.adapters.code_analysis.pytest_runner._get_git_changed_files",
    return_value=["packages/hexastack_core/src/hexastack_core/models.py"],
)
@patch("sys.argv", ["pytest-run", "-A", "-U"])
def test_run_main_with_affected(
    mock_git: MagicMock, mock_exit: MagicMock, mock_subproc: MagicMock, tmp_path: Path
) -> None:
    """Verify run_main resolves affected package test path when -A is passed."""
    with patch(
        "hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path
    ):
        pkg_dir = tmp_path / "packages" / "hexastack_core"
        (pkg_dir / "src" / "hexastack_core").mkdir(parents=True)
        (pkg_dir / "tests" / "unit").mkdir(parents=True)
        (pkg_dir / "pyproject.toml").write_text("[project]\nname = 'hexastack-core'\n")
        run_main()
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert str(pkg_dir / "tests" / "unit") in cmd_args
        assert "--cov-reset" in cmd_args


def test_run_main_exercise_gate_refuses_zero_tests(tmp_path: Path) -> None:
    """Verify run_main intercepts pytest exit code 5 (0 tests collected) and refuses."""
    with (
        patch("hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path),
        patch("subprocess.run", return_value=MagicMock(returncode=5)),
    ):
        code = run_main([])
        assert code == 1


def test_run_main_exercise_gate_allows_empty_override(tmp_path: Path) -> None:
    """Verify run_main allows 0 tests when --allow-empty is explicitly set."""
    with (
        patch("hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path),
        patch("subprocess.run", return_value=MagicMock(returncode=5)),
    ):
        code = run_main(["--allow-empty"])
        assert code == 0


def test_run_main_with_bench_flags(tmp_path: Path) -> None:
    """Verify run_main applies --no-cov and benchmark options when --bench is enabled."""
    pkg_dir = tmp_path / "packages" / "hexastack_cqrs"
    (pkg_dir / "src" / "hexastack_cqrs").mkdir(parents=True)
    (pkg_dir / "tests" / "benchmarks").mkdir(parents=True)

    with (
        patch("hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path),
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_subproc,
        patch(
            "hexaqual.adapters.code_analysis.pytest_runner._is_pytest_benchmark_installed",
            return_value=True,
        ),
    ):
        code = run_main(
            [
                "-B",
                "-p",
                "cqrs",
                "--benchmark-save=v1",
                "--benchmark-compare",
                "--benchmark-json=bench.json",
                "--benchmark-min-rounds=20",
            ]
        )
        assert code == 0
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert str(pkg_dir / "tests" / "benchmarks") in cmd_args
        assert "--no-cov" in cmd_args
        assert "--benchmark-only" in cmd_args
        assert "--benchmark-save=v1" in cmd_args
        assert "--benchmark-compare" in cmd_args
        assert "--benchmark-json=bench.json" in cmd_args
        assert "--benchmark-min-rounds=20" in cmd_args


def test_run_main_with_bench_smoke_mode(tmp_path: Path) -> None:
    """Verify run_main applies --benchmark-disable in smoke mode."""
    pkg_dir = tmp_path / "packages" / "hexastack_cqrs"
    (pkg_dir / "src" / "hexastack_cqrs").mkdir(parents=True)
    (pkg_dir / "tests" / "benchmarks").mkdir(parents=True)

    with (
        patch("hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path),
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_subproc,
        patch(
            "hexaqual.adapters.code_analysis.pytest_runner._is_pytest_benchmark_installed",
            return_value=True,
        ),
    ):
        code = run_main(["--bench", "-p", "cqrs", "--smoke"])
        assert code == 0
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert "--no-cov" in cmd_args
        assert "--benchmark-disable" in cmd_args


def test_run_main_skips_benchmark_on_normal_run(tmp_path: Path) -> None:
    """Verify run_main injects --benchmark-skip when pytest-benchmark is installed on normal run."""
    pkg_dir = tmp_path / "packages" / "hexastack_core"
    (pkg_dir / "src" / "hexastack_core").mkdir(parents=True)
    (pkg_dir / "tests" / "unit").mkdir(parents=True)

    with (
        patch("hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path),
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_subproc,
        patch(
            "hexaqual.adapters.code_analysis.pytest_runner._is_pytest_benchmark_installed",
            return_value=True,
        ),
    ):
        code = run_main(["-p", "core", "-U"])
        assert code == 0
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        assert "--benchmark-skip" in cmd_args


def test_run_main_bench_not_installed(tmp_path: Path) -> None:
    """Verify run_main exits with error if --bench requested but plugin missing."""
    with (
        patch("hexaqual.adapters.code_analysis.pytest_runner.get_repo_root", return_value=tmp_path),
        patch(
            "hexaqual.adapters.code_analysis.pytest_runner._is_pytest_benchmark_installed",
            return_value=False,
        ),
        patch("sys.exit") as mock_exit,
    ):
        run_main(["--bench"])
        mock_exit.assert_called_once_with(1)
