"""Unit tests for HexaqueueClusterRunnerAdapter.

Notes/Architectural Intent:
    Verifies that HexaqueueClusterRunnerAdapter translates mutation and pytest invocations
    into Hexaqueue JobSpec DAGs, submits them over HTTP REST, parses SSE progress pulses,
    handles fallback polling, and delegates local repository analysis to base runner.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from rich.console import Console

from hexaqual.adapters.runners.hexaqueue_cluster import HexaqueueClusterRunnerAdapter
from hexaqual.domain.testing import MutationEngine
from hexaqual.ports.testing import TestingRunnerPort


def test_headers_and_initialization() -> None:
    """Verify headers construction with user, elevation, and auth token."""
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="https://cluster.local:8080/",
        user_id="alice",
        elevate=True,
        token="secret-token-123",
        poll_interval=0.1,
    )
    headers = adapter._get_headers()
    assert headers["X-Hexaqueue-User"] == "alice"
    assert headers["X-Hexaqueue-Elevate"] == "true"
    assert headers["Authorization"] == "Bearer secret-token-123"


def test_run_mutation_testing_gremlins_success(tmp_path: Path) -> None:
    """Verify mutation testing with gremlins engine submits run and parses SSE pulses."""
    submitted_payloads: list[dict] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        if url_path == "/v1/runs" and request.method == "POST":
            payload = json.loads(request.content.decode("utf-8"))
            submitted_payloads.append(payload)
            return httpx.Response(
                status_code=201,
                json={"run_id": payload["run_spec"]["id"], "state": "PENDING"},
            )
        if "/stream" in url_path and request.method == "GET":
            sse_content = (
                "event: run_status\n"
                'data: {"state": "RUNNING", "completed_jobs": 0, "total_jobs": 1, "running_jobs": 1, "failed_jobs": 0}\n\n'
                "event: run_done\n"
                'data: {"state": "DONE", "outcome": "COMPLETED", "completed_jobs": 1, "total_jobs": 1, "running_jobs": 0, "failed_jobs": 0}\n\n'
            )
            return httpx.Response(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                text=sse_content,
            )
        return httpx.Response(status_code=404)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="http://cluster.local:8000")

    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        user_id="bob",
        http_client=client,
        console=Console(quiet=True),
    )

    pkg_dir = tmp_path / "my_pkg"
    pkg_dir.mkdir()
    exit_code = adapter.run_mutation_testing(
        package_dir=pkg_dir,
        engine=MutationEngine.GREMLINS,
        reset_cache=True,
        workers=4,
        numprocesses=2,
        batch_size=20,
    )

    assert exit_code == 0
    assert len(submitted_payloads) == 1
    job = submitted_payloads[0]["jobs"][0]
    assert job["command"] == "pytest"
    assert "--gremlins" in job["args"]
    assert "--gremlin-clear-cache" in job["args"]
    assert "--gremlin-workers=4" in job["args"]
    assert "--gremlin-batch-size=20" in job["args"]
    assert "-n" in job["args"]
    assert "2" in job["args"]


def test_run_mutation_testing_mutmut(tmp_path: Path) -> None:
    """Verify mutation testing with mutmut engine constructs correct command."""
    submitted_payloads: list[dict] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        if url_path == "/v1/runs" and request.method == "POST":
            payload = json.loads(request.content.decode("utf-8"))
            submitted_payloads.append(payload)
            return httpx.Response(status_code=201, json={"run_id": "r1", "state": "PENDING"})
        if "/stream" in url_path:
            sse_content = (
                "event: run_done\n"
                'data: {"state": "DONE", "outcome": "COMPLETED", "completed_jobs": 1, "total_jobs": 1}\n\n'
            )
            return httpx.Response(status_code=200, text=sse_content)
        return httpx.Response(status_code=404)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport, base_url="http://cluster.local:8000")

    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        http_client=client,
        console=Console(quiet=True),
    )

    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    exit_code = adapter.run_mutation_testing(package_dir=pkg_dir, engine=MutationEngine.MUTMUT)
    assert exit_code == 0
    assert len(submitted_payloads) == 1
    job = submitted_payloads[0]["jobs"][0]
    assert job["command"] == "mutmut"
    assert job["args"] == ["run"]


def test_execute_pytest_and_outcome_mapping(tmp_path: Path) -> None:
    """Verify execute_pytest submits job and maps failed outcome."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/runs":
            return httpx.Response(status_code=201, json={"run_id": "r-pytest"})
        if "/stream" in request.url.path:
            sse_content = (
                "event: run_done\n"
                'data: {"state": "DONE", "outcome": "FAILED", "failed_jobs": 1, "total_jobs": 1}\n\n'
            )
            return httpx.Response(status_code=200, text=sse_content)
        return httpx.Response(status_code=404)

    client = httpx.Client(
        transport=httpx.MockTransport(mock_handler), base_url="http://cluster.local:8000"
    )
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        http_client=client,
        console=Console(quiet=True),
    )

    exit_code = adapter.execute_pytest(
        test_nodes=["tests/unit/test_foo.py::test_bar"],
        extra_args=["-v"],
        cwd=tmp_path,
    )
    assert exit_code == 1


