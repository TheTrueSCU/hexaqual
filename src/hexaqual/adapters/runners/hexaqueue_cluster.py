"""Hexaqueue cluster execution adapter for distributed test and mutation runs.

Notes/Architectural Intent:
    Encapsulates remote job submission, Server-Sent Events (SSE) telemetry streaming,
    and log ingestion against a remote Hexaqueue batch cluster via HTTP/SSE.
    Implements TestingRunnerPort by translating local pytest/gremlins invocations into
    Hexaqueue JobSpec DAGs while delegating local file inspection and git diff
    analysis to a local TestingRunnerPort delegate.
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from rich.console import Console

from hexaqual.adapters.runners.testing_runner import SubprocessTestingRunnerAdapter
from hexaqual.domain.testing import MutationEngine
from hexaqual.ports.testing import TestingRunnerPort

logger = logging.getLogger(__name__)

__all__ = [
    "HexaqueueClusterRunnerAdapter",
]


class HexaqueueClusterRunnerAdapter(TestingRunnerPort):
    """Remote runner adapter submitting test and mutation workloads to a Hexaqueue cluster."""

    def __init__(
        self,
        cluster_url: str = "http://localhost:8000",
        user_id: str = "default",
        elevate: bool = False,
        token: str | None = None,
        poll_interval: float = 0.5,
        timeout: float = 300.0,
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
            timeout: Maximum overall timeout in seconds for remote job execution.
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
        self._timeout = timeout
        self._base_runner = base_runner or SubprocessTestingRunnerAdapter()
        self._console = console or Console()
        self._err_console = Console(stderr=True)
        self._client = http_client

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

    def run_mutation_testing(
        self,
        package_dir: Path,
        engine: MutationEngine = MutationEngine.GREMLINS,
        reset_cache: bool = False,
        workers: int | str | None = None,
        numprocesses: int | str | None = None,
        batch_size: int | None = None,
        report_file: Path | None = None,
    ) -> int:
        """Run mutation testing on a remote Hexaqueue cluster.

        Args:
            package_dir: Directory path of package to mutate.
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
            cluster RunOutcome to process returncode.
        """
        run_id = f"mut-{package_dir.name}-{uuid4().hex[:8]}"
        cmd, args = self._build_mutation_command(
            package_dir=package_dir,
            engine=engine,
            reset_cache=reset_cache,
            workers=workers,
            numprocesses=numprocesses,
            batch_size=batch_size,
            report_file=report_file,
        )

        job_spec = {
            "id": f"job-{run_id}-0",
            "run_id": run_id,
            "name": f"mutation-{package_dir.name}",
            "command": cmd,
            "args": args,
            "env": {
                "PYTHONUNBUFFERED": "1",
                "HEXAQUEUE_CWD": str(package_dir.resolve()),
            },
            "resources": {"cpus": 2, "ram_mb": 2048},
            "tags": [f"package:{package_dir.name}", f"owner:{self._user_id}", "type:mutation"],
            "user": self._user_id,
        }

        submission_payload = {
            "run_spec": {
                "id": run_id,
                "name": f"Mutation Testing [{package_dir.name}]",
                "tags": [f"package:{package_dir.name}", "type:mutation"],
            },
            "jobs": [job_spec],
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

        effective_cwd = cwd.resolve() if cwd else Path.cwd().resolve()
        job_spec = {
            "id": f"job-{run_id}-0",
            "run_id": run_id,
            "name": f"pytest-{pkg_name}",
            "command": "pytest",
            "args": all_args,
            "env": {
                "PYTHONUNBUFFERED": "1",
                "HEXAQUEUE_CWD": str(effective_cwd),
            },
            "resources": {"cpus": 2, "ram_mb": 2048},
            "tags": [f"package:{pkg_name}", f"owner:{self._user_id}", "type:test"],
            "user": self._user_id,
        }

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
            if reset_cache:
                args.append("--gremlin-clear-cache")
            eff_workers = workers if workers is not None else "auto"
            args.append(f"--gremlin-workers={eff_workers}")
            eff_batch = batch_size if batch_size is not None else 10
            args.append(f"--gremlin-batch-size={eff_batch}")
            args.append("--gremlin-batch")

            if numprocesses is not None:
                args.extend(["-n", str(numprocesses)])
            else:
                args.extend(["-n", "auto"])

            if report_file is not None:
                args.append(f"--gremlins-html-dir={report_file.parent}")
            args.append("--gremlin-report=json,console")
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

            return self._stream_run_progress(client=client, run_id=run_id)
        finally:
            if should_close:
                client.close()

    def _stream_run_progress(self, client: httpx.Client, run_id: str) -> int:
        """Stream SSE run progress pulses, falling back to polling if necessary."""
        stream_url = f"{self._cluster_url}/v1/runs/{run_id}/stream"
        start_time = time.time()
        params = {"poll_interval": self._poll_interval, "timeout": self._timeout}

        try:
            with client.stream(
                "GET", stream_url, params=params, headers=self._get_headers()
            ) as stream_resp:
                if stream_resp.status_code == 200:
                    for line in stream_resp.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            raw_data = line[6:].strip()
                            outcome_code = self._process_sse_data(raw_data)
                            if outcome_code is not None:
                                return outcome_code
        except Exception as exc:
            logger.debug("SSE streaming connection interrupted (%s), falling back to polling", exc)

        return self._poll_run_progress(client=client, run_id=run_id, start_time=start_time)

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

        self._console.print(
            f"[dim][Hexaqueue][/dim] State: [cyan]{state}[/cyan] | "
            f"Progress: [green]{completed}/{total}[/green] completed, "
            f"[yellow]{running}[/yellow] running, "
            f"[red]{failed}[/red] failed"
        )

        if state == "DONE" or outcome is not None:
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
                with contextlib.suppress(Exception):
                    client.post(
                        f"{self._cluster_url}/v1/runs/{run_id}/cancel",
                        headers=self._get_headers(),
                    )
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
