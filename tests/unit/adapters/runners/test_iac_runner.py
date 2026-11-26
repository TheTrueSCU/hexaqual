"""Unit tests for SubprocessIacAuditorAdapter.

Notes/Architectural Intent:
    Verifies IaC artifact discovery (including ignored directory pruning and
    Kubernetes YAML detection), binary resolution, and JSON output parsing across
    OpenTofu/Terraform, TFLint, Trivy, Checkov, Hadolint, and ShellCheck.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexaqual.adapters.runners.iac_runner import (
    SubprocessIacAuditorAdapter,
    _deduplicate_ancestor_dirs,
    _execute_subprocess,
)
from hexaqual.domain.iac import (
    IacCheckStatus,
    IacSeverity,
    IacToolName,
)


def test_discover_assets_polyglot_and_ignores(tmp_path: Path) -> None:
    """Verify discover_assets detects IaC files while pruning ignored dirs and workflows."""
    # OpenTofu module
    tf_dir = tmp_path / "deploy" / "tofu" / "oci"
    tf_dir.mkdir(parents=True)
    (tf_dir / "main.tf").write_text('terraform { required_version = ">= 1.6" }\n', encoding="utf-8")
    (tf_dir / "prod.tfvars").write_text('env = "prod"\n', encoding="utf-8")
    (tf_dir / "extra.tf.json").write_text("{}", encoding="utf-8")

    # Dockerfiles
    docker_dir = tmp_path / "deploy" / "docker"
    docker_dir.mkdir(parents=True)
    (docker_dir / "Dockerfile").write_text("FROM python:3.13-slim\n", encoding="utf-8")
    (docker_dir / "Dockerfile.worker").write_text("FROM python:3.13-slim\n", encoding="utf-8")
    (docker_dir / "gpu.dockerfile").write_text("FROM python:3.13-slim\n", encoding="utf-8")

    # Helm chart + K8s manifest + non-K8s YAML
    chart_dir = tmp_path / "deploy" / "charts" / "api"
    (chart_dir / "templates").mkdir(parents=True)
    (chart_dir / "Chart.yaml").write_text("apiVersion: v2\nname: api\n", encoding="utf-8")
    (chart_dir / "templates" / "deploy.yaml").write_text(
        "apiVersion: apps/v1\nkind: Deployment\n", encoding="utf-8"
    )
    k8s_standalone = tmp_path / "deploy" / "k8s" / "service.yml"
    k8s_standalone.parent.mkdir(parents=True)
    k8s_standalone.write_text("apiVersion: v1\nkind: Service\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "apiVersion: fake\nkind: NotK8s\n", encoding="utf-8"
    )
    (tmp_path / "config.yaml").write_text("foo: bar\n", encoding="utf-8")

    # Shell scripts
    (tf_dir / "templates").mkdir()
    (tf_dir / "templates" / "bootstrap.sh").write_text("#!/bin/bash\necho hi\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "check.bash").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    # Ignored directories
    for ignored in (".venv", ".terraform", ".git", "node_modules", "dist"):
        bad = tmp_path / ignored
        bad.mkdir()
        (bad / "ignored.tf").write_text("# ignored\n", encoding="utf-8")
        (bad / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        (bad / "ignored.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    adapter = SubprocessIacAuditorAdapter()
    inv = adapter.discover_assets(tmp_path)

    assert inv.has_any is True
    assert inv.tofu_dirs == (tf_dir.resolve(),)
    assert len(inv.tofu_files) == 3
    assert len(inv.dockerfiles) == 3
    # Chart dir suppresses nested template YAML, while standalone service.yml is kept
    assert inv.k8s_paths == (chart_dir.resolve(), k8s_standalone.resolve())
    assert len(inv.shell_scripts) == 2

    # Explicit scoped path discovery
    scoped = adapter.discover_assets(tmp_path, paths=(Path("deploy/docker/Dockerfile"),))
    assert scoped.dockerfiles == ((docker_dir / "Dockerfile").resolve(),)
    assert scoped.tofu_files == ()


def test_deduplicate_ancestor_dirs(tmp_path: Path) -> None:
    """Verify nested directories under an already included parent are deduplicated."""
    parent = tmp_path / "infra"
    child = parent / "modules" / "net"
    sibling = tmp_path / "docker"
    parent.mkdir(parents=True)
    child.mkdir(parents=True)
    sibling.mkdir(parents=True)

    deduped = _deduplicate_ancestor_dirs((child, parent, sibling, parent))
    assert deduped == (sibling.resolve(), parent.resolve())


def test_execute_subprocess_handles_success_and_oserror() -> None:
    """Verify _execute_subprocess wraps subprocess.run and catches OSError."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        code, out, err, dur = _execute_subprocess(["echo", "ok"])
        assert code == 0
        assert out == "ok"
        assert err == ""
        assert dur >= 0.0

    with patch("subprocess.run", side_effect=OSError("missing binary")):
        code, out, err, dur = _execute_subprocess(["missing"])
        assert code == 1
        assert "missing binary" in err


