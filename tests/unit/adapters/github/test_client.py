"""Unit tests for GitHub HTTP client adapter."""

from hexaqual.adapters.github.client import (
    GitHubHttpAdapter,
    get_github_token,
)


def test_get_github_token() -> None:
    """Verify token resolution callable executes safely."""
    token = get_github_token()
    # May be string or None depending on environment
    assert token is None or isinstance(token, str)


def test_github_http_adapter_init() -> None:
    """Verify adapter initialization and context manager."""
    with GitHubHttpAdapter(token="dummy", owner="TestOwner", repo="TestRepo") as client:
        assert client.owner == "TestOwner"
        assert client.repo == "TestRepo"
        assert client.token == "dummy"


def test_parse_github_url_variants() -> None:
    """Verify _parse_github_url handles SSH SCP, HTTPS, and userinfo formats."""
    from hexaqual.adapters.github.client import _parse_github_url

    # SSH SCP format
    assert _parse_github_url("git@github.com:TheTrueSCU/hexastack.git") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("git@github.com:Owner/Repo") == ("Owner", "Repo")

    # HTTPS format
    assert _parse_github_url("https://github.com/TheTrueSCU/hexastack.git") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("https://github.com/TheTrueSCU/hexastack") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("https://github.com/TheTrueSCU/hexastack.git/") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("git@github.com:TheTrueSCU/hexastack.git/") == (
        "TheTrueSCU",
        "hexastack",
    )

    # HTTPS with userinfo
    assert _parse_github_url(
        "https://user:token@github.com/TheTrueSCU/hexastack.git"  # pragma: allowlist secret
    ) == (
        "TheTrueSCU",
        "hexastack",
    )

    # Non-GitHub host returns None
    assert _parse_github_url("git@gitlab.com:TheTrueSCU/hexastack.git") is None
    assert _parse_github_url("https://gitlab.com/TheTrueSCU/hexastack.git") is None