def test_submission_failure_handling(tmp_path: Path) -> None:
    """Verify handling when Hexaqueue cluster rejects submission with 500 error."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, text="Internal Cluster Scheduler Error")

    client = httpx.Client(
        transport=httpx.MockTransport(mock_handler), base_url="http://cluster.local:8000"
    )
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        http_client=client,
        console=Console(quiet=True),
    )

    code = adapter.execute_pytest(test_nodes=["tests/test_x.py"], cwd=tmp_path)
    assert code == 1


def test_stream_fallback_to_polling(tmp_path: Path) -> None:
    """Verify SSE streaming failure falls back to REST polling."""
    poll_calls = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal poll_calls
        if request.url.path == "/v1/runs" and request.method == "POST":
            return httpx.Response(status_code=201, json={"run_id": "r-poll"})
        if "/stream" in request.url.path:
            # Simulate SSE endpoint failure (e.g. 502 Bad Gateway or proxy failure)
            return httpx.Response(status_code=502, text="Proxy Error")
        if request.url.path.startswith("/v1/runs/") and request.method == "GET":
            poll_calls += 1
            if poll_calls == 1:
                return httpx.Response(
                    status_code=200,
                    json={
                        "run_id": "r-poll",
                        "state": "RUNNING",
                        "completed_jobs": 0,
                        "total_jobs": 1,
                    },
                )
            return httpx.Response(
                status_code=200,
                json={
                    "run_id": "r-poll",
                    "state": "DONE",
                    "outcome": "COMPLETED",
                    "completed_jobs": 1,
                    "total_jobs": 1,
                },
            )
        return httpx.Response(status_code=404)

    client = httpx.Client(
        transport=httpx.MockTransport(mock_handler), base_url="http://cluster.local:8000"
    )
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        poll_interval=0.01,
        http_client=client,
        console=Console(quiet=True),
    )

    code = adapter.execute_pytest(test_nodes=["tests/test_foo.py"], cwd=tmp_path)
    assert code == 0
    assert poll_calls >= 2


def test_delegated_mutation_and_diff_analysis() -> None:
    """Verify mutation records and git diff analysis delegate to base_runner."""
    mock_base = MagicMock(spec=TestingRunnerPort)
    adapter = HexaqueueClusterRunnerAdapter(base_runner=mock_base)

    adapter.read_mutation_records(Path("db.sqlite"))
    mock_base.read_mutation_records.assert_called_once()

    adapter.get_changed_lines(Path())
    mock_base.get_changed_lines.assert_called_once()


def test_delegated_impact_and_coverage_analysis() -> None:
    """Verify impacted tests and line coverage lookup delegate to base_runner."""
    mock_base = MagicMock(spec=TestingRunnerPort)
    adapter = HexaqueueClusterRunnerAdapter(base_runner=mock_base)

    adapter.find_impacted_tests({})
    mock_base.find_impacted_tests.assert_called_once()

    adapter.get_tests_covering_line("foo.py", 10)
    mock_base.get_tests_covering_line.assert_called_once()


def test_delegated_boundary_and_redundancy_audits() -> None:
    """Verify architectural boundaries and test redundancy audits delegate to base_runner."""
    mock_base = MagicMock(spec=TestingRunnerPort)
    adapter = HexaqueueClusterRunnerAdapter(base_runner=mock_base)

    adapter.audit_layer_boundary_leaks()
    mock_base.audit_layer_boundary_leaks.assert_called_once()

    adapter.audit_redundant_tests()
    mock_base.audit_redundant_tests.assert_called_once()


def test_security_validation_rejects_insecure_remote_http_token() -> None:
    """Verify CWE-319 protection: bearer tokens cannot be transmitted over remote plain HTTP."""
    with pytest.raises(ValueError, match="Insecure transport"):
        HexaqueueClusterRunnerAdapter(
            cluster_url="http://remote-cluster.internal:8000",
            token="secret-token",
        )


def test_security_validation_allows_https_and_localhost() -> None:
    """Verify security validation permits HTTPS and localhost/testcluster."""
    adapter1 = HexaqueueClusterRunnerAdapter(
        cluster_url="https://remote-cluster.internal:8000",
        token="secret-token",
    )
    assert adapter1._token == "secret-token"

    adapter2 = HexaqueueClusterRunnerAdapter(
        cluster_url="http://localhost:8000",
        token="secret-token",
    )
    assert adapter2._token == "secret-token"


def test_process_sse_data_edge_cases_and_outcomes() -> None:
    """Verify _process_sse_data parses error payloads, invalid JSON, and maps exit codes."""
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://localhost:8000",
        console=Console(quiet=True),
    )

    invalid_code = adapter._process_sse_data("invalid-json{")
    assert invalid_code is None

    err_payload = json.dumps(
        {
            "state": "DONE",
            "outcome": "FAILED",
            "error": "SyntaxError in test file",
        }
    )
    failed_code = adapter._process_sse_data(err_payload)
    assert failed_code == 1

    timeout_payload = json.dumps({"state": "DONE", "outcome": "TIMED_OUT"})
    timeout_code = adapter._process_sse_data(timeout_payload)
    assert timeout_code == 2

    cancelled_payload = json.dumps({"state": "DONE", "outcome": "CANCELLED"})
    cancel_code = adapter._process_sse_data(cancelled_payload)
    assert cancel_code == 130

    unknown_payload = json.dumps({"state": "DONE", "outcome": "UNEXPECTED_STATE"})
    unknown_code = adapter._process_sse_data(unknown_payload)
    assert unknown_code == 1


def test_run_mutation_testing_defaults_and_report_file(tmp_path: Path) -> None:
    """Verify mutation testing defaults numprocesses to auto and forwards report_file parent."""
    submitted_payloads: list[dict] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/runs":
            payload = json.loads(request.content.decode("utf-8"))
            submitted_payloads.append(payload)
            return httpx.Response(status_code=201, json={"run_id": "r-defaults"})
        if "/stream" in request.url.path:
            sse_content = (
                "event: run_done\n"
                'data: {"state": "DONE", "outcome": "COMPLETED", "completed_jobs": 1, "total_jobs": 1}\n\n'
            )
            return httpx.Response(status_code=200, text=sse_content)
        return httpx.Response(status_code=404)

    client = httpx.Client(
        transport=httpx.MockTransport(mock_handler), base_url="http://cluster.local:8000"
    )
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        http_client=client,
        console=Console(quiet=True),
    )

    report_path = tmp_path / "reports" / "gremlins.html"
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    exit_code = adapter.run_mutation_testing(
        package_dir=pkg_dir,
        engine=MutationEngine.GREMLINS,
        reset_cache=False,
        numprocesses=None,
        report_file=report_path,
    )

    assert exit_code == 0
    assert len(submitted_payloads) == 1
    job = submitted_payloads[0]["jobs"][0]
    assert "-n" in job["args"]
    assert "auto" in job["args"]
    assert f"--gremlins-html-dir={report_path.parent}" in job["args"]
    assert "--gremlin-clear-cache" not in job["args"]


def test_submit_and_stream_connect_error(tmp_path: Path) -> None:
    """Verify _submit_and_stream handles httpx.ConnectError gracefully and returns 1."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to establish cluster connection", request=request)

    client = httpx.Client(
        transport=httpx.MockTransport(mock_handler), base_url="http://cluster.local:8000"
    )
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        http_client=client,
        console=Console(quiet=True),
    )

    code = adapter.execute_pytest(test_nodes=["tests/test_net.py"], cwd=tmp_path)
    assert code == 1