def test_check_tool_availability(tmp_path: Path) -> None:
    """Verify check_tool_availability resolves tofu/terraform fallback and venv checkov."""
    adapter = SubprocessIacAuditorAdapter()

    def _fake_which(name: str) -> str | None:
        return {
            "terraform": "/usr/local/bin/terraform",
            "tflint": "/usr/local/bin/tflint",
        }.get(name)

    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", side_effect=_fake_which),
        patch("hexaqual.adapters.runners.iac_runner.Path.is_file", return_value=True),
    ):
        avail = adapter.check_tool_availability()

    by_tool = {item.tool: item for item in avail}
    assert by_tool[IacToolName.TOFU_FMT].binary == "terraform"
    assert by_tool[IacToolName.TOFU_FMT].installed is True
    assert by_tool[IacToolName.TFLINT].installed is True
    assert by_tool[IacToolName.TRIVY].installed is False
    assert by_tool[IacToolName.CHECKOV].installed is True


def test_run_tofu_fmt_scenarios(tmp_path: Path) -> None:
    """Verify run_tofu_fmt across skip, missing binary, strict mode, pass, fix, and fail."""
    adapter = SubprocessIacAuditorAdapter()
    tf_dir = tmp_path / "tofu"
    tf_dir.mkdir()

    res_empty = adapter.run_tofu_fmt(tmp_path, ())
    assert res_empty.status == IacCheckStatus.SKIP

    with patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value=None):
        res_missing = adapter.run_tofu_fmt(tmp_path, (tf_dir,), strict=False)
        assert res_missing.status == IacCheckStatus.SKIP
        res_strict = adapter.run_tofu_fmt(tmp_path, (tf_dir,), strict=True)
        assert res_strict.status == IacCheckStatus.FAIL

    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tofu"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            side_effect=[(0, "", "", 0.02), (0, "", "", 0.02)],
        ) as mock_exec,
    ):
        res_pass = adapter.run_tofu_fmt(tmp_path, (tf_dir,), fix=True)
        assert res_pass.status == IacCheckStatus.PASS
        call_count = mock_exec.call_count
        assert call_count == 2

    diff_out = "main.tf\n--- old/main.tf\n+++ new/main.tf\n@@ -1 +1 @@\n"
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tofu"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(3, diff_out, "", 0.03),
        ),
    ):
        res_fail = adapter.run_tofu_fmt(tmp_path, (tf_dir,))
        assert res_fail.status == IacCheckStatus.FAIL
        assert res_fail.findings[0].file_path == "tofu/main.tf"
        assert res_fail.findings[0].rule_id == "tofu-fmt"


