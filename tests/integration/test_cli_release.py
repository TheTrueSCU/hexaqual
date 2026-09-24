"""Integration tests for hexaqual release CLI subcommands.

Notes/Architectural Intent:
    Exercises package building, PyPI release collision checks, and publishing
    workflows in a synthetic workspace without real network calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from hexaqual.cli.release import release_app


@pytest.mark.integration
def test_release_help(runner: CliRunner) -> None:
    """Verify release CLI displays help and available subcommands."""
    res = runner.invoke(release_app, ["--help"])
    assert res.exit_code == 0
    assert "Distribution package building" in res.stdout
    assert "build" in res.stdout
    assert "check" in res.stdout
    assert "publish" in res.stdout


@pytest.mark.integration
def test_release_check_clean(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify release check inspects PyPI for existing releases without errors.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # Mock PyPI client to report no versions released yet
    with patch(
        "hexaqual.adapters.publishers.pypi.PyPiPublisherAdapter.check_version_exists",
        return_value=False,
    ):
        res = runner.invoke(release_app, ["check"])
        assert res.exit_code == 0
        assert "pkg-core" in res.stdout or "pkg_core" in res.stdout


@pytest.mark.integration
def test_release_check_detects_collision(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify release check flags when a version already exists on PyPI.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)

    # Mock PyPI client returning True for pkg-core 0.1.0 collision
    def mock_check_version(self, pkg_name: str, version: str) -> bool:
        return "core" in pkg_name and version == "0.1.0"

    with patch(
        "hexaqual.adapters.publishers.pypi.PyPiPublisherAdapter.check_version_exists",
        new=mock_check_version,
    ):
        res = runner.invoke(release_app, ["check"])
        assert res.exit_code == 0
        assert "EXISTS" in res.stdout or "0.1.0" in res.stdout


@pytest.mark.integration
def test_release_build_invocation(
    synthetic_workspace: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify release build executes and constructs distribution directory.

    Args:
        synthetic_workspace: Temporary workspace fixture.
        runner: CLI execution runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.chdir(synthetic_workspace)
    dist_dir = synthetic_workspace / "dist"

    def mock_build(
        self, package_name: str, out_dir: Path, env: dict[str, str] | None = None
    ) -> tuple[bool, str]:
        out_dir.mkdir(parents=True, exist_ok=True)
        wheel = out_dir / f"{package_name}-0.1.0-py3-none-any.whl"
        sdist = out_dir / f"{package_name}-0.1.0.tar.gz"
        wheel.write_bytes(b"PK\x03\x04fake_wheel")
        sdist.write_bytes(b"fake_sdist")
        return True, "Successfully built artifacts"

    with patch(
        "hexaqual.adapters.publishers.pypi.PyPiPublisherAdapter.build_package",
        new=mock_build,
    ):
        res = runner.invoke(release_app, ["build", "--dist-dir", str(dist_dir)])
        assert res.exit_code == 0
        is_dir = dist_dir.is_dir()
        assert is_dir is True
        wheels = list(dist_dir.glob("*.whl"))
        has_wheels = len(wheels) > 0
        assert has_wheels is True