def test_build_client_lifecycle(tmp_path: Path) -> None:
    """Verify _build_client instantiates default httpx.Client and cleans it up when none is injected."""
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://localhost:8000",
        console=Console(quiet=True),
    )
    client = adapter._build_client()
    assert str(client.base_url) == "http://localhost:8000"
    client.close()


def test_stream_exception_falls_back_to_polling() -> None:
    """Verify SSE streaming exception logs debug and falls back to polling."""
    mock_client = MagicMock()
    mock_client.stream.side_effect = httpx.ReadTimeout("Stream connection timed out")

    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://localhost:8000",
        console=Console(quiet=True),
    )
    with pytest.MonkeyPatch.context() as mp:
        mock_poll = MagicMock(return_value=0)
        mp.setattr(adapter, "_poll_run_progress", mock_poll)
        code = adapter._stream_run_progress(client=mock_client, run_id="r-stream-err")
        assert code == 0
        mock_poll.assert_called_once()


def test_poll_run_progress_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _poll_run_progress cancels timed out run, prints warning on non-200 cancel, and returns 2."""
    cancelled_urls: list[str] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "/cancel" in request.url.path:
            cancelled_urls.append(request.url.path)
            return httpx.Response(status_code=500, text="Cluster cancellation failed")
        return httpx.Response(status_code=200, json={"state": "RUNNING"})

    client = httpx.Client(
        transport=httpx.MockTransport(mock_handler), base_url="http://cluster.local:8000"
    )
    adapter = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        timeout=0.01,
        poll_interval=0.005,
        http_client=client,
        console=Console(quiet=True),
    )

    exit_code = adapter._poll_run_progress(client=client, run_id="r-timed-out", start_time=0.0)
    assert exit_code == 2
    assert len(cancelled_urls) == 1

    # Test when cancel returns 200 and start_time defaults to None
    def mock_success_cancel(request: httpx.Request) -> httpx.Response:
        if "/cancel" in request.url.path:
            return httpx.Response(status_code=200, json={"status": "cancelled"})
        return httpx.Response(status_code=200, json={"state": "RUNNING"})

    client_success = httpx.Client(
        transport=httpx.MockTransport(mock_success_cancel), base_url="http://cluster.local:8000"
    )
    adapter_fast_timeout = HexaqueueClusterRunnerAdapter(
        cluster_url="http://cluster.local:8000",
        timeout=-1.0,  # Immediately timeout
        poll_interval=0.001,
        http_client=client_success,
        console=Console(quiet=True),
    )
    exit_code_success = adapter_fast_timeout._poll_run_progress(
        client=client_success, run_id="r-success-cancel"
    )
    assert exit_code_success == 2