def test_run_tofu_validate_scenarios(tmp_path: Path) -> None:
    """Verify run_tofu_validate handles uninitialized modules, --init, JSON diagnostics, and pass."""
    adapter = SubprocessIacAuditorAdapter()
    tf_dir = tmp_path / "infra"
    tf_dir.mkdir()

    assert adapter.run_tofu_validate(tmp_path, ()).status == IacCheckStatus.SKIP

    with patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value=None):
        assert adapter.run_tofu_validate(tmp_path, (tf_dir,)).status == IacCheckStatus.SKIP

    # Uninitialized without --init
    with patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tofu"):
        res_uninit = adapter.run_tofu_validate(tmp_path, (tf_dir,), init_tofu=False, strict=False)
        assert res_uninit.status == IacCheckStatus.SKIP
        res_uninit_strict = adapter.run_tofu_validate(
            tmp_path, (tf_dir,), init_tofu=False, strict=True
        )
        assert res_uninit_strict.status == IacCheckStatus.FAIL

    # --init failure
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tofu"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(1, "", "provider error", 0.05),
        ),
    ):
        res_init_fail = adapter.run_tofu_validate(tmp_path, (tf_dir,), init_tofu=True)
        assert res_init_fail.status == IacCheckStatus.FAIL
        assert res_init_fail.findings[0].rule_id == "tofu-init"

    # --init success + validate -json clean
    valid_json = json.dumps({"valid": True, "diagnostics": []})
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tofu"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            side_effect=[(0, "", "", 0.1), (0, valid_json, "", 0.05)],
        ),
    ):
        res_ok = adapter.run_tofu_validate(tmp_path, (tf_dir,), init_tofu=True)
        assert res_ok.status == IacCheckStatus.PASS
        assert res_ok.targets_checked == 1

    # Initialized module with JSON diagnostic
    (tf_dir / ".terraform").mkdir()
    invalid_json = json.dumps(
        {
            "valid": False,
            "diagnostics": [
                {
                    "severity": "error",
                    "summary": "Missing required argument",
                    "detail": "The argument 'compartment_id' is required",
                    "range": {"filename": "pool.tf", "start": {"line": 14}},
                }
            ],
        }
    )
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tofu"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(1, invalid_json, "", 0.04),
        ),
    ):
        res_diag = adapter.run_tofu_validate(tmp_path, (tf_dir,))
        assert res_diag.status == IacCheckStatus.FAIL
        assert res_diag.findings[0].file_path == "infra/pool.tf"
        assert res_diag.findings[0].line == 14
        assert res_diag.findings[0].severity == IacSeverity.HIGH


def test_run_tflint_trivy_checkov(tmp_path: Path) -> None:
    """Verify JSON parsing for TFLint, Trivy config, and Checkov (dict and list)."""
    adapter = SubprocessIacAuditorAdapter()
    tf_dir = tmp_path / "oci"
    tf_dir.mkdir()
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.13\n", encoding="utf-8")

    # TFLint
    tflint_json = json.dumps(
        {
            "issues": [
                {
                    "rule": {"name": "terraform_unused_declarations", "severity": "warning"},
                    "message": "variable unused",
                    "range": {"filename": "vars.tf", "start": {"line": 8}},
                }
            ],
            "errors": [{"severity": "error", "message": "plugin error"}],
        }
    )
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tflint"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(2, tflint_json, "", 0.03),
        ),
    ):
        tflint_res = adapter.run_tflint(tmp_path, (tf_dir,))
        assert tflint_res.status == IacCheckStatus.FAIL
        assert len(tflint_res.findings) == 2
        assert tflint_res.findings[0].rule_id == "terraform_unused_declarations"

    # Trivy
    trivy_json = json.dumps(
        {
            "Results": [
                {
                    "Target": "Dockerfile",
                    "Misconfigurations": [
                        {
                            "ID": "DS002",
                            "Title": "Root user",
                            "Message": "Specify USER",
                            "Severity": "HIGH",
                            "Status": "FAIL",
                            "Resolution": "Add USER nonroot",
                            "CauseMetadata": {"StartLine": 1},
                        },
                        {
                            "ID": "DS026",
                            "Title": "Healthcheck",
                            "Severity": "LOW",
                            "Status": "PASS",
                        },
                    ],
                }
            ]
        }
    )
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/trivy"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(1, trivy_json, "", 0.05),
        ),
    ):
        trivy_res = adapter.run_trivy(tmp_path, (dockerfile,))
        assert trivy_res.status == IacCheckStatus.FAIL
        assert len(trivy_res.findings) == 1
        assert trivy_res.findings[0].rule_id == "DS002"
        assert trivy_res.findings[0].severity == IacSeverity.HIGH

    # Checkov list payload
    checkov_json = json.dumps(
        [
            {
                "results": {
                    "failed_checks": [
                        {
                            "check_id": "CKV_DOCKER_2",
                            "check_name": "Ensure HEALTHCHECK instructions",
                            "repo_file_path": "/Dockerfile",
                            "file_line_range": [1, 1],
                            "severity": "MEDIUM",
                            "guideline": "https://docs.example.com",
                        }
                    ]
                }
            }
        ]
    )
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/checkov"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(1, checkov_json, "", 0.1),
        ),
    ):
        ckv_res = adapter.run_checkov(tmp_path, (dockerfile,))
        assert ckv_res.status == IacCheckStatus.FAIL
        assert len(ckv_res.findings) == 1
        assert ckv_res.findings[0].rule_id == "CKV_DOCKER_2"
        assert ckv_res.findings[0].line == 1


