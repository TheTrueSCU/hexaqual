"""Pytest test runner and architecture contract generator commands."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from hexaqual.adapters.workspace import (
    get_example_directory,
    get_git_changed_files,
    get_package_directories,
    get_package_directory,
    get_repo_root,
    resolve_affected_packages,
)


def _get_git_changed_files(base_ref: str = "origin/main") -> list[str]:
    """Retrieve list of modified files compared against git base_ref."""
    return get_git_changed_files(base_ref=base_ref)


def _setup_example_target(example_name: str, sub_dir: str, root: Path) -> str:
    """Configure sys.path and PYTHONPATH for an example and return its test directory path."""
    ex_dir = get_example_directory(example_name, root)
    src_dir = ex_dir / "src"
    if src_dir.is_dir():
        src_path_str = str(src_dir.resolve())
        if src_path_str not in sys.path:
            sys.path.insert(0, src_path_str)
        current_pypath = os.environ.get("PYTHONPATH", "")
        if src_path_str not in current_pypath.split(os.pathsep):
            os.environ["PYTHONPATH"] = (
                f"{src_path_str}{os.pathsep}{current_pypath}" if current_pypath else src_path_str
            )
    target = ex_dir / sub_dir
    if target.is_dir():
        return str(target)
    if (ex_dir / "tests").is_dir():
        return str(ex_dir / "tests")
    return str(ex_dir)


def _is_pytest_benchmark_installed() -> bool:
    """Check if pytest-benchmark plugin is installed in current Python environment."""
    try:
        import pytest_benchmark  # noqa: F401

        return True
    except ImportError:
        return False


def _pkg_test_path(pkg_dir: Path, sub_dir: str) -> str:
    """Resolve sub-directory path for package tests, falling back to tests if needed."""
    if (pkg_dir / sub_dir).is_dir():
        return str(pkg_dir / sub_dir)
    if sub_dir == "tests/benchmarks" and (pkg_dir / "tests").is_dir():
        return str(pkg_dir / "tests")
    return str(pkg_dir / sub_dir)


def _resolve_package_targets(
    packages: list[str] | None,
    affected: bool,
    sub_dir: str,
    root: Path,
) -> tuple[list[str], set[str] | None]:
    """Resolve target test directory paths for workspace packages."""
    if packages:
        paths = [_pkg_test_path(get_package_directory(p, root), sub_dir) for p in packages]
        return paths, set(packages)

    if affected:
        changed = _get_git_changed_files()
        affected_pkgs = resolve_affected_packages(changed, root)
        if affected_pkgs is not None:
            paths = [_pkg_test_path(get_package_directory(p, root), sub_dir) for p in affected_pkgs]
            return paths, affected_pkgs

    paths = [
        _pkg_test_path(pkg_dir, sub_dir)
        for pkg_dir in get_package_directories(root)
        if (pkg_dir / "tests").is_dir()
    ]
    return paths, None


def _resolve_test_targets(
    packages: list[str] | None,
    examples: list[str] | None,
    affected: bool,
    unit_only: bool,
    properties_only: bool,
    benchmark_only: bool,
    root: Path,
) -> tuple[list[str], set[str] | None]:
    """Resolve target test directory paths and active package set based on CLI flags."""
    if benchmark_only:
        sub_dir = "tests/benchmarks"
    elif properties_only:
        sub_dir = "tests/properties"
    elif unit_only:
        sub_dir = "tests/unit"
    else:
        sub_dir = "tests"

    if examples:
        paths = [_setup_example_target(e, sub_dir, root) for e in examples]
        return paths, None

    return _resolve_package_targets(packages, affected, sub_dir, root)


def _build_coverage_args(
    args: argparse.Namespace,
    active_pkgs: set[str] | None,
    root: Path,
) -> list[str]:
    """Construct coverage scoping and context arguments for pytest."""
    cov_args: list[str] = []
    if args.with_context:
        cov_args.extend(["-n", "0", "--cov-context=test"])

    if getattr(args, "benchmark", False) or args.examples:
        cov_args.append("--no-cov")
    elif active_pkgs is not None:
        cov_pkgs = [
            p
            for p in active_pkgs
            if p != "tools" and (get_package_directory(p, root) / "src").is_dir()
        ]
        if cov_pkgs:
            cov_args.append("--cov-reset")
            for p in cov_pkgs:
                pkg_src = get_package_directory(p, root) / "src"
                cov_args.append(f"--cov={pkg_src}")
        else:
            cov_args.append("--no-cov")
    return cov_args


def _build_benchmark_options(args: argparse.Namespace) -> list[str]:
    """Construct specific benchmark execution options."""
    opts: list[str] = []
    if getattr(args, "smoke", False):
        opts.append("--benchmark-disable")
    else:
        opts.append("--benchmark-only")
    if save := getattr(args, "benchmark_save", None):
        opts.append(f"--benchmark-save={save}")
    if getattr(args, "benchmark_compare", False):
        opts.append("--benchmark-compare")
    if json_path := getattr(args, "benchmark_json", None):
        opts.append(f"--benchmark-json={json_path}")
    if min_rounds := getattr(args, "benchmark_min_rounds", None):
        opts.append(f"--benchmark-min-rounds={min_rounds}")
    return opts


def _build_benchmark_args(args: argparse.Namespace, unknown: list[str]) -> list[str]:
    """Construct pytest-benchmark specific arguments based on parsed CLI flags."""
    if getattr(args, "benchmark", False):
        if not _is_pytest_benchmark_installed():
            print(
                "❌ [Benchmark Error] pytest-benchmark is not installed. "
                "Install with 'uv add --dev pytest-benchmark' or 'pip install hexaqual[bench]'.",
                file=sys.stderr,
            )
            sys.exit(1)
        return _build_benchmark_options(args)

    has_bench_unknown = any(arg.startswith("--benchmark-") for arg in unknown)
    if not has_bench_unknown and _is_pytest_benchmark_installed():
        return ["--benchmark-skip"]
    return []


def run_main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for pytest-run."""
    parser = argparse.ArgumentParser(description="Run pytest test suite.")
    parser.add_argument(
        "-p", "--package", dest="packages", action="append", help="Target package name."
    )
    parser.add_argument(
        "-e", "--example", dest="examples", action="append", help="Target example project."
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="all_packages",
        action="store_true",
        help="Run across all workspace packages.",
    )
    parser.add_argument("-A", "--affected", action="store_true")
    parser.add_argument("-U", "--unit", action="store_true")
    parser.add_argument("-P", "--properties", action="store_true")
    parser.add_argument(
        "--with-context",
        action="store_true",
        help="Capture test function contexts in .coverage for Test Impact Analysis and boundary audits (disables xdist).",
    )
    parser.add_argument(
        "--cluster",
        default="local",
        help="Execution target cluster ('local' or 'hexaqueue').",
    )
    parser.add_argument(
        "--cluster-url",
        default=os.environ.get("HEXAQUEUE_URL", "http://localhost:8000"),
        help="Hexaqueue cluster REST endpoint URL.",
    )
    parser.add_argument(
        "--cluster-token",
        default=os.environ.get("HEXAQUEUE_TOKEN"),
        help="Authentication bearer token for Hexaqueue cluster.",
    )
    parser.add_argument(
        "--cluster-user",
        default=os.environ.get("HEXAQUEUE_USER", "default"),
        help="Submitting user identity for Hexaqueue cluster.",
    )
    parser.add_argument(
        "--cluster-elevate",
        action="store_true",
        help="Assert administrative elevation on Hexaqueue cluster.",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Permit test runs where zero tests are collected or executed (exercise gate override).",
    )
    parser.add_argument(
        "-B",
        "--bench",
        "--benchmark",
        dest="benchmark",
        action="store_true",
        help="Run benchmark suite using pytest-benchmark with zero coverage overhead.",
    )
    parser.add_argument(
        "--benchmark-save",
        dest="benchmark_save",
        help="Save benchmark results with given name tag under .benchmarks/.",
    )
    parser.add_argument(
        "--benchmark-compare",
        dest="benchmark_compare",
        action="store_true",
        help="Compare against latest saved benchmark baseline.",
    )
    parser.add_argument(
        "--benchmark-json",
        dest="benchmark_json",
        help="Export benchmark results to JSON file path.",
    )
    parser.add_argument(
        "--benchmark-min-rounds",
        dest="benchmark_min_rounds",
        type=int,
        help="Minimum number of benchmark rounds per test.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke mode: disable measurement cycles and run each benchmark once.",
    )
    args, unknown = parser.parse_known_args(argv)

    root = get_repo_root()
    test_paths, active_pkgs = _resolve_test_targets(
        packages=args.packages,
        examples=args.examples,
        affected=args.affected,
        unit_only=args.unit,
        properties_only=args.properties,
        benchmark_only=args.benchmark,
        root=root,
    )

    cov_args = _build_coverage_args(args=args, active_pkgs=active_pkgs, root=root)
    bench_args = _build_benchmark_args(args=args, unknown=unknown or [])
    call_args = test_paths + cov_args + bench_args + (unknown or [])

    if getattr(args, "cluster", "local").lower() == "hexaqueue":
        from hexaqual.adapters.runners.hexaqueue_cluster import HexaqueueClusterRunnerAdapter

        cluster_runner = HexaqueueClusterRunnerAdapter(
            cluster_url=args.cluster_url,
            user_id=args.cluster_user,
            elevate=args.cluster_elevate,
            token=args.cluster_token,
        )
        returncode = cluster_runner.execute_pytest(test_nodes=call_args, cwd=root)
        if argv is None:
            sys.exit(returncode)
        return returncode

    res = subprocess.run([sys.executable, "-m", "pytest", *call_args])
    returncode = res.returncode
    if returncode == 5:
        if args.allow_empty:
            returncode = 0
        else:
            print(
                "❌ [Exercise Gate] Refused test run with 0 executed tests. "
                "A check that refuses zero activity prevents misleading green passes "
                "(use --allow-empty if intentional).",
                file=sys.stderr,
            )
            returncode = 1
    if argv is None:
        sys.exit(returncode)
    return returncode


__all__ = [
    "run_main",
]
