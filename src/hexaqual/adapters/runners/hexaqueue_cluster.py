"""Hexaqueue cluster execution adapter for distributed test and mutation runs.

Notes/Architectural Intent:
    Encapsulates remote job submission, Server-Sent Events (SSE) telemetry streaming,
    and log ingestion against a remote Hexaqueue batch cluster via HTTP/SSE.
    Implements TestingRunnerPort by translating local pytest/gremlins invocations into
    Hexaqueue JobSpec DAGs while delegating local file inspection and git diff
    analysis to a local TestingRunnerPort delegate.
"""

from __future__ import annotations

import ast
import contextlib
import json
import logging
import math
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from rich.console import Console

from hexaqual.adapters.runners.testing_runner import SubprocessTestingRunnerAdapter
from hexaqual.domain.imports import optional_dependency
from hexaqual.domain.testing import MutationEngine
from hexaqual.ports.testing import TestingRunnerPort

logger = logging.getLogger(__name__)

DEFAULT_MAX_CLUSTER_SLICES = 16
DEFAULT_MAX_SLICE_WEIGHT = 450
_HEAVY_MUTABLE_NODES = (ast.BinOp, ast.Compare, ast.BoolOp, ast.AugAssign)
_LIGHT_MUTABLE_NODES = (ast.UnaryOp, ast.If, ast.IfExp, ast.While, ast.Return)
_PER_FILE_OVERHEAD = 5