def test_github_http_adapter_api_methods() -> None:
    """Verify GitHubHttpAdapter methods via mock httpx transport."""
    from unittest.mock import patch

    import httpx

    def mock_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/Owner/Repo":
            return httpx.Response(
                200,
                json={
                    "name": "Repo",
                    "visibility": "public",
                    "private": False,
                    "default_branch": "main",
                    "allow_auto_merge": True,
                    "allow_squash_merge": True,
                    "has_pages": False,
                },
            )
        if path == "/repos/Owner/Repo/actions/permissions":
            return httpx.Response(200, json={"enabled": True, "allowed_actions": "all"})
        if path == "/repos/Owner/Repo/actions/permissions/workflow":
            return httpx.Response(
                200,
                json={
                    "default_workflow_permissions": "read",
                    "can_approve_pull_request_reviews": False,
                },
            )
        if path == "/repos/Owner/Repo/environments":
            return httpx.Response(200, json={"environments": [{"name": "production"}]})
        if path == "/repos/Owner/Repo/branches/main/protection":
            return httpx.Response(
                200,
                json={
                    "required_status_checks": {"contexts": ["CI"]},
                    "required_conversation_resolution": {"enabled": True},
                },
            )
        if path == "/repos/Owner/Repo/pulls/10":
            return httpx.Response(
                200,
                json={
                    "head": {"ref": "feat", "sha": "abc1234"},
                    "title": "PR Title",
                },
            )
        if path == "/repos/Owner/Repo/commits/abc1234/check-runs":
            return httpx.Response(
                200,
                json={
                    "check_runs": [
                        {
                            "id": 1,
                            "name": "quality-gate",
                            "status": "completed",
                            "conclusion": "success",
                            "html_url": "https://github.com",
                            "output": {"title": "All Passed", "summary": "Clean run"},
                        }
                    ]
                },
            )
        if path == "/graphql":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "reviewThreads": {
                                    "nodes": [
                                        {
                                            "id": "thread_1",
                                            "isResolved": False,
                                            "resolvedBy": None,
                                            "comments": {
                                                "nodes": [
                                                    {
                                                        "id": "c_1",
                                                        "author": {"login": "octocat"},
                                                        "body": "Fix this line",
                                                        "path": "file.py",
                                                        "line": 42,
                                                        "createdAt": "2026-09-01T00:00:00Z",
                                                        "url": "https://github.com",
                                                    }
                                                ]
                                            },
                                        }
                                    ]
                                }
                            }
                        }
                    }
                },
            )
        if path == "/repos/Owner/Repo/issues/10/comments":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 501,
                        "user": {"login": "reviewer"},
                        "body": "General comment",
                        "created_at": "2026-09-01T00:00:00Z",
                        "html_url": "https://github.com",
                    }
                ],
            )
        if path == "/repos/Owner/Repo/pulls/10/comments":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 601,
                        "user": {"login": "reviewer"},
                        "body": "Inline comment",
                        "created_at": "2026-09-01T00:00:00Z",
                        "path": "file.py",
                        "line": 10,
                        "html_url": "https://github.com",
                        "diff_hunk": "@@ -1,3 +1,3 @@",
                    }
                ],
            )
        if path == "/repos/Owner/Repo/code-scanning/alerts":
            return httpx.Response(
                200,
                json=[
                    {
                        "number": 1,
                        "rule": {
                            "id": "py/sql-injection",
                            "description": "SQL injection",
                            "severity": "error",
                            "security_severity_level": "critical",
                            "help": "Sanitize query",
                        },
                        "most_recent_instance": {
                            "location": {"path": "db.py", "start_line": 5, "end_line": 6},
                            "message": {"text": "Unescaped string formatting"},
                        },
                        "state": "open",
                    }
                ],
            )
        if path == "/repos/Owner/Repo/code-scanning/alerts/1":
            return httpx.Response(
                200,
                json={
                    "number": 1,
                    "rule": {
                        "id": "py/sql-injection",
                        "description": "SQL injection",
                        "severity": "error",
                        "security_severity_level": "critical",
                    },
                    "most_recent_instance": {
                        "location": {"path": "db.py", "start_line": 5, "end_line": 6},
                        "message": {"text": "Unescaped string formatting"},
                    },
                    "state": "open",
                },
            )
        if path == "/repos/Owner/Repo/actions/runs":
            return httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {
                            "id": 999,
                            "name": "CI",
                            "conclusion": "success",
                            "head_sha": "abc1234",
                            "event": "push",
                            "status": "completed",
                            "display_title": "Commit message",
                            "html_url": "https://github.com",
                        }
                    ]
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    adapter = GitHubHttpAdapter(token="mock", owner="Owner", repo="Repo")
    adapter._client = httpx.Client(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(mock_handler),
    )

    # 1. get_repo_status
    status = adapter.get_repo_status()
    assert status.name == "Repo"
    assert status.default_branch == "main"
    assert status.require_conversation_resolution is True
    assert "production" in status.environments
    assert "CI" in status.required_status_checks

    # 2. get_pr_summary
    pr = adapter.get_pr_summary(10)
    assert len(pr.check_runs) == 1
    assert pr.check_runs[0].name == "quality-gate"
    assert len(pr.review_threads) == 1
    assert pr.review_threads[0].id == "thread_1"
    assert len(pr.general_comments) == 2  # 1 issue comment + 1 pull comment

    # 3. get_code_scanning_alerts and single alert
    alerts = adapter.get_code_scanning_alerts()
    assert len(alerts) == 1
    assert alerts[0].rule_id == "py/sql-injection"

    single = adapter.get_single_alert(1)
    assert single.number == 1
    assert single.severity == "error"

    # 4. get_workflow_runs (with gh CLI fallback to REST)
    with patch("shutil.which", return_value=None):
        runs = adapter.get_workflow_runs()
        assert len(runs) == 1
        assert runs[0]["name"] == "CI"
        assert runs[0]["databaseId"] == 999