def test_run_hadolint_and_shellcheck(tmp_path: Path) -> None:
    """Verify Hadolint and ShellCheck JSON parsing and threshold behavior."""
    adapter = SubprocessIacAuditorAdapter()
    df = tmp_path / "Dockerfile"
    df.write_text("FROM python:3.13\n", encoding="utf-8")
    sh = tmp_path / "boot.sh"
    sh.write_text("#!/bin/bash\necho $foo\n", encoding="utf-8")

    # Hadolint advisory only (exit 0)
    info_json = json.dumps(
        [{"line": 1, "code": "DL3066", "message": "Notice", "file": "Dockerfile", "level": "info"}]
    )
    with (
        patch(
            "hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/hadolint"
        ),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(0, info_json, "", 0.02),
        ),
    ):
        hl_ok = adapter.run_hadolint(tmp_path, (df,), failure_threshold="warning")
        assert hl_ok.status == IacCheckStatus.PASS
        assert "advisory notice" in hl_ok.details

    # Hadolint failure
    warn_json = json.dumps(
        [
            {
                "line": 2,
                "code": "DL3008",
                "message": "Pin versions",
                "file": "Dockerfile",
                "level": "warning",
            }
        ]
    )
    with (
        patch(
            "hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/hadolint"
        ),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(1, warn_json, "", 0.02),
        ),
    ):
        hl_fail = adapter.run_hadolint(tmp_path, (df,))
        assert hl_fail.status == IacCheckStatus.FAIL
        assert hl_fail.findings[0].rule_id == "DL3008"

    # ShellCheck failure and clean
    sc_json = json.dumps(
        [
            {
                "file": "boot.sh",
                "line": 2,
                "level": "warning",
                "code": 2086,
                "message": "Double quote to prevent globbing",
            }
        ]
    )
    with (
        patch(
            "hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/shellcheck"
        ),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            side_effect=[(1, sc_json, "", 0.02), (0, "[]", "", 0.02)],
        ),
    ):
        sc_fail = adapter.run_shellcheck(tmp_path, (sh,))
        assert sc_fail.status == IacCheckStatus.FAIL
        assert sc_fail.findings[0].rule_id == "SC2086"

        sc_pass = adapter.run_shellcheck(tmp_path, (sh,))
        assert sc_pass.status == IacCheckStatus.PASS