def _estimate_file_mutation_weight(path: Path) -> int:
    """Estimate mutation workload weight of a Python source file via AST analysis."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return _PER_FILE_OVERHEAD
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return max(1, len(source.splitlines()))

    doc_ids: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.body
        ):
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                doc_ids.add(id(first.value))

    weight = _PER_FILE_OVERHEAD
    for node in ast.walk(tree):
        if id(node) in doc_ids:
            continue
        if isinstance(node, _HEAVY_MUTABLE_NODES):
            weight += 3
        elif isinstance(node, _LIGHT_MUTABLE_NODES) or (
            isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool))
        ):
            weight += 1
    return weight


def _pack_weighted_buckets(
    items: list[tuple[int, str]],
    bucket_count: int,
) -> list[tuple[int, list[str]]]:
    """Pack sorted ``(weight, target)`` pairs into ``bucket_count`` LPT buckets."""
    buckets: list[tuple[int, list[str]]] = [(0, []) for _ in range(bucket_count)]
    for weight, target in items:
        min_idx = min(range(bucket_count), key=lambda idx: buckets[idx][0])
        cur_weight, cur_paths = buckets[min_idx]
        cur_paths.append(target)
        buckets[min_idx] = (cur_weight + weight, cur_paths)
    return [(w, sorted(paths)) for w, paths in buckets if paths]


def _partition_targets_lpt(
    weighted_items: Sequence[tuple[int, str]],
    *,
    min_slices: int = 1,
    max_slices: int = DEFAULT_MAX_CLUSTER_SLICES,
    max_slice_weight: int | None = DEFAULT_MAX_SLICE_WEIGHT,
) -> list[tuple[int, list[str]]]:
    """Partition weighted targets into capacity-capped LPT slices ordered heaviest-first."""
    if not weighted_items:
        return []
    ordered = sorted(weighted_items, key=lambda item: (-item[0], item[1]))
    clamped_max = max(1, max_slices)
    clamped_min = min(max(1, min_slices), clamped_max, len(ordered))

    if max_slice_weight is None or max_slice_weight <= 0:
        packed = _pack_weighted_buckets(ordered, clamped_min)
        packed.sort(key=lambda item: (-item[0], item[1][0]))
        return packed

    solo_limit = clamped_max - 1 if len(ordered) > clamped_max else clamped_max
    solo: list[tuple[int, str]] = []
    rest: list[tuple[int, str]] = []
    for item in ordered:
        if item[0] >= max_slice_weight and len(solo) < solo_limit:
            solo.append(item)
        else:
            rest.append(item)

    slices: list[tuple[int, list[str]]] = [(w, [p]) for w, p in solo]
    if rest:
        remaining_slots = max(1, clamped_max - len(solo))
        rest_total = sum(w for w, _ in rest)
        min_rest_buckets = max(1, clamped_min - len(solo))
        needed_buckets = max(min_rest_buckets, math.ceil(rest_total / max_slice_weight))
        bucket_count = min(len(rest), remaining_slots, needed_buckets)
        slices.extend(_pack_weighted_buckets(rest, bucket_count))

    slices.sort(key=lambda item: (-item[0], item[1][0]))
    return slices


__all__ = [
    "HexaqueueClusterRunnerAdapter",
]


def _is_pytest_hexaqueue_installed() -> bool:
    """Check if pytest-hexaqueue plugin is installed in current Python environment."""
    return optional_dependency("pytest_hexaqueue") is not None


class HexaqueueClusterRunnerAdapter(TestingRunnerPort):
    """Remote runner adapter submitting test and mutation workloads to a Hexaqueue cluster."""

    def __init__(
        self,
        cluster_url: str = "http://localhost:8000",
        user_id: str = "default",
        elevate: bool = False,
        token: str | None = None,
        poll_interval: float = 0.5,
        timeout: float | None = None,
        base_runner: TestingRunnerPort | None = None,
        console: Console | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Initialize Hexaqueue cluster runner adapter.

        Args:
            cluster_url: Base HTTP URL of Hexaqueue Server (e.g. 'http://localhost:8000').
            user_id: Submitting user account or identity.
            elevate: Whether to request administrative elevation.
            token: Optional bearer token for authenticated cluster access.
            poll_interval: Interval in seconds between SSE pulses or polling checks.
            timeout: Maximum overall timeout in seconds for remote job execution (defaults to env HEXAQUEUE_TIMEOUT or 1800.0s).
            base_runner: Optional local delegate for static inspection and git diffs.
            console: Optional Rich Console for progress reporting.
            http_client: Optional preconfigured httpx.Client (e.g. for testing with MockTransport).

        Notes/Architectural Intent:
            Decouples test execution and mutation crunching from local compute by dispatching
            workloads over HTTP/SSE. Delegates local tasks (git diff extraction, coverage file
            reading) to an underlying base runner.
        """
        self._cluster_url = cluster_url.rstrip("/")
        self._user_id = user_id
        self._elevate = elevate
        self._token = token
        self._poll_interval = poll_interval
        if timeout is not None:
            self._timeout = timeout
        else:
            env_timeout = os.environ.get("HEXAQUEUE_TIMEOUT")
            self._timeout = float(env_timeout) if env_timeout else 1800.0
        self._base_runner = base_runner or SubprocessTestingRunnerAdapter()
        self._console = console or Console()
        self._err_console = console if console is not None else Console(stderr=True)
        self._client = http_client
        self._heartbeat_interval = 30.0
        self._last_status_snapshot: tuple[Any, int, int, int, int] | None = None
        self._last_print_time: float = 0.0
        self._validate_security()

    def _validate_security(self) -> None:
        """Enforce TLS for remote credential transmission (CWE-319)."""
        if not self._token:
            return
        parsed = urllib.parse.urlsplit(self._cluster_url)
        hostname = (parsed.hostname or "").lower()
        is_local = hostname in (
            "localhost",
            "127.0.0.1",
            "::1",
            "testcluster",
            "local-cluster",
        )
        if parsed.scheme.lower() == "http" and not is_local:
            raise ValueError(
                f"Insecure transport: Bearer token cannot be transmitted over unencrypted HTTP ({self._cluster_url}). "
                "Use HTTPS for remote cluster authentication."
            )

    def _get_headers(self) -> dict[str, str]:
        """Construct HTTP request headers for Hexaqueue REST API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Hexaqueue-User": self._user_id,
            "X-Hexaqueue-Elevate": "true" if self._elevate else "false",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _build_client(self) -> httpx.Client:
        """Create or return an active HTTP client instance."""
        if self._client is not None:
            return self._client
        return httpx.Client(
            base_url=self._cluster_url,
            headers=self._get_headers(),
            timeout=self._timeout,
        )

    def _find_repo_root(self, start_dir: Path) -> Path:
        """Find the enclosing git repository root directory."""
        current = start_dir.resolve()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return start_dir.resolve()

    def _stage_workspace_collateral(self, client: httpx.Client, workspace_dir: Path) -> str | None:
        """Stage repository workspace into cluster CAS and return registered collateral ID.

        Args:
            client: HTTP client connected to Hexaqueue server.
            workspace_dir: Package or repository directory to package.

        Returns:
            Registered CAS collateral bundle ID, or None if archiver is unavailable.
        """
        archiver_mod = optional_dependency("pytest_hexaqueue.adapters.git_archiver")
        if archiver_mod is None:
            return None

        repo_root = self._find_repo_root(workspace_dir)
        try:
            archiver = archiver_mod.GitWorkspaceArchiver()
            archive_bytes, sha256 = archiver.archive_workspace(repo_root)
        except Exception as exc:
            logger.debug("Failed to package workspace archive: %s", exc)
            return None

        clean_sha = sha256.strip().lower()
        try:
            resp = client.get(
                f"{self._cluster_url}/api/v1/collateral/checksum/{clean_sha}",
                headers=self._get_headers(),
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    cid = data.get("id") or (data.get("bundle", {}) or {}).get("id")
                    if cid:
                        return str(cid)
        except Exception as exc:
            logger.debug("CAS cache check failed (%s), proceeding to stage", exc)

        stage_headers = dict(self._get_headers())
        stage_headers["Content-Type"] = "application/octet-stream"
        stage_headers["X-Collateral-Name"] = f"{repo_root.name}.tar.gz"
        stage_headers["X-Collateral-SHA256"] = clean_sha

        try:
            resp = client.post(
                f"{self._cluster_url}/api/v1/collateral/stage",
                content=archive_bytes,
                headers=stage_headers,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                if isinstance(data, dict):
                    cid = data.get("id") or (data.get("bundle", {}) or {}).get("id")
                    if cid:
                        return str(cid)
        except Exception as exc:
            logger.warning("Failed to stage workspace collateral to cluster: %s", exc)

        return None

    def _collect_mutation_targets(self, package_dir: Path) -> list[str]:
        """Discover candidate Python source files within package directory.

        Args:
            package_dir: Base package directory.

        Returns:
            List of relative source file paths.
        """
        src_dir = package_dir / "src"
        search_root = src_dir if src_dir.is_dir() else package_dir
        targets: list[str] = []
        for py_file in sorted(search_root.rglob("*.py")):
            if "__pycache__" in py_file.parts or py_file.name == "__init__.py":
                continue
            try:
                rel = py_file.relative_to(package_dir)
                targets.append(str(rel))
            except ValueError:
                targets.append(py_file.name)
        return targets

    def _partition_targets(
        self,
        targets: list[str],
        slice_count: int,
        *,
        package_dir: Path | None = None,
        max_slice_weight: int | None = None,
        max_slices: int | None = None,
    ) -> list[list[str]]:
        """Partition target file list into AST-weighted LPT slice groups.

        Args:
            targets: List of relative file paths.
            slice_count: Minimum number of slice groups (bounded by file count).
            package_dir: Optional package directory used to compute AST mutation
                weights for each target file on disk.
            max_slice_weight: Optional per-slice AST weight cap enabling
                heavy-file isolation and dynamic slice expansion.
            max_slices: Upper bound on slices when capacity-capped expansion is
                active (defaults to ``max(slice_count, DEFAULT_MAX_CLUSTER_SLICES)``).

        Returns:
            List of partitioned file lists ordered heaviest-first (LPT).
        """
        if not targets:
            return [[]]
        if slice_count <= 1 and max_slice_weight is None:
            return [targets]

        weighted = [
            (
                _estimate_file_mutation_weight(package_dir / target)
                if package_dir is not None
                else 1,
                target,
            )
            for target in targets
        ]
        upper_bound = (
            max(slice_count, max_slices)
            if max_slices is not None
            else max(slice_count, DEFAULT_MAX_CLUSTER_SLICES)
        )
        packed = _partition_targets_lpt(
            weighted,
            min_slices=max(1, slice_count),
            max_slices=upper_bound,
            max_slice_weight=max_slice_weight,
        )
        return [paths for _weight, paths in packed] or [[]]

    def _build_mutation_job_specs(
        self,
        run_id: str,
        package_dir: Path,
        repo_root: Path,
        collateral_id: str | None,
        engine: MutationEngine,
        reset_cache: bool,
        workers: int | str | None,
        numprocesses: int | str | None,
        batch_size: int | None,
        report_file: Path | None,
        targets: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Construct constituent JobSpecs for mutation testing across worker slots.

        Args:
            run_id: Parent run identifier.
            package_dir: Directory path of package to mutate.
            repo_root: Enclosing repository root.
            collateral_id: Optional CAS collateral bundle ID.
            engine: Mutation engine to use.
            reset_cache: Whether to clear incremental analysis cache.
            workers: Number of mutation workers.
            numprocesses: Baseline test worker count.
            batch_size: Gremlins per worker batch.
            report_file: Path to write the JSON report.

        Returns:
            List of JobSpec dictionaries.
        """
        try:
            rel_cwd = package_dir.relative_to(repo_root)
        except ValueError:
            rel_cwd = package_dir.resolve()

        resolved_targets: list[str] = []
        min_slices = 1
        max_slice_weight: int | None = None
        if engine == MutationEngine.GREMLINS or str(engine).lower() == "gremlins":
            resolved_targets = (
                [t.strip() for t in targets if t.strip()]
                if targets
                else self._collect_mutation_targets(package_dir)
            )
            max_slice_weight = DEFAULT_MAX_SLICE_WEIGHT
            if isinstance(workers, int) and workers > 1:
                min_slices = workers
            elif workers == "auto" or workers is None:
                min_slices = 1

        target_groups = self._partition_targets(
            resolved_targets,
            min_slices,
            package_dir=package_dir,
            max_slice_weight=max_slice_weight,
            max_slices=max(min_slices, DEFAULT_MAX_CLUSTER_SLICES),
        )
        job_specs: list[dict[str, Any]] = []

        for idx, group in enumerate(target_groups):
            cmd, args = self._build_mutation_command(
                package_dir=package_dir,
                engine=engine,
                reset_cache=reset_cache and idx == 0,
                workers=workers,
                numprocesses=numprocesses,
                batch_size=batch_size,
                report_file=report_file,
                target_files=group if group else None,
            )

            job_spec: dict[str, Any] = {
                "id": f"job-{run_id}-{package_dir.name}-{idx}",
                "run_id": run_id,
                "name": f"mutation-{package_dir.name}-batch-{idx}",
                "command": cmd,
                "args": args,
                "env": {
                    "PYTHONUNBUFFERED": "1",
                    "HEXAQUEUE_CWD": str(rel_cwd),
                },
                "resources": {"cpus": 2, "ram_mb": 2048},
                "tags": [
                    f"package:{package_dir.name}",
                    f"owner:{self._user_id}",
                    "type:mutation",
                ],
                "user": self._user_id,
            }
            if collateral_id:
                job_spec["collateral_ids"] = [collateral_id]
            job_specs.append(job_spec)

        return job_specs

    def run_mutation_testing(
        self,
        package_dir: Path | Sequence[Path],
        engine: MutationEngine = MutationEngine.GREMLINS,
        reset_cache: bool = False,
        workers: int | str | None = None,
        numprocesses: int | str | None = None,
        batch_size: int | None = None,
        report_file: Path | None = None,
        targets: Sequence[str] | None = None,
    ) -> int:
        """Run mutation testing on a remote Hexaqueue cluster.

        Args:
            package_dir: Directory path or sequence of package directories to mutate.
            engine: Mutation engine to use (e.g. GREMLINS or MUTMUT).
            reset_cache: Whether to clear incremental analysis cache.
            workers: Number of mutation workers (or 'auto') during mutation phase.
            numprocesses: Pytest-xdist worker count for baseline test execution.
            batch_size: Number of gremlins per worker batch.
            report_file: Path to write the JSON report.

        Returns:
            Exit code of remote mutation testing process (0 for success, non-zero on failure).

        Raises:
            httpx.HTTPError: If network communication with Hexaqueue cluster fails critically.

        Notes/Architectural Intent:
            Converts local mutation flags into a Hexaqueue JobSpec DAG, submits it to
            POST /v1/runs, streams progress via SSE (or polling fallback), and maps
            cluster RunOutcome to process returncode. Supports scheduling multiple packages
            within a single unified run DAG to maximize cluster worker utilization.
        """
        pkg_list = [package_dir] if isinstance(package_dir, Path) else list(package_dir)

        if not pkg_list:
            return 0

        client = self._build_client()
        first_pkg = pkg_list[0]
        repo_root = self._find_repo_root(first_pkg)
        collateral_id = self._stage_workspace_collateral(client, first_pkg)

        if len(pkg_list) == 1:
            run_id = f"mut-{first_pkg.name}-{uuid4().hex[:8]}"
            run_name = f"Mutation Testing [{first_pkg.name}]"
            tags = [f"package:{first_pkg.name}", "type:mutation"]
        else:
            run_id = f"mut-multi-{uuid4().hex[:8]}"
            run_name = f"Mutation Testing [{len(pkg_list)} packages]"
            tags = ["type:mutation", *(f"package:{p.name}" for p in pkg_list)]

        all_job_specs: list[dict[str, Any]] = []
        for pkg in pkg_list:
            job_specs = self._build_mutation_job_specs(
                run_id=run_id,
                package_dir=pkg,
                repo_root=repo_root,
                collateral_id=collateral_id,
                engine=engine,
                reset_cache=reset_cache,
                workers=workers,
                numprocesses=numprocesses,
                batch_size=batch_size,
                report_file=report_file,
                targets=targets,
            )
            all_job_specs.extend(job_specs)

        submission_payload = {
            "run_spec": {
                "id": run_id,
                "name": run_name,
                "tags": tags,
            },
            "jobs": all_job_specs,
            "dependencies": {},
            "user_id": self._user_id,
            "elevate": self._elevate,
        }

        return self._submit_and_stream(run_id=run_id, payload=submission_payload)

    def execute_pytest(
        self,
        test_nodes: list[str],
        extra_args: list[str] | None = None,
        cwd: Path | None = None,
    ) -> int:
        """Run pytest with specific test node IDs on the remote cluster.

        Args:
            test_nodes: List of pytest test node ID targets.
            extra_args: Extra CLI arguments passed to pytest.
            cwd: Optional working directory for pytest execution.

        Returns:
            Exit code of pytest execution.

        Raises:
            httpx.HTTPError: If cluster communication fails.

        Notes/Architectural Intent:
            Dispatches targeted test subsets to the Hexaqueue cluster, monitors execution,
            and returns the resulting outcome code.
        """
        pkg_name = cwd.name if cwd else "workspace"
        run_id = f"test-{pkg_name}-{uuid4().hex[:8]}"
        all_args = list(test_nodes)
        if extra_args:
            all_args.extend(extra_args)

        if self._client is None and _is_pytest_hexaqueue_installed():
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                *all_args,
                "--hexaqueue",
                "--hq-server",
                self._cluster_url,
            ]
            if self._token:
                cmd.extend(["--hq-token", self._token])
            res = subprocess.run(cmd, cwd=cwd)
            return res.returncode

        client = self._build_client()
        target_dir = cwd.resolve() if cwd else Path.cwd().resolve()
        repo_root = self._find_repo_root(target_dir)
        collateral_id = self._stage_workspace_collateral(client, target_dir)
        try:
            rel_cwd = target_dir.relative_to(repo_root)
        except ValueError:
            rel_cwd = target_dir

        job_spec: dict[str, Any] = {
            "id": f"job-{run_id}-0",
            "run_id": run_id,
            "name": f"pytest-{pkg_name}",
            "command": "pytest",
            "args": all_args,
            "env": {
                "PYTHONUNBUFFERED": "1",
                "HEXAQUEUE_CWD": str(rel_cwd),
            },
            "resources": {"cpus": 2, "ram_mb": 2048},
            "tags": [f"package:{pkg_name}", f"owner:{self._user_id}", "type:test"],
            "user": self._user_id,
        }
        if collateral_id:
            job_spec["collateral_ids"] = [collateral_id]

        submission_payload = {
            "run_spec": {
                "id": run_id,
                "name": f"Pytest Suite [{pkg_name}]",
                "tags": [f"package:{pkg_name}", "type:test"],
            },
            "jobs": [job_spec],
            "dependencies": {},
            "user_id": self._user_id,
            "elevate": self._elevate,
        }

        return self._submit_and_stream(run_id=run_id, payload=submission_payload)

    def _build_mutation_command(
        self,
        package_dir: Path,
        engine: MutationEngine,
        reset_cache: bool,
        workers: int | str | None,
        numprocesses: int | str | None,
        batch_size: int | None,
        report_file: Path | None,
        target_files: list[str] | None = None,
    ) -> tuple[str, list[str]]:
        """Construct executable command and arguments for mutation testing."""
        if engine == MutationEngine.GREMLINS or str(engine).lower() == "gremlins":
            cmd = "pytest"
            args = [
                "--rootdir=.",
                "-o",
                "addopts=",
                "--cov=src",
                "--cov-fail-under=0",
                "--gremlins",
            ]
            if target_files:
                args.append(f"--gremlin-targets={','.join(target_files)}")
            if reset_cache:
                args.append("--gremlin-clear-cache")
            eff_workers = workers if workers is not None else "auto"
            args.append(f"--gremlin-workers={eff_workers}")
            eff_batch = batch_size if batch_size is not None else 10
            args.append(f"--gremlin-batch-size={eff_batch}")
            args.append("--gremlin-batch")
            args.append("--gremlin-mutant-timeout=30")
            args.extend(["-m", "not demo and not e2e and not integration"])

            if numprocesses is not None:
                args.extend(["-n", str(numprocesses)])
            else:
                args.extend(["-n", "auto"])

            if report_file is not None:
                args.append(f"--gremlins-html-dir={report_file.parent}")
            args.append("--gremlin-report=json,console")
            if (package_dir / "tests" / "unit").is_dir():
                args.append("tests/unit")
            return cmd, args

        cmd = "mutmut"
        args = ["run"]
        return cmd, args

    def _submit_and_stream(self, run_id: str, payload: dict[str, Any]) -> int:
        """Submit run specification to Hexaqueue and stream progress to completion."""
        client = self._build_client()
        should_close = self._client is None
        submit_url = f"{self._cluster_url}/v1/runs"

        self._console.print(
            f"[bold blue]Submitting workload to Hexaqueue cluster:[/bold blue] {run_id}"
        )
        self._last_status_snapshot = None
        self._last_print_time = 0.0
        try:
            try:
                resp = client.post(submit_url, json=payload, headers=self._get_headers())
                if resp.status_code not in (200, 201):
                    self._err_console.print(
                        f"[bold red]Cluster run submission failed ({resp.status_code}):[/bold red] {resp.text}"
                    )
                    return 1
            except httpx.HTTPError as exc:
                self._err_console.print(
                    f"[bold red]Failed to connect to Hexaqueue cluster:[/bold red] {exc}"
                )
                return 1

            self._emit_step_summary(run_id, payload)
            return self._stream_run_progress(client=client, run_id=run_id)
        finally:
            if should_close:
                client.close()

    def _emit_step_summary(self, run_id: str, payload: dict[str, Any]) -> None:
        """Append run and job inspection CLI commands to GITHUB_STEP_SUMMARY."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
        if not summary_path:
            return
        jobs = payload.get("jobs", [])
        job_ids = [str(j["id"]) for j in jobs if isinstance(j, dict) and j.get("id")]
        lines = [
            f"### Hexaqueue Remote Run: `{run_id}`\n",
            f"- **Run Status**: `hq status {run_id}`",
            "- **Live Monitor**: `hq top`",
        ]
        for job_id in job_ids[:10]:
            lines.append(f"- **Job Logs**: `hq logs {job_id}`")
        if len(job_ids) > 10:
            lines.append(f"- _...and {len(job_ids) - 10} more jobs (`hq status {run_id}`)_")
        with (
            contextlib.suppress(OSError),
            Path(summary_path).open("a", encoding="utf-8") as fh,
        ):
            fh.write("\n".join(lines) + "\n\n")

    def _cancel_remote_run(self, client: httpx.Client, run_id: str) -> None:
        """Best-effort cancellation of a remote Hexaqueue run."""
        with contextlib.suppress(Exception):
            cancel_resp = client.post(
                f"{self._cluster_url}/v1/runs/{run_id}/cancel",
                headers=self._get_headers(),
                timeout=5.0,
            )
            if cancel_resp.status_code not in (200, 202, 204):
                self._err_console.print(
                    f"[yellow]Warning: Remote run cancellation returned status {cancel_resp.status_code}[/yellow]"
                )

    def _stream_run_progress(self, client: httpx.Client, run_id: str) -> int:
        """Stream SSE run progress pulses, falling back to polling if necessary."""
        stream_url = f"{self._cluster_url}/v1/runs/{run_id}/stream"
        start_time = time.time()
        params = {"poll_interval": self._poll_interval, "timeout": self._timeout}
        stream_timeout = httpx.Timeout(
            timeout=float(self._timeout),
            read=min(max(float(self._poll_interval) * 3, 65.0), float(self._timeout)),
        )

        is_main = threading.current_thread() is threading.main_thread()
        prev_sigint: Any = None
        prev_sigterm: Any = None

        def _raise_interrupt(_signum: int, _frame: Any) -> None:
            raise KeyboardInterrupt

        if is_main:
            prev_sigint = signal.signal(signal.SIGINT, _raise_interrupt)
            prev_sigterm = signal.signal(signal.SIGTERM, _raise_interrupt)

        try:
            try:
                with client.stream(
                    "GET",
                    stream_url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=stream_timeout,
                ) as stream_resp:
                    if stream_resp.status_code == 200:
                        for line in stream_resp.iter_lines():
                            if time.time() - start_time > self._timeout:
                                break
                            if not line:
                                continue
                            if line.startswith("data: "):
                                raw_data = line[6:].strip()
                                outcome_code = self._process_sse_data(raw_data)
                                if outcome_code is not None:
                                    return outcome_code
            except Exception as exc:
                logger.debug(
                    "SSE streaming connection interrupted (%s), falling back to polling", exc
                )

            return self._poll_run_progress(client=client, run_id=run_id, start_time=start_time)
        except KeyboardInterrupt:
            self._err_console.print(
                f"[yellow]Interrupted; cancelling remote Hexaqueue run {run_id}...[/yellow]"
            )
            self._cancel_remote_run(client, run_id)
            return 130
        finally:
            if is_main:
                if prev_sigint is not None:
                    signal.signal(signal.SIGINT, prev_sigint)
                if prev_sigterm is not None:
                    signal.signal(signal.SIGTERM, prev_sigterm)

    def _process_sse_data(self, raw_data: str) -> int | None:
        """Parse SSE JSON payload and print status pulses."""
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            return None

        state = data.get("state")
        completed = data.get("completed_jobs", 0)
        total = data.get("total_jobs", 1)
        failed = data.get("failed_jobs", 0)
        running = data.get("running_jobs", 0)
        outcome = data.get("outcome")

        snapshot = (state, completed, total, running, failed)
        is_terminal = state == "DONE" or outcome is not None
        now = time.monotonic()
        should_print = (
            is_terminal
            or snapshot != self._last_status_snapshot
            or (now - self._last_print_time) >= self._heartbeat_interval
        )
        if should_print:
            self._last_status_snapshot = snapshot
            self._last_print_time = now
            timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            self._console.print(
                f"[dim][Hexaqueue {timestamp}][/dim] State: [cyan]{state}[/cyan] | "
                f"Progress: [green]{completed}/{total}[/green] completed, "
                f"[yellow]{running}[/yellow] running, "
                f"[red]{failed}[/red] failed"
            )

        if is_terminal:
            if outcome in ("FAILED", "failed", "CANCELLED", "cancelled"):
                err = data.get("error") or data.get("failure_reason") or data.get("message")
                if err:
                    self._err_console.print(f"[bold red]Run failure details:[/bold red] {err}")
            return self._outcome_to_exit_code(outcome)
        return None

    def _poll_run_progress(
        self, client: httpx.Client, run_id: str, start_time: float | None = None
    ) -> int:
        """Poll run status endpoint periodically until completion."""
        poll_url = f"{self._cluster_url}/v1/runs/{run_id}"
        if start_time is None:
            start_time = time.time()

        while True:
            if time.time() - start_time > self._timeout:
                self._cancel_remote_run(client, run_id)
                self._err_console.print(
                    f"[bold red]Run {run_id} timed out after {self._timeout}s[/bold red]"
                )
                return 2

            with contextlib.suppress(httpx.HTTPError):
                resp = client.get(poll_url, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    exit_code = self._process_sse_data(json.dumps(data))
                    if exit_code is not None:
                        return exit_code

            time.sleep(self._poll_interval)

    @staticmethod
    def _outcome_to_exit_code(outcome: str | None) -> int:
        """Map Hexaqueue RunOutcome to process exit code."""
        if outcome in ("COMPLETED", "completed", "SUCCEEDED", "succeeded"):
            return 0
        if outcome in ("FAILED", "failed"):
            return 1
        if outcome in ("TIMED_OUT", "timed_out"):
            return 2
        if outcome in ("CANCELLED", "cancelled"):
            return 130
        return 1

    # --- Delegated Local Methods ---

    def read_mutation_records(
        self,
        path: Path,
        engine: MutationEngine = MutationEngine.GREMLINS,
        package_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Delegate mutation cache reading to base runner."""
        return self._base_runner.read_mutation_records(
            path=path, engine=engine, package_filter=package_filter
        )

    def get_changed_lines(
        self, repo_root: Path, base_ref: str | None = None
    ) -> dict[Path, set[int]]:
        """Delegate git diff changed line analysis to base runner."""
        return self._base_runner.get_changed_lines(repo_root=repo_root, base_ref=base_ref)

    def find_impacted_tests(
        self, changed_lines: dict[Path, set[int]], cov_path: Path | None = None
    ) -> set[str]:
        """Delegate test impact correlation to base runner."""
        return self._base_runner.find_impacted_tests(changed_lines=changed_lines, cov_path=cov_path)

    def get_tests_covering_line(
        self, file_path: str | Path, line_number: int, cov_path: Path | None = None
    ) -> list[str]:
        """Delegate line test coverage query to base runner."""
        return self._base_runner.get_tests_covering_line(
            file_path=file_path, line_number=line_number, cov_path=cov_path
        )

    def audit_layer_boundary_leaks(self, cov_path: Path | None = None) -> list[tuple[str, str]]:
        """Delegate boundary leak auditing to base runner."""
        return self._base_runner.audit_layer_boundary_leaks(cov_path=cov_path)

    def audit_redundant_tests(self, cov_path: Path | None = None) -> list[str]:
        """Delegate redundancy audit to base runner."""
        return self._base_runner.audit_redundant_tests(cov_path=cov_path)