def test_iac_runner_missing_binaries_empty_and_malformed_json(tmp_path: Path) -> None:
    """Verify empty inputs, missing binaries, malformed JSON fallbacks, and clean passes."""
    from hexaqual.adapters.runners.iac_runner import (
        _format_rel_path,
        _infer_category_from_path,
        _is_k8s_manifest,
        _parse_checkov_json,
        _parse_hadolint_json,
        _parse_shellcheck_json,
        _parse_tflint_json,
        _parse_tofu_validate_json,
        _parse_trivy_json,
    )
    from hexaqual.domain.iac import IacCategory

    adapter = SubprocessIacAuditorAdapter()
    tf_dir = tmp_path / "tf"
    tf_dir.mkdir()
    df = tmp_path / "Dockerfile"
    df.write_text("FROM scratch\n", encoding="utf-8")
    sh = tmp_path / "run.sh"
    sh.write_text("#!/bin/sh\n", encoding="utf-8")

    # Path inference and relative formatting edge cases
    assert (
        _format_rel_path(Path("/unrelated/other/file.tf"), tmp_path) == "/unrelated/other/file.tf"
    )
    assert _infer_category_from_path("deploy/k8s.yaml") == IacCategory.KUBERNETES
    assert _infer_category_from_path("scripts/boot.sh") == IacCategory.SHELL
    assert _is_k8s_manifest(tmp_path / "missing.yaml", tmp_path) is False

    # Malformed / non-dict / non-list JSON parser paths
    for bad in ("{bad", "123", "null"):
        assert _parse_tofu_validate_json(bad, tf_dir, tmp_path) == []
        assert _parse_tflint_json(bad, tf_dir, tmp_path) == []
        assert _parse_trivy_json(bad, tf_dir, tmp_path) == []
        assert _parse_checkov_json(bad, tf_dir, tmp_path) == []
        assert _parse_hadolint_json(bad, tmp_path) == []
        assert _parse_shellcheck_json(bad, tmp_path) == []

    # Dict checkov payload and empty asset skips
    ckv_dict = json.dumps(
        {
            "results": {
                "failed_checks": [
                    {"check_id": "CKV_1", "check_name": "Bad config", "file_path": "/tf/main.tf"}
                ]
            }
        }
    )
    ckv_findings = _parse_checkov_json(ckv_dict, tmp_path, tmp_path)
    assert len(ckv_findings) == 1
    assert _parse_checkov_json(json.dumps({"results": "bad"}), tmp_path, tmp_path) == []

    assert adapter.run_tflint(tmp_path, ()).status == IacCheckStatus.SKIP
    assert adapter.run_trivy(tmp_path, ()).status == IacCheckStatus.SKIP
    assert adapter.run_checkov(tmp_path, ()).status == IacCheckStatus.SKIP
    assert adapter.run_hadolint(tmp_path, ()).status == IacCheckStatus.SKIP
    assert adapter.run_shellcheck(tmp_path, ()).status == IacCheckStatus.SKIP

    # Missing binaries across remaining tools
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value=None),
        patch("hexaqual.adapters.runners.iac_runner.Path.is_file", return_value=False),
    ):
        assert adapter.run_tflint(tmp_path, (tf_dir,)).status == IacCheckStatus.SKIP
        assert adapter.run_trivy(tmp_path, (tf_dir,)).status == IacCheckStatus.SKIP
        assert adapter.run_checkov(tmp_path, (tf_dir,)).status == IacCheckStatus.SKIP
        assert adapter.run_hadolint(tmp_path, (df,)).status == IacCheckStatus.SKIP
        assert adapter.run_shellcheck(tmp_path, (sh,)).status == IacCheckStatus.SKIP

    # Fallback errors when subprocess fails with non-JSON stderr, plus clean PASS paths
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tool"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            side_effect=[
                (2, "", "tflint crash", 0.01),
                (0, json.dumps({"issues": [], "errors": []}), "", 0.01),
                (1, "", "trivy crash", 0.01),
                (0, json.dumps({"Results": []}), "", 0.01),
                (1, "", "checkov crash", 0.01),
                (0, json.dumps({"results": {"failed_checks": []}}), "", 0.01),
            ],
        ),
    ):
        assert adapter.run_tflint(tmp_path, (tf_dir,)).status == IacCheckStatus.FAIL
        assert adapter.run_tflint(tmp_path, (tf_dir,)).status == IacCheckStatus.PASS
        assert adapter.run_trivy(tmp_path, (tf_dir,)).status == IacCheckStatus.FAIL
        assert adapter.run_trivy(tmp_path, (tf_dir,)).status == IacCheckStatus.PASS
        assert adapter.run_checkov(tmp_path, (tf_dir,)).status == IacCheckStatus.FAIL
        assert adapter.run_checkov(tmp_path, (tf_dir,)).status == IacCheckStatus.PASS

    # Tofu validate fallback diagnostic on non-zero exit + bad JSON
    (tf_dir / ".terraform").mkdir()
    with (
        patch("hexaqual.adapters.runners.iac_runner.shutil.which", return_value="/usr/bin/tofu"),
        patch(
            "hexaqual.adapters.runners.iac_runner._execute_subprocess",
            return_value=(1, "", "broken hcl", 0.02),
        ),
    ):
        val_fail = adapter.run_tofu_validate(tmp_path, (tf_dir,))
        assert val_fail.status == IacCheckStatus.FAIL
        assert "broken hcl" in val_fail.findings[0].message
